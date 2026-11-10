// SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
//
// SPDX-License-Identifier: Apache-2.0

use numpy::ndarray::{ArrayBase, Axis, Dimension, ViewRepr};
use std::iter::once;
use wide::u64x4;

use super::gates::RowIndex;

/// Convert a column of a boolean array into a vector of SIMD u64x4 blocks representing the same data.
pub fn col_to_col<D: Dimension>(col: ArrayBase<ViewRepr<&bool>, D>) -> Vec<u64x4> {
    col.axis_chunks_iter(Axis(0), 256)
        .map(|chunk| {
            let mut block = [0u64; 4];
            for (i, b) in chunk.into_iter().enumerate() {
                if *b {
                    block[i / 64] |= 1u64 << (i % 64);
                }
            }
            u64x4::from(block)
        })
        .collect()
}

/// Store the column of a tableau corresponding to a qubit.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Column {
    /// Blocks of the column. Use SIMD-accelerated operations.
    pub blocks: Vec<u64x4>,
    /// Number of rows of the column. The last block may not be full.
    pub num_rows: usize,
    /// Mask of the elements in the final block, that belong to the row.
    /// Used to make sure elements not belonging in the row are set to 0.
    final_block_mask: u64x4,
}

impl Column {
    pub fn new(blocks: Vec<u64x4>, num_rows: usize) -> Self {
        assert!(!blocks.is_empty() && num_rows > 0);
        let final_block_mask = build_final_block_mask(num_rows);
        let mut column = Self {
            blocks,
            num_rows,
            final_block_mask,
        };
        column.apply_final_block_mask();
        column
    }

    /// Make sure all elements in the final block that do not belong to the row are zeroed out.
    pub fn apply_final_block_mask(&mut self) {
        *self
            .blocks
            .last_mut()
            .expect("Should have at least one block.") &= self.final_block_mask;
    }

    /// Number of blocks in the row.
    pub fn storage_len(&self) -> usize {
        self.blocks.len()
    }

    /// Set all elements in the column to zero.
    pub fn set_to_zero(&mut self) {
        for block in &mut self.blocks {
            *block = u64x4::ZERO;
        }
    }

    /// Set all elements in the column to one.
    pub fn set_to_one(&mut self) {
        for block in &mut self.blocks {
            *block = u64x4::MAX;
        }
        *self
            .blocks
            .last_mut()
            .expect("Should have at least one block.") &= self.final_block_mask;
    }

    /// Check if all elements in the column are zero.
    pub fn is_zero(&self) -> bool {
        self.blocks.iter().all(|block| *block == u64x4::ZERO)
    }

    /// Initialize a new column with all zero entries and the current shape.
    pub fn zeros_like(&self) -> Self {
        let mut empty = self.clone();
        empty.set_to_zero();
        empty
    }

    /// Initialize a new column with all one entries and the current shape.
    pub fn ones_like(&self) -> Self {
        let mut empty = self.clone();
        empty.set_to_one();
        empty
    }

    /// Apply a Toffoli gate to the current column with controls `controls`.
    /// The second entry in each `controls`-tuple shows whether we control on |1>
    /// (true) or |0> (false).
    pub fn toffoli<'a>(
        &mut self,
        controls: impl IntoIterator<Item = (&'a Self, bool)> + Clone + Sync,
    ) {
        assert!(
            controls
                .clone()
                .into_iter()
                .all(|c| self.num_rows == c.0.num_rows)
        );

        self.blocks
            .iter_mut()
            .enumerate()
            .for_each(|(block_idx, block)| {
                *block ^= controls
                    .clone()
                    .into_iter()
                    .map(|(col, is_one)| {
                        if is_one {
                            col.blocks[block_idx]
                        } else {
                            !col.blocks[block_idx]
                        }
                    })
                    .reduce(|a, b| a & b)
                    .expect("Controls have at least one entry.");
            });
        self.apply_final_block_mask();
    }

    /// Apply a CX gate to the current column with control `control`.
    pub fn cx(&mut self, control: &Self) {
        self.toffoli(once((control, true)));
    }

