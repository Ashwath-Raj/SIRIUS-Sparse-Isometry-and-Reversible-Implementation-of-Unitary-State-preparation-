// SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
//
// SPDX-License-Identifier: Apache-2.0

use numpy::ndarray::{ArrayBase, Dim, ViewRepr};
use std::{cmp::min, fmt, iter::once};

use super::{
    column::{Column, col_to_col},
    gates::{ColumnIndex, Gate, RowIndex, ToffoliControls},
};

/// Store the signs to fix of each basis state.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Signs {
    /// Temporary column to store intermediary results of
    /// Toffoli gates for performance reasons.
    tmp_col: Column,
    /// Signs of each basis state. Needs to be all zero at the end of the algorithm.
    pub signs: Column,
    /// Extra column used to guarantee that all elements have been iterated over.
    /// Needs to be all zero at the end of the algorithm.
    pub extra_col: Column,
}

impl Signs {
    fn new(signs: Column) -> Self {
        let tmp_col = Column::zeros_like(&signs);
        let extra_col = Column::ones_like(&signs);
        Self {
            tmp_col,
            signs,
            extra_col,
        }
    }
}

/// Stores the basis states that shall be mapped into the subspace.
#[derive(Clone, Debug, PartialEq, Eq)]
#[repr(align(64))]
pub struct Tableau {
    /// Columns of the tableau corresponding to qubits.
    pub cols: Vec<Column>,
    /// Number of qubits in the subpspace.
    pub subspace_bitsize: usize,
    /// Temporary column to store intermediary results of
    /// Toffoli gates for performance reasons.
    tmp_col: Column,
    /// Signs to be fixed and extra column for doing so.
    pub signs: Option<Signs>,
}

impl fmt::Display for Tableau {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let signs = self.signs.as_ref();

        for row_idx in 0u32..self.num_rows() as u32 {
            f.write_fmt(format_args!(
                "{:?} | {:?} | {:?}\n",
                self.get_row(RowIndex(row_idx))
                    .map(|x| x as usize)
                    .collect::<Vec<usize>>(),
                signs
                    .map(|signs| signs.signs.get(RowIndex(row_idx)))
                    .map(|x| x as usize),
                signs
                    .map(|signs| signs.extra_col.get(RowIndex(row_idx)))
                    .map(|x| x as usize)
            ))?;
        }
        Ok(())
    }
}

impl Tableau {
    /// Crate new tableau out of a list of `cols` and (if provided) of a `signs` column.
    /// If a `subspace_bitsize` is provided use it, otherwise compute the minimal subspace to
    /// enumerate all rows of the tableau.
    fn new(cols: Vec<Column>, signs: Option<Column>, subspace_bitsize: Option<usize>) -> Self {
        assert!(cols.iter().all(|col| col.num_rows == cols[0].num_rows));

        if let Some(subspace_bitsize) = subspace_bitsize {
            assert!(subspace_bitsize >= next_two_exponent(cols[0].num_rows));
            assert!(subspace_bitsize < cols.len());
        }
        let subspace_bitsize = subspace_bitsize.unwrap_or(next_two_exponent(cols[0].num_rows));

        let tmp_col = Column::zeros_like(&cols[0]);

        if let Some(signs) = &signs {
            assert!(signs.num_rows == cols[0].num_rows);
        }
        let signs = signs.map(Signs::new);

        Self {
            cols,
            subspace_bitsize,
            tmp_col,
            signs,
        }
    }

    /// Build a tableau from boolean arrays for `state` and `signs`.
    pub fn build(
        state: ArrayBase<ViewRepr<&bool>, Dim<[usize; 2]>>,
        signs: Option<ArrayBase<ViewRepr<&bool>, Dim<[usize; 1]>>>,
    ) -> Self {
        let cols: Vec<Column> = state
            .columns()
            .into_iter()
            .map(|col| Column::new(col_to_col(col), state.shape()[0]))
            .collect();
        let signs = signs
            .as_ref()
            .map(|signs| Column::new(col_to_col(*signs), signs.shape()[0]));
        Self::new(cols, signs, None)
    }

