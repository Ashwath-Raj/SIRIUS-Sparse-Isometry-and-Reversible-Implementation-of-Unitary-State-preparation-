// SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
//
// SPDX-License-Identifier: Apache-2.0

use std::ops::BitAnd;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct RowIndex(pub u32);

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ColumnIndex(pub usize);

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
/// Controls for a multi-controlled Toffoli gate of up to 32 control-qubits.
pub struct ToffoliControls {
    /// Set bits are control qubits.
    active_cols: BitVec,
    /// For set bits control on |1>, else on |0>.
    /// Only matters if corresponding bit in `active_cols` is set.
    positive_controls: BitVec,
}

impl ToffoliControls {
    pub fn new(active_cols: BitVec, positive_controls: BitVec) -> Self {
        assert_eq!(active_cols.len, positive_controls.len);
        Self {
            active_cols,
            positive_controls,
        }
    }

    /// Check if there are any controls.
    pub fn is_empty(&self) -> bool {
        self.active_cols.is_empty()
    }

    /// Iterate over all control qubits with corresponding information, whether
    /// the qubit is positively (true) or negatively controlled on that qubit.
    pub fn controls(&self) -> impl Iterator<Item = (ColumnIndex, bool)> + Clone {
        self.active_cols
            .into_iter()
            .enumerate()
            .zip(self.positive_controls.into_iter())
            .filter(|((_, active), _)| *active)
            .map(|((col, _), positive_control)| (ColumnIndex(col), positive_control))
    }
}

/// Store the bits of `len` qubits. Must be less than 33.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct BitVec {
    bits: u32,
    len: u8,
}

impl BitAnd for BitVec {
    type Output = Self;

    fn bitand(self, rhs: Self) -> Self::Output {
        assert!(
            self.len == rhs.len,
            "BitAnd requires equal lengths ({} != {})",
            self.len,
            rhs.len
        );
        Self::new(self.bits & rhs.bits, self.len)
    }
}

impl FromIterator<bool> for BitVec {
    fn from_iter<I: IntoIterator<Item = bool>>(iter: I) -> Self {
        let mut bits = 0u32;
        let mut len = 0u8;
        for (i, b) in iter.into_iter().enumerate() {
            len += 1;
            if b {
                bits |= 1u32 << i;
            }
        }
        let bits = bits.reverse_bits() >> (32 - len);
        Self { bits, len }
    }
}

impl BitVec {
    /// Create a new `BitVec`.
    pub fn new(bits: u32, len: u8) -> Self {
        assert!(
            len > 0 && len <= 32,
            "len must be less of equal than 32 and more than 0"
        );
        // `bits` must not contain a 1 beyond the declared length.
        assert!(
            bits.leading_zeros() >= 32 - len as u32,
            "bits contain a 1 outside the declared length"
        );
        Self { bits, len }
    }

    pub fn value(&self) -> u32 {
        self.bits
    }

    /// Iterate over the boolean values of the bits, **MSB first**.
    pub fn into_iter(self) -> impl Iterator<Item = bool> + Clone {
        (0..self.len)
            .rev()
            .map(move |i| ((self.bits >> i) & 1) != 0)
    }

    /// Get a bitmask where the bits from index `start` (inclusive) to
    /// `end` (exclusive) are set to one, each conted from the MSB.
    pub fn bit_mask(start: ColumnIndex, end: ColumnIndex, len: u8) -> Self {
        if start == end {
            return Self::new(0, len);
        }

        let width = (end.0 - start.0) as u32;
        let mask = (u32::MAX >> (32 - width)) << (len as usize - end.0);
        Self::new(mask, len)
    }

    /// Check if any bit is set.
    pub fn is_empty(&self) -> bool {
        self.bits == 0u32
    }
}

/// Gates we apply to the tableau.
/// For performance reasons we use small gates living on the stack.
/// We have three marker Gates that later help to parse the gate sequence.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Gate {
    /// Mark the end of a row construction.
    EndRow,
    /// Mark the end of a batch creation.
    EndBatch,
    /// Mark the end of zeroing a batch.
    EndZeroing,
    /// Multi controlled Toffoli controlled on `controls` with the tmp_col
    /// as the target. For use within Qualtran store the `k` of the first element
    /// in the batch and whether the PUI `use_restricted`.
    ToffoliPUIFixed {
        controls: ToffoliControls,
        k: u32,
        use_restricted: bool,
    },
    /// Multi control Toffoli controlled on `controls` and the tmp_col
    /// with target `target_col` and if `toggle_extra_col` also the extra_col.
    /// If `toggle_sign` also toggle the sign using the same controls.
    ToffoliPUIRest {
        target_col: ColumnIndex,
        controls: ToffoliControls,
        toggle_sign: bool,
        toggle_extra_col: bool,
    },
    /// Swap the two columns.
    Swap {
        target: ColumnIndex,
        non_target: ColumnIndex,
    },
    /// Toffoli with target `target` and controls `control0`, `control1`.
    /// The second entry in the control tuples shows whether we control on |1>
    /// (true) or |0> (false).
    Toffoli {
        target: ColumnIndex,
        control_positive: ColumnIndex,
        control_with_bool: (ColumnIndex, bool),
    },
    /// CX gate with `target` and `control` columns.
    CX {
        target: ColumnIndex,
        control: ColumnIndex,
    },
    /// CX gate whose control is the extra_col in the tableau.
    CXExtra(ColumnIndex),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[should_panic(expected = "bits contain a 1 outside the declared length")]
    fn bitvec_new_bits_out_of_range() {
        BitVec::new(0b1110, 3);
    }

    #[test]
    fn bitvec_new_ok() {
        BitVec::new(0b10101, 5);
    }

    #[test]
    fn bitvec_from_and_into_iter() {
        let src = vec![false, true, false, true, true, false];
        let bv: BitVec = src.clone().into_iter().collect();
        assert_eq!(bv.into_iter().collect::<Vec<_>>(), src);
    }

    #[test]
    fn bitvec_bit_mask_basic() {
        let mask = BitVec::bit_mask(ColumnIndex(2), ColumnIndex(5), 8);
        assert_eq!(
            mask.into_iter().collect::<Vec<_>>(),
            vec![false, false, true, true, true, false, false, false]
        );
    }

    #[test]
    fn bitvec_bit_mask_full_range() {
        let mask = BitVec::bit_mask(ColumnIndex(0), ColumnIndex(32), 32);
        assert_eq!(mask.into_iter().collect::<Vec<_>>(), vec![true; 32]);
    }

    #[test]
    fn multiple_mixed_controls() {
        let active = BitVec::from_iter([true, false, true, false, false, true]);
        let positive = BitVec::from_iter([true, false, false, false, false, true]);
        let ctrl = ToffoliControls::new(active, positive);

        let expected = vec![
            (ColumnIndex(0), true),
            (ColumnIndex(2), false),
            (ColumnIndex(5), true),
        ];

        let collected: Vec<_> = ctrl.controls().collect();
        assert_eq!(collected, expected);
    }
}