    /// Get the content at row `row`.
    pub fn get(&self, row: RowIndex) -> bool {
        assert!(row.0 < self.num_rows as u32);
        let lane = row.0 % 256;
        self.blocks[(row.0 / 256) as usize].as_array()[(lane / 64) as usize] & (1 << (lane % 64))
            != 0
    }

    /// Find a non-zero element. Return None if none is found.
    pub fn find_non_zero_element(&self) -> Option<RowIndex> {
        self.blocks.iter().enumerate().find_map(|(i, block)| {
            if *block != u64x4::ZERO {
                Some(
                    block
                        .as_array()
                        .iter()
                        .enumerate()
                        .find_map(|(lane, a)| {
                            let offset = (i * 256 + lane * 64) as u32;
                            (a.trailing_zeros() != 64)
                                .then_some(RowIndex(offset + a.trailing_zeros()))
                        })
                        .unwrap(),
                )
            } else {
                None
            }
        })
    }

    /// Find a non-zero element excluding the row `exclude`. Return None if there is no non-zero element.
    pub fn find_non_zero_element_exclude_row(&self, exclude: RowIndex) -> Option<RowIndex> {
        self.blocks.iter().enumerate().find_map(|(i, block)| {
            if *block != u64x4::ZERO {
                block.as_array().iter().enumerate().find_map(|(lane, a)| {
                    let offset = (i * 256 + lane * 64) as u32;
                    if (a.trailing_zeros() != 64) && (offset + a.trailing_zeros() != exclude.0) {
                        Some(RowIndex(offset + a.trailing_zeros()))
                    } else if (a.trailing_zeros() != 64)
                        && (63 - a.leading_zeros() != a.trailing_zeros())
                    {
                        Some(RowIndex(offset + 63 - a.leading_zeros()))
                    } else {
                        None
                    }
                })
            } else {
                None
            }
        })
    }

    /// Find a non-zero element excluding the rows `exclude`. Return None if there is no non-zero element.
    pub fn find_non_zero_element_exclude_row_list(
        &self,
        exclude: impl Iterator<Item = Option<RowIndex>> + Clone,
    ) -> Option<RowIndex> {
        self.blocks.iter().enumerate().find_map(|(i, block)| {
            if *block != u64x4::ZERO {
                block.as_array().iter().enumerate().find_map(|(lane, a)| {
                    bool_iter(*a).enumerate().find_map(|(j, set)| {
                        let offset = (i * 256 + lane * 64) as u32;
                        let row = RowIndex(offset + j as u32);
                        if set
                            && exclude.clone().all(|batch_row| {
                                batch_row.as_ref().is_none_or(|batch_row| *batch_row != row)
                            })
                        {
                            Some(row)
                        } else {
                            None
                        }
                    })
                })
            } else {
                None
            }
        })
    }
}

/// Build a mask for the final block of a column with `num_rows` rows.
pub fn build_final_block_mask(num_rows: usize) -> u64x4 {
    assert!(num_rows > 0);

    if num_rows.is_multiple_of(256) {
        return u64x4::MAX;
    }

    let num_full_lanes = (num_rows % 256) / 64;
    let mut block = [0u64; 4];
    for lane in block.iter_mut().take(num_full_lanes) {
        *lane = u64::MAX;
    }

    let num_final_lane_bits = num_rows % 64;
    if num_final_lane_bits > 0 {
        block[num_full_lanes] = (1u64 << num_final_lane_bits) - 1
    }
    u64x4::from(block)
}

/// Iterate over the bits of a u64 from LSB to MSB.
fn bool_iter(val: u64) -> impl Iterator<Item = bool> {
    (0..64).map(move |i| ((val >> i) & 1) != 0)
}

#[cfg(test)]
mod tests {
    use numpy::ndarray::Array1;

    use super::*;

    #[test]
    fn test_bool_iter_basic_pattern() {
        let bits: Vec<bool> = bool_iter(0b10110).collect();
        assert_eq!(&bits[0..5], &[false, true, true, false, true]);
        assert!(bits[5..].iter().all(|&b| !b));
        assert_eq!(bits.len(), 64);
    }