    /// Recompose the tableau from the `subtableaus` and update it with the blocks from the `rest_tableau`.
    pub fn recompose(&mut self, subtableaus: &[Tableau]) {
        assert!(
            subtableaus
                .iter()
                .all(|tab| tab.num_cols() == self.num_cols()
                    && tab.subspace_bitsize == self.subspace_bitsize)
        );

        assert!(
            subtableaus
                .iter()
                .map(|tableau| tableau.num_rows())
                .sum::<usize>()
                == self.num_rows()
        );

        for (i, col) in self.cols.iter_mut().enumerate() {
            col.blocks.clear();

            for t in subtableaus {
                let sub_col = &t.cols[i];
                col.blocks.extend_from_slice(&sub_col.blocks);
            }
        }
        if let Some(sign) = self.signs.as_mut() {
            sign.signs.blocks.clear();
            sign.extra_col.blocks.clear();

            for t in subtableaus {
                let signs = &t.signs.as_ref().expect("Should have signs");
                sign.signs.blocks.extend_from_slice(&signs.signs.blocks);
                sign.extra_col
                    .blocks
                    .extend_from_slice(&signs.extra_col.blocks);
            }
        }
    }

    /// Decompose the tableau into sub-tableaus where each row in a sub-tableau has `sub_problem_size` many blocks.
    /// All but the last block of the last sub-tableau are fully filled.
    pub fn decompose(&self, sub_problem_size: usize) -> Vec<Tableau> {
        let storage_len = self.cols[0].storage_len();
        assert!(storage_len > sub_problem_size);

        (0..storage_len)
            .step_by(sub_problem_size)
            .map(|blocks_start| {
                let blocks_end = min(blocks_start + sub_problem_size, storage_len);
                let num_rows = min(256 * sub_problem_size, self.num_rows() - 256 * blocks_start);

                let new_cols: Vec<Column> = self
                    .cols
                    .iter()
                    .map(|c| Column::new(c.blocks[blocks_start..blocks_end].to_vec(), num_rows))
                    .collect();

                let new_signs: Option<Column> = self.signs.as_ref().map(|c| {
                    Column::new(c.signs.blocks[blocks_start..blocks_end].to_vec(), num_rows)
                });

                Tableau::new(new_cols, new_signs, Some(self.subspace_bitsize))
            })
            .collect()
    }

    /// Number of rows in the tableau.
    pub fn num_rows(&self) -> usize {
        self.cols[0].num_rows
    }

    /// Number of columns in the tableau.
    pub fn num_cols(&self) -> usize {
        self.cols.len()
    }

    /// Number of blocks of each column in the tableau.
    pub fn row_storage_len(&self) -> usize {
        self.cols[0].storage_len()
    }