    #[test]
    fn test_build_final_block_mask() {
        assert_eq!(build_final_block_mask(512), u64x4::MAX);
        assert_eq!(
            build_final_block_mask(192),
            u64x4::from([u64::MAX, u64::MAX, u64::MAX, 0])
        );
        assert_eq!(
            build_final_block_mask(62),
            u64x4::from([u64::MAX >> 2, 0, 0, 0])
        );
        assert_eq!(
            build_final_block_mask(193),
            u64x4::from([u64::MAX, u64::MAX, u64::MAX, 1])
        );
    }

    #[test]
    fn test_apply_final_block_mask() {
        let col1 = Column::new(vec![u64x4::ZERO, u64x4::from([0, 3, 0, 0])], 256 + 64 + 2);
        let col2 = Column::new(vec![u64x4::ZERO, u64x4::from([0, 7, 0, 0])], 256 + 64 + 2);
        let col3 = Column::new(vec![u64x4::ZERO, u64x4::from([0, 7, 0, 0])], 256 + 64 + 3);

        assert_eq!(col1, col2);
        assert_ne!(col1, col3);
    }

    #[test]
    fn test_get_and_set_bits() {
        let col = Column::new(vec![u64x4::ZERO, u64x4::from([0, 2, 0, 0])], 256 + 64 + 2);
        assert!(col.get(RowIndex(256 + 64 + 1)));
        assert!(!col.get(RowIndex(256 + 64)));
    }

    #[test]
    fn test_cx_gate() {
        let mut target = Column::new(vec![u64x4::ZERO; 2], 301);
        let control = Column::new(
            vec![
                u64x4::from([1u64 << 5, 0, 0, 0]),
                u64x4::from([1u64 << (300 % 256), 0, 0, 0]),
            ],
            301,
        );

        target.cx(&control);
        assert_eq!(target, control);
    }

    #[test]
    fn test_toffoli() {
        let mut target = Column::new(vec![u64x4::MAX, u64x4::from([0, 3, 0, 0])], 256 + 64 + 2);
        let control0 = Column::new(vec![u64x4::MAX, u64x4::from([0, 1, 0, 0])], 256 + 64 + 2);
        let control1 = Column::new(vec![u64x4::MAX, u64x4::from([0, 2, 0, 0])], 256 + 64 + 2);
        target.toffoli([(&control0, true), (&control1, false)].into_iter());
        assert_eq!(target, control1);
    }

    #[test]
    fn test_find_non_zero_element() {
        let col = Column::new(vec![u64x4::ZERO, u64x4::from([0, 3, 0, 0])], 256 + 64 + 2);
        let found = col.find_non_zero_element().expect("must find something");
        assert_eq!(found, RowIndex(256 + 64));
        let col = Column::new(vec![u64x4::MAX, u64x4::from([0, 3, 0, 0])], 256 + 64 + 2);
        let found = col.find_non_zero_element().expect("must find something");
        assert_eq!(found, RowIndex(0));
    }

    #[test]
    fn test_find_non_zero_element_exclude_row() {
        let col = Column::new(vec![u64x4::ZERO, u64x4::from([0, 3, 0, 0])], 256 + 64 + 2);
        let found = col
            .find_non_zero_element_exclude_row(RowIndex(256 + 64))
            .expect("must find something");
        assert_eq!(found, RowIndex(256 + 64 + 1));
    }

    #[test]
    fn test_find_non_zero_element_exclude_row_list() {
        let col = Column::new(vec![u64x4::MAX, u64x4::from([0, 3, 0, 0])], 256 + 64 + 2);
        let found = col
            .find_non_zero_element_exclude_row_list(
                (0..256)
                    .map(RowIndex)
                    .chain(once(RowIndex(256 + 64)))
                    .map(Some),
            )
            .expect("must find something");
        assert_eq!(found, RowIndex(256 + 64 + 1));
    }

    #[test]
    fn test_to_column() {
        let num_rows = 512 + 64 + 2;
        let col = Column::new(
            col_to_col(
                (0..num_rows)
                    .map(|i| i % 2 == 1)
                    .collect::<Array1<_>>()
                    .view(),
            ),
            num_rows,
        );
        assert!((0..num_rows).all(|i| col.get(RowIndex(i as u32)) == (i % 2 == 1)))
    }
}