    /// Get the content of `row`-th row.
    pub fn get_row(&self, row: RowIndex) -> impl Iterator<Item = bool> + use<'_> {
        self.cols.iter().map(move |col| col.get(row))
    }

    /// Get the element in row `row` and column `column`.
    pub fn get(&self, row: RowIndex, colum: ColumnIndex) -> bool {
        self.cols[colum.0].get(row)
    }

    /// Apply the gates in `circ` to the tableau.
    pub fn apply_circ(&mut self, circ: &[Gate]) {
        for gate in circ {
            match gate {
                Gate::CX { control, target } => self.cx(*control, *target),
                Gate::CXExtra(target) => self.cx_extra(*target),
                Gate::Swap { target, non_target } => self.swap(*target, *non_target),
                Gate::Toffoli {
                    target,
                    control_positive,
                    control_with_bool,
                } => self.toffoli(*target, (*control_positive, true), *control_with_bool),
                Gate::ToffoliPUIFixed {
                    controls,
                    k: _,
                    use_restricted: _,
                } => self.toffoli_pui_fixed(*controls),
                Gate::ToffoliPUIRest {
                    target_col,
                    controls,
                    toggle_sign,
                    toggle_extra_col,
                } => self.toffoli_pui_rest(*target_col, *controls, *toggle_sign, *toggle_extra_col),
                _ => {} // Ignore marker gates.
            }
        }
    }

    /// Apply a Toffoli gat with target `target` and controls `control0`, `control1`.
    /// The second entry in the control tuples shows whether we control on |1>
    /// (true) or |0> (false).    
    fn toffoli(
        &mut self,
        target: ColumnIndex,
        control0: (ColumnIndex, bool),
        control1: (ColumnIndex, bool),
    ) {
        assert!(control0.0 < target);
        assert!(control1.0 < target);
        let (left, right) = self.cols.split_at_mut(target.0);
        right[0].toffoli(
            [control0, control1]
                .iter()
                .map(|(col, controlled_on_one)| (&left[col.0], *controlled_on_one)),
        );
    }

    /// Swap the two columns.
    fn swap(&mut self, a: ColumnIndex, b: ColumnIndex) {
        self.cols.swap(a.0, b.0);
    }

    /// Apply a CX gate with target `target` and control `control`.
    fn cx(&mut self, control: ColumnIndex, target: ColumnIndex) {
        assert!(control != target);
        let (control, target) = if control > target {
            let (left, right) = self.cols.split_at_mut(control.0);

            (&right[0], &mut left[target.0])
        } else {
            let (left, right) = self.cols.split_at_mut(target.0);
            (&left[control.0], &mut right[0])
        };

        target.cx(control);
    }

    /// Apply a CX gate with target `target` whose control is the extra column in the tableau.
    fn cx_extra(&mut self, target: ColumnIndex) {
        self.cols[target.0].cx(&self
            .signs
            .as_ref()
            .expect("Should have an extra column.")
            .extra_col)
    }

    /// Apply a multi-controlled Toffoli controlled on `controls` with the temporary
    /// column in the tableau as the target.    
    fn toffoli_pui_fixed(&mut self, controls: ToffoliControls) {
        let (subspace, _) = self.cols.split_at_mut(self.subspace_bitsize);
        if !controls.is_empty() {
            self.tmp_col.set_to_zero();
            self.tmp_col.toffoli(
                controls
                    .controls()
                    .map(|(col, set_to_one)| (&subspace[col.0], set_to_one)),
            );
        } else {
            self.tmp_col.set_to_one();
        }
    }

    /// Apply a multi-controlled Toffoli controlled on `controls` and the tmp_col
    /// with target `target_col` and if `toggle_extra_col` also the extra_col.
    /// If `toggle_sign` also toggle the sign using the same controls.
    fn toffoli_pui_rest(
        &mut self,
        target_col: ColumnIndex,
        controls: ToffoliControls,
        toggle_sign: bool,
        toggle_extra_col: bool,
    ) {
        let (subspace, non_subspace) = self.cols.split_at_mut(self.subspace_bitsize);

        let controls = controls
            .controls()
            .map(|(col, set_to_one)| (&subspace[col.0], set_to_one))
            .chain(once((&self.tmp_col, true)));

        if toggle_extra_col || toggle_sign {
            let signs = self
                .signs
                .as_mut()
                .expect("Should have signs if they are supposed to be toggled.");

            // Store the AND of the controls for performance reasons.
            signs.tmp_col.set_to_zero();
            signs.tmp_col.toffoli(controls);
            non_subspace[target_col.0].toffoli(once((&signs.tmp_col, true)));

            if toggle_extra_col {
                signs.extra_col.toffoli(once((&signs.tmp_col, true)));
            }
            if toggle_sign {
                signs.signs.toffoli(once((&signs.tmp_col, true)));
            }
        } else {
            non_subspace[target_col.0].toffoli(controls);
        }
    }
}

/// Give the smallest value u > 0 such that `num` <= 2**u.
pub fn next_two_exponent(num: usize) -> usize {
    if num < 2 {
        1usize
    } else {
        num.next_power_of_two().ilog2() as usize
    }
}

#[cfg(test)]
mod tests {

    use super::super::gates::BitVec;
    use super::*;

    use numpy::ndarray::{Array1, Array2};

    fn create_test_tableau() -> Tableau {
        let num_rows = 512 + 64 + 2;
        let num_cols = 11;

        let mut data = Array2::<bool>::default((num_rows, num_cols));

        for row in 0..num_rows {
            for col in 1..num_cols {
                let bit_is_one = ((row >> (num_cols - 1 - col)) & 1) == 1;
                data[(row, col)] = bit_is_one;
            }
        }
        Tableau::build(data.view(), Some(Array1::<bool>::default(num_rows).view()))
    }

    #[test]
    fn test_decompose_and_recompose_roundtrip() {
        let tableau = create_test_tableau();
        let subtableaus = tableau.decompose(2);

        assert_eq!(subtableaus.len(), 2);
        assert_eq!(subtableaus[0].num_rows(), 2 * 256);
        assert_eq!(subtableaus[1].num_rows(), 66);

        let mut recomposed = tableau.clone();
        recomposed.swap(ColumnIndex(2), ColumnIndex(5));
        recomposed.recompose(&subtableaus);

        assert_eq!(recomposed, tableau);
    }

    #[test]
    fn test_extra_cx() {
        let mut tableau = create_test_tableau();
        let mut tableau_base = tableau.clone();
        tableau.cx_extra(ColumnIndex(0));
        tableau_base.cols[0] = Column::ones_like(&tableau_base.cols[0]);

        assert_eq!(tableau_base, tableau);
    }

    #[test]
    fn test_toffoli_and_cx_tableau() {
        let mut tableau = create_test_tableau();
        let mut tableau_base = tableau.clone();
        tableau.toffoli(
            ColumnIndex(7),
            (ColumnIndex(2), true),
            (ColumnIndex(4), false),
        );
        tableau.toffoli(
            ColumnIndex(7),
            (ColumnIndex(2), true),
            (ColumnIndex(4), true),
        );
        tableau_base.cx(ColumnIndex(2), ColumnIndex(7));

        assert_eq!(tableau_base, tableau);
    }

    #[test]
    fn test_pui_0() {
        let mut tableau = create_test_tableau();
        let mut tableau_base = tableau.clone();
        let subspace_bitsize = tableau.subspace_bitsize as u8;

        tableau_base.toffoli(
            ColumnIndex(10),
            (ColumnIndex(2), true),
            (ColumnIndex(3), false),
        );
        tableau.toffoli_pui_fixed(ToffoliControls::new(
            BitVec::new(0b0011000000, subspace_bitsize),
            BitVec::new(0b0010000000, subspace_bitsize),
        ));
        tableau.toffoli_pui_rest(
            ColumnIndex(10 - subspace_bitsize as usize),
            ToffoliControls::new(
                BitVec::new(0, subspace_bitsize),
                BitVec::new(0, subspace_bitsize),
            ),
            false,
            false,
        );
        tableau.tmp_col = Column::zeros_like(&tableau.tmp_col);

        assert_eq!(tableau_base, tableau);
    }

    #[test]
    fn test_pui_1() {
        let mut tableau = create_test_tableau();
        let mut tableau_base = tableau.clone();
        let subspace_bitsize = tableau.subspace_bitsize as u8;

        tableau_base.toffoli(
            ColumnIndex(10),
            (ColumnIndex(2), true),
            (ColumnIndex(3), false),
        );
        tableau.toffoli_pui_fixed(ToffoliControls::new(
            BitVec::new(0, subspace_bitsize),
            BitVec::new(0, subspace_bitsize),
        ));
        tableau.toffoli_pui_rest(
            ColumnIndex(10 - subspace_bitsize as usize),
            ToffoliControls::new(
                BitVec::new(0b0011000000, subspace_bitsize),
                BitVec::new(0b0010000000, subspace_bitsize),
            ),
            false,
            false,
        );
        tableau.tmp_col = Column::zeros_like(&tableau.tmp_col);

        assert_eq!(tableau_base, tableau);
    }

    #[test]
    fn test_pui_sign_extra() {
        let mut tableau = create_test_tableau();
        let subspace_bitsize = tableau.subspace_bitsize as u8;

        tableau.toffoli_pui_fixed(ToffoliControls::new(
            BitVec::new(0, subspace_bitsize),
            BitVec::new(0, subspace_bitsize),
        ));
        tableau.toffoli_pui_rest(
            ColumnIndex(10 - subspace_bitsize as usize),
            ToffoliControls::new(
                BitVec::new(0b0100000000, subspace_bitsize),
                BitVec::new(0, subspace_bitsize),
            ),
            false,
            true,
        );
        tableau.toffoli_pui_rest(
            ColumnIndex(10 - subspace_bitsize as usize),
            ToffoliControls::new(
                BitVec::new(0b0100000000, subspace_bitsize),
                BitVec::new(0b0100000000, subspace_bitsize),
            ),
            true,
            false,
        );
        assert_eq!(
            tableau.signs.as_ref().expect("Should have signs").extra_col,
            tableau.cols[1]
        );
        assert_eq!(
            tableau.signs.as_ref().expect("Should have signs").signs,
            tableau.cols[1]
        );
    }
}
