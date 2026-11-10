// SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
//
// SPDX-License-Identifier: Apache-2.0

use std::{
    collections::HashSet,
    iter::{once, repeat_n},
    mem::take,
    thread::scope,
};

use super::{
    gates::{BitVec, ColumnIndex, Gate, RowIndex, ToffoliControls},
    tableau::{Tableau, next_two_exponent},
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
/// Three possible non-zero elements required for creating a new batch element.
enum NonZeroElement {
    /// Non-zero element in a column that is the target column or on the right of it.
    Good { row: RowIndex, col: ColumnIndex },
    /// No non-zero element within the target column or on the right of it.
    /// But non-zero element in the extra column in row `row`.
    Extra { row: RowIndex },
    /// No non-zero element in the target column or on the right of it.
    /// But non-zero element on the left of it within the non-subspace register
    /// in a row not yet in the batch.
    Bad { row: RowIndex, col: ColumnIndex },
}

/// Element within the batch.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct BatchElement {
    /// Row index of the state. Can be set to None if the row lies in a different subproblem.
    row: Option<RowIndex>,
    /// Subspace content of the state.
    subspace_content: BitVec,
    /// Whether to negate the sign of the state, i.e. the current content of the sign column.
    toggle_sign: bool,
    /// Whether to toggle the extra column, i.e. the current content of the extra column.
    toggle_extra_col: bool,
}

impl BatchElement {
    fn new(
        row: RowIndex,
        subspace_content: u32,
        toggle_sign: bool,
        toggle_extra_col: bool,
        subspace_bitsize: usize,
    ) -> Self {
        Self {
            row: Some(row),
            subspace_content: BitVec::new(subspace_content, subspace_bitsize as u8),
            toggle_sign,
            toggle_extra_col,
        }
    }

    /// Hide all rows. Used when a batch in a subproblem is not full at
    /// the end and is therefore filled up further in a new subproblem.
    fn hide_row(&mut self) {
        self.row = None;
    }
}

/// A problem instance keeping track of the relevant data of the algorithm.
pub struct Problem<'a> {
    /// Current tableau which shall be mapped in subspace form.
    tableau: &'a mut Tableau,
    /// Current batch.
    batch: Vec<BatchElement>,
    /// Counter variable. Shows how many states have already been mapped into the
    /// subspace. The subspace contains all binary bitstrings up to this number.
    k: u32,
    /// Circuit that transformed the initial tableau to the current version
    pub circuit: Vec<Gate>,
    /// Bijection sending the integer corresponding to the binary value in the
    /// subspace register of the row to its row index.
    pub bijection: Vec<(u32, RowIndex)>,
}

impl<'a> Problem<'a> {
    pub fn new(tableau: &'a mut Tableau) -> Self {
        Self {
            tableau,
            batch: Vec::new(),
            k: 0u32,
            circuit: Vec::new(),
            bijection: Vec::new(),
        }
    }

    /// Add `gate` to the circuit and apply it to the tableau.
    fn apply_gate(&mut self, gate: Gate) {
        self.circuit.push(gate);
        self.tableau.apply_circ(&[gate]);
    }

    /// Load relevant problem data from the `sub_problem`.
    fn synchronise_with_sub_problem(&mut self, sub_problem: Problem, num_prior_rows: u32) {
        self.batch = sub_problem.batch;
        for batch_element in &mut self.batch {
            if let Some(row) = batch_element.row.as_mut() {
                *row = RowIndex(row.0 + num_prior_rows)
            }
        }
        self.k = sub_problem.k;
        self.circuit.extend(sub_problem.circuit);
        self.bijection.extend(
            sub_problem
                .bijection
                .into_iter()
                .map(|(i, row)| (i, RowIndex(row.0 + num_prior_rows))),
        );
    }

    /// Create a sub-problem from the `tableau` initialized with the correct problem data.
    fn create_sub_problem<'b>(&mut self, tableau: &'b mut Tableau) -> Problem<'b> {
        let mut batch = take(&mut self.batch);
        for batch_element in &mut batch {
            batch_element.hide_row();
        }
        Problem {
            tableau,
            batch,
            k: self.k,
            circuit: Vec::new(),
            bijection: Vec::new(),
        }
    }

    /// The maximum batch size is the biggest power of two that fits into the
    /// full register after the subspace qubits are removed.
    fn max_batch_size(&self) -> usize {
        let non_subspace_bitsize = self.tableau.num_cols() - self.tableau.subspace_bitsize;
        assert!(non_subspace_bitsize != 0);

        if non_subspace_bitsize.is_power_of_two() {
            non_subspace_bitsize
        } else {
            non_subspace_bitsize.next_power_of_two() / 2
        }
    }

    /// Given a control element (`control_row`, `control_column`) we bring the of this element into the desired
    /// format, i.e. the subspace qubits are set to the binary representation of the current k and non-subspace
    /// qubits are 0, except of the i-th, where i is the number of current elements in the batch. After that add
    /// the row to the batch.
    fn format_row_and_add_to_batch(&mut self, control_row: RowIndex, control_column: ColumnIndex) {
        let subspace_bitsize = self.tableau.subspace_bitsize;

        let (toggle_sign, toggle_extra_col) = if let Some(signs) = self.tableau.signs.as_ref() {
            (
                signs.signs.get(control_row),
                signs.extra_col.get(control_row),
            )
        } else {
            (false, false)
        };

        let new_batch_element = BatchElement::new(
            control_row,
            self.k,
            toggle_sign,
            toggle_extra_col,
            subspace_bitsize,
        );

        let non_subspace_aim = (subspace_bitsize..self.tableau.num_cols())
            .map(|col| ColumnIndex(col) == control_column);

        let circ_len = self.circuit.len();
        self.circuit.extend(
            new_batch_element
                .subspace_content
                .into_iter()
                .chain(non_subspace_aim)
                .enumerate()
                .filter(|(col, target_val)| {
                    self.tableau.get(control_row, ColumnIndex(*col)) != *target_val
                })
                .map(|(col, _)| Gate::CX {
                    control: control_column,
                    target: ColumnIndex(col),
                })
                .chain(once(Gate::EndRow)),
        );
        self.tableau.apply_circ(&self.circuit[circ_len..]);

        // Row has now the form |self.k|0...1....0| where the 1 is at control column.

        self.batch.push(new_batch_element);
        self.bijection.push((self.k, control_row));
    }

    /// Try to find the next non-zero element in the `target_col` whose row we can then format
    /// and add to the batch. First check if we have a good non-zero element at the target column
    /// or on the right of it. If this does not yield anything, check if we have an extra column with
    /// a non-zero entry ignoring rows in the batch. Lastly check if there is a non-zero element in the
    /// non-suspace register left of the target column whose row is not yet in the batch. If none of
    /// the searches yield an element return None.
    fn find_next_non_zero_element(&self, target_col: ColumnIndex) -> Option<NonZeroElement> {
        (target_col.0..self.tableau.num_cols())
            .find_map(|col| {
                self.tableau.cols[col]
                    .find_non_zero_element()
                    .map(|row| NonZeroElement::Good {
                        row,
                        col: ColumnIndex(col),
                    })
            })
            .or_else(|| {
                self.batch
                    .iter()
                    .map(|batch_element| batch_element.row)
                    .enumerate()
                    .find_map(|(col, batch_row)| {
                        // Search for non-zero element in batch_row excluding the batch_row.
                        let batch_col = ColumnIndex(col + self.tableau.subspace_bitsize);
                        if let Some(batch_row) = batch_row {
                            self.tableau.cols[batch_col.0]
                                .find_non_zero_element_exclude_row(batch_row)
                        } else {
                            // batch element in earlier subtableau.
                            self.tableau.cols[batch_col.0].find_non_zero_element()
                        }
                        .map(|row| NonZeroElement::Bad {
                            row,
                            col: batch_col,
                        })
                    })
            })
            .or_else(|| {
                self.tableau.signs.as_ref().and_then(|signs| {
                    // Search for non-zero element in extra_col ignoring all rows in the batch.
                    signs
                        .extra_col
                        .find_non_zero_element_exclude_row_list(
                            self.batch.iter().map(|batch_element| batch_element.row),
                        )
                        .map(|row| NonZeroElement::Extra { row })
                })
            })
    }

    /// Make sure that the `target_col` has some non-zero element without changing elements in the batch.
    /// If the `non_zero_el` is good, we only have to swap the corresponding column to the target column.
    /// In the other cases a more involved procedure is needed.
    fn create_target_column(
        &mut self,
        target_col: ColumnIndex,
        non_zero_el: NonZeroElement,
    ) -> RowIndex {
        match non_zero_el {
            NonZeroElement::Good { row, col } => {
                if col != target_col {
                    self.apply_gate(Gate::Swap {
                        target: target_col,
                        non_target: col,
                    });
                }
                row
            }
            NonZeroElement::Bad { row, col } => {
                self.create_target_column_from_bad_column(target_col, row, col);
                row
            }
            NonZeroElement::Extra { row } => {
                self.create_target_column_from_extra_column(target_col);
                row
            }
        }
    }

    /// Create the `target_col` from the extra column by first applying a CX on the target column controlled on
    /// the extra column. Then remove potential unwanted ones in rows that are in the batch caused by this CX.
    /// The last step can not delete the target entry in the target column, as the target row only has a single entry.
    fn create_target_column_from_extra_column(&mut self, target_col: ColumnIndex) {
        self.apply_gate(Gate::CXExtra(target_col));

        let circ_len = self.circuit.len();
        self.circuit.extend(
            self.batch
                .iter()
                .enumerate()
                .filter(|(_, batch_element)| batch_element.toggle_extra_col)
                .map(|(i, _)| {
                    let batch_col = ColumnIndex(i + self.tableau.subspace_bitsize);
                    Gate::CX {
                        control: batch_col,
                        target: target_col,
                    }
                }),
        );
        self.tableau.apply_circ(&self.circuit[circ_len..]);
    }

    /// Create the `target_col` from a `col` that already corresponds to an element in the batch.
    /// Apply a Toffoli with this column as control and the target column as target. The second control
    /// column of the Toffoli is one in which the the batch row and the `row` differ. Control that qubit
    /// on the value of the element in the row.
    fn create_target_column_from_bad_column(
        &mut self,
        target_col: ColumnIndex,
        row: RowIndex,
        col: ColumnIndex,
    ) {
        let col_equal = col;
        let col_differing = ColumnIndex(
            self.batch[col_equal.0 - self.tableau.subspace_bitsize] // batch element with a 1 in col_equal
                .subspace_content
                .into_iter()
                .chain(repeat_n(false, col_equal.0)) // row content of the batch element
                // need to do it like this since the batch row might be in a different subproblem.
                .zip(self.tableau.get_row(row))
                .enumerate()
                .find(|(_, (a, b))| a != b)
                .expect("By construction we should have a differing element.")
                .0,
        );
        let differing_value_target_row = self.tableau.get(row, col_differing);

        self.apply_gate(Gate::Toffoli {
            target: target_col,
            control_positive: col_equal,
            control_with_bool: (col_differing, differing_value_target_row),
        });
    }

    /// Zero the non-subspace register content of the rows in the batch using a partial unary iteration (PUI).
    /// If it `make_restricted` we use a restricted PUI to make sure all elements that were in the subspace before
    /// are still in the subspace after the PUI.
    fn zero_non_subspace_bits(&mut self, use_restricted: bool) {
        assert!(
            (self.k - self.batch.len() as u32).is_multiple_of(self.max_batch_size() as u32),
            "Should have had only full batches before."
        );
        assert!(!self.batch.is_empty());
        let subspace_bitsize = self.tableau.subspace_bitsize;

        // Batch rows are |fixed cols|changing cols|non subspace bits|
        // The first is   |fixed cols|0...........0|10..............0|
        // The second is  |fixed cols|0...........1|01..............0|
        // And so forth.

        let num_changing_bits = next_two_exponent(self.batch.len());
        let num_fixed_bits = subspace_bitsize - num_changing_bits;

        let bit_mask_changing_cols = BitVec::bit_mask(
            ColumnIndex(num_fixed_bits),
            ColumnIndex(subspace_bitsize),
            subspace_bitsize as u8,
        );
        let bit_mask_fixed_cols = BitVec::bit_mask(
            ColumnIndex(0),
            ColumnIndex(num_fixed_bits),
            subspace_bitsize as u8,
        );

        let k_0 = self.batch[0].subspace_content;

        let fixed_cols = if use_restricted {
            bit_mask_fixed_cols // control on all fixed bits
        } else {
            k_0 & bit_mask_fixed_cols // control only on fixed bits that are set to 1
        };

        self.circuit.push(Gate::EndBatch);

        // For performance reasons write Toffoli over the fixed cols into an ancilla row.
        self.apply_gate(Gate::ToffoliPUIFixed {
            controls: ToffoliControls::new(fixed_cols, k_0),
            k: k_0.value(),
            use_restricted,
        });

        let circ_len = self.circuit.len();
        self.circuit.extend(
            // For simplicity always make the rest a restricted PUI. This only makes a difference in a underfull batch
            // which can only happen for the last batch. This should be neglectable in realistic scenarios.
            self.batch
                .iter()
                .enumerate()
                .map(
                    |(non_subspace_column, batch_element)| Gate::ToffoliPUIRest {
                        target_col: ColumnIndex(non_subspace_column),
                        controls: ToffoliControls::new(
                            bit_mask_changing_cols,
                            batch_element.subspace_content,
                        ),
                        toggle_sign: batch_element.toggle_sign,
                        toggle_extra_col: batch_element.toggle_extra_col,
                    },
                )
                .chain(once(Gate::EndZeroing)),
        );
        self.tableau.apply_circ(&self.circuit[circ_len..]);
    }

    /// Solve the problem by dividing the tableau into subproblems with `sub_problem_size`*256 elemenent
    /// and sequentially solving them. We use multithreading for applying the gates found in a subproblem
    /// to the other subproblems. Doing this multithreading for each gate individually does not work since
    /// individual gates are too cheap compared to the multithreading overhead.
    pub fn run_via_subproblems(&mut self, sub_problem_size: usize) {
        assert!(sub_problem_size < self.tableau.row_storage_len());
        let mut sub_tableaus = self.tableau.decompose(sub_problem_size);

        let mut tableaus_finished: Vec<usize> = Vec::new();

        for i in 0..sub_tableaus.len() {
            let circ_len = self.circuit.len();
            let mut sub_problem = self.create_sub_problem(&mut sub_tableaus[i]);
            sub_problem.run(true);
            // Don't zero the last batch if it is not full.
            // Instead plug it into the next subproblem.

            if sub_problem.k - self.k == sub_problem.tableau.num_rows() as u32 {
                tableaus_finished.push(i);
            }
            self.synchronise_with_sub_problem(sub_problem, (i * sub_problem_size * 256) as u32);

            scope(|s| {
                let circ = &self.circuit[circ_len..];
                for (j, tableau) in sub_tableaus.iter_mut().enumerate() {
                    if j + 1 == i || (j != i && !tableaus_finished.contains(&j)) {
                        // Need j = i -1 for zeroing elements in batch that have not been full.
                        s.spawn(move || {
                            tableau.apply_circ(circ);
                        });
                    }
                }
            });
        }

        self.tableau.recompose(&sub_tableaus);

        // Fix rows that have not been iterated over and were in the subspace at the end of
        // their respective subproblem. Those rows can leak out of the subspace in subsequent subproblems.
        self.run(false);

        self.validate();
    }

    /// Solve the problem. Don't clear the final batch if `is_subproblem` is set. Also do not complete
    /// the bijection in this case.
    pub fn run(&mut self, is_subproblem: bool) {
        let k_start = self.k;

        loop {
            if self.batch.len() == self.max_batch_size() {
                let use_restricted = self.tableau.signs.is_some();
                self.zero_non_subspace_bits(use_restricted);
                self.batch.clear();
            }

            let target_col = ColumnIndex(self.tableau.subspace_bitsize + self.batch.len());

            if let Some(non_zero_el) = self.find_next_non_zero_element(target_col) {
                let target_row = self.create_target_column(target_col, non_zero_el);
                self.format_row_and_add_to_batch(target_row, target_col);
                self.k += 1;
            } else {
                if !self.batch.is_empty() && !is_subproblem {
                    let all_mapped = self.k - k_start == self.tableau.num_rows() as u32;
                    self.zero_non_subspace_bits(!all_mapped);
                    self.batch.clear();
                    if !all_mapped {
                        self.check_and_fix_final_double_element();
                    }
                }
                break;
            }
        }

        if !is_subproblem {
            self.complete_bijection();
            self.validate();
        }
    }

    /// If at the last zeroing not all elements have been mapped into the subspace by the algorithm
    /// or are in the last batch but are there without having been iterated over, it can happen,
    /// that the last element of the batch is |v>|e_k> and there is a state |v>|0>.
    /// After the final zeroing we thus have a state |v>|e_k> outside the subspace.
    /// Check if this is the case and fix it via an X controlled on |v>.
    fn check_and_fix_final_double_element(&mut self) {
        if let Some(non_zero_el) =
            self.find_next_non_zero_element(ColumnIndex(self.tableau.subspace_bitsize))
        {
            assert!(
                self.tableau.signs.is_none(),
                "If there are signs we should iterate over all basis states"
            );
            if let NonZeroElement::Good {
                row: control_row,
                col: control_column,
            } = non_zero_el
            {
                let subspace_bitsize = self.tableau.subspace_bitsize as u8;
                let circ_len = self.circuit.len();

                let free_subspace_val = self.find_free_subspace_val(); // target subspace value for the row.

                self.circuit.extend(
                    free_subspace_val
                        .into_iter()
                        .enumerate()
                        .filter(|(col, target_val)| {
                            self.tableau.get(control_row, ColumnIndex(*col)) != *target_val
                        })
                        .map(|(col, _)| Gate::CX {
                            control: control_column, // Write target subspace value.
                            target: ColumnIndex(col),
                        })
                        .chain([
                            Gate::EndRow,
                            Gate::EndBatch,
                            Gate::ToffoliPUIFixed {
                                // Zero the lone 1 with a multi-controlled X.
                                controls: ToffoliControls::new(
                                    // Make it fit within the existing Gate structure.
                                    BitVec::bit_mask(
                                        ColumnIndex(0),
                                        ColumnIndex(subspace_bitsize as usize),
                                        subspace_bitsize,
                                    ),
                                    free_subspace_val,
                                ),
                                k: free_subspace_val.value(),
                                use_restricted: true,
                            },
                            Gate::ToffoliPUIRest {
                                target_col: ColumnIndex(
                                    control_column.0 - subspace_bitsize as usize,
                                ),
                                controls: ToffoliControls::new(
                                    BitVec::new(0, subspace_bitsize),
                                    BitVec::new(0, subspace_bitsize),
                                ),
                                toggle_sign: false,
                                toggle_extra_col: false,
                            },
                            Gate::EndZeroing,
                        ]),
                );
                self.bijection
                    .push((free_subspace_val.value(), control_row));
                self.tableau.apply_circ(&self.circuit[circ_len..]);
            } else {
                panic!("Should have a good element.")
            }
        }
    }

    /// Find a free value within the subspace, i.e. a |k> such that |k>|?> is not in the tableau.
    fn find_free_subspace_val(&mut self) -> BitVec {
        let missing_rows: HashSet<u32> = self
            .missing_rows()
            .iter()
            .map(|row| {
                BitVec::from_iter(
                    self.tableau
                        .get_row(*row)
                        .take(self.tableau.subspace_bitsize),
                )
                .value()
            })
            .collect();
        BitVec::new(
            (self.k..)
                .find(|subspace_content| !missing_rows.contains(subspace_content))
                .expect("There should be a free value"),
            self.tableau.subspace_bitsize as u8,
        )
    }

    /// Validate that all states are in the subspace.
    /// In case there are signs to fix, check that they have been fixed.
    fn validate(&self) {
        assert!(
            self.tableau.cols[self.tableau.subspace_bitsize..]
                .iter()
                .all(|col| col.is_zero())
        );
        assert_eq!(self.bijection.len(), self.tableau.num_rows());

        if let Some(signs) = self.tableau.signs.as_ref() {
            assert_eq!(self.k as usize, self.tableau.num_rows());
            assert!(signs.signs.is_zero());
            assert!(signs.extra_col.is_zero());
        }
    }

    /// Find the rows which have not yet been in a batch.
    fn missing_rows(&mut self) -> Vec<RowIndex> {
        self.bijection.sort_by_key(|&(_, row_idx)| row_idx);
        let mut i_bij = 0usize;
        (0..self.tableau.num_rows() as u32)
            .map(RowIndex)
            .filter(move |i| {
                if i_bij < self.bijection.len() && self.bijection[i_bij].1 == *i {
                    i_bij += 1;
                    false
                } else {
                    true
                }
            })
            .collect()
    }

    /// Add elements to the bijection which have not been in a batch yet.
    fn complete_bijection(&mut self) {
        if self.bijection.len() < self.tableau.num_rows() {
            let missing_rows = self.missing_rows();
            self.bijection.extend(missing_rows.iter().map(|row| {
                (
                    BitVec::from_iter(
                        self.tableau
                            .get_row(*row)
                            .take(self.tableau.subspace_bitsize),
                    )
                    .value(),
                    *row,
                )
            }));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::super::column::{Column, col_to_col};
    use super::*;

    use numpy::{
        array,
        ndarray::{Array1, Array2},
    };

    #[test]
    fn missing_and_complete_bijection_work() {
        let data: Array2<bool> = array![
            [false, false, false, false],
            [true, true, false, false],
            [false, true, false, false],
            [true, false, false, false],
        ];
        let mut tableau = Tableau::build(data.view(), None);
        let mut prob = Problem::new(&mut tableau);

        prob.bijection = vec![(0, RowIndex(0)), (1, RowIndex(2))];
        prob.k = 2;

        let missing = prob.missing_rows();
        assert_eq!(missing, vec![RowIndex(1), RowIndex(3)]);

        prob.complete_bijection();
        let expected: HashSet<(u32, RowIndex)> = [
            (0, RowIndex(0)),
            (1, RowIndex(2)),
            (2, RowIndex(3)),
            (3, RowIndex(1)),
        ]
        .into_iter()
        .collect();

        let actual: HashSet<(u32, RowIndex)> = prob.bijection.into_iter().collect();
        assert_eq!(expected, actual);
    }

    #[test]
    fn test_good_element() {
        let mut tableau = Tableau::build(
            array![
                [false, false, true, false, false],
                [false, false, true, false, true],
                [true, false, false, false, false],
                [true, false, true, false, false],
            ]
            .view(),
            None,
        );
        let target_column = ColumnIndex(3);
        let mut prob = Problem::new(&mut tableau);
        prob.k = 1;
        prob.batch = vec![BatchElement::new(
            RowIndex(0),
            0,
            false,
            false,
            prob.tableau.subspace_bitsize,
        )];
        let non_zero_el = prob.find_next_non_zero_element(target_column);
        assert_eq!(
            Some(NonZeroElement::Good {
                row: RowIndex(1),
                col: ColumnIndex(4)
            }),
            non_zero_el
        );

        let target_row = prob.create_target_column(target_column, non_zero_el.unwrap());
        let target_tableau = Tableau::build(
            array![
                [false, false, true, false, false],
                [false, false, true, true, false],
                [true, false, false, false, false],
                [true, false, true, false, false],
            ]
            .view(),
            None,
        );
        assert_eq!(target_tableau, *prob.tableau);
        prob.format_row_and_add_to_batch(target_row, target_column);
        assert_eq!(
            BatchElement::new(RowIndex(1), 1, false, false, prob.tableau.subspace_bitsize),
            prob.batch[1]
        );
        prob.k += 1;

        let target_tableau = Tableau::build(
            array![
                [false, false, true, false, false],
                [false, true, false, true, false],
                [true, false, false, false, false],
                [true, false, true, false, false],
            ]
            .view(),
            None,
        );
        assert_eq!(target_tableau, *prob.tableau);
        prob.zero_non_subspace_bits(false);
        let target_tableau = Tableau::build(
            array![
                [false, false, false, false, false],
                [false, true, false, false, false],
                [true, false, true, false, false],
                [true, false, false, false, false],
            ]
            .view(),
            None,
        );
        assert_eq!(target_tableau.cols, prob.tableau.cols);
    }

    #[test]
    fn test_find_bad_next_non_zero_element_and_create_column() {
        let mut tableau = Tableau::build(
            array![
                [false, false, true, false, false],
                [false, true, true, false, false],
                [true, false, false, false, false],
                [true, true, false, false, false],
            ]
            .view(),
            None,
        );
        let mut prob = Problem::new(&mut tableau);
        let target_column = ColumnIndex(3);
        prob.k = 1;
        prob.batch = vec![BatchElement::new(
            RowIndex(0),
            0,
            false,
            false,
            prob.tableau.subspace_bitsize,
        )];
        let non_zero_el = prob.find_next_non_zero_element(target_column);
        assert_eq!(
            Some(NonZeroElement::Bad {
                row: RowIndex(1),
                col: ColumnIndex(2)
            }),
            non_zero_el
        );

        let target_row = prob.create_target_column(target_column, non_zero_el.unwrap());
        let target_tableau = Tableau::build(
            array![
                [false, false, true, false, false],
                [false, true, true, true, false],
                [true, false, false, false, false],
                [true, true, false, false, false],
            ]
            .view(),
            None,
        );
        assert_eq!(target_tableau, *prob.tableau);
        prob.format_row_and_add_to_batch(target_row, target_column);
        assert_eq!(
            BatchElement::new(RowIndex(1), 1, false, false, prob.tableau.subspace_bitsize),
            prob.batch[1]
        );
        prob.k += 1;

        let target_tableau = Tableau::build(
            array![
                [false, false, true, false, false],
                [false, true, false, true, false],
                [true, false, false, false, false],
                [true, true, false, false, false],
            ]
            .view(),
            None,
        );
        assert_eq!(target_tableau, *prob.tableau);
        prob.zero_non_subspace_bits(false);
        let target_tableau = Tableau::build(
            array![
                [false, false, false, false, false],
                [false, true, false, false, false],
                [true, false, true, false, false],
                [true, true, false, true, false],
            ]
            .view(),
            None,
        );
        assert_eq!(target_tableau.cols, prob.tableau.cols);
    }

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
    fn test_find_extra_col_next_non_zero_element_and_create_column() {
        let mut tableau = Tableau::build(
            array![
                [false, false, true, false, false],
                [false, false, false, false, false],
                [true, false, false, false, false],
                [true, true, false, false, false],
            ]
            .view(),
            Some(array![false, true, true, false].view()),
        );
        let target_column = ColumnIndex(3);
        let mut prob = Problem::new(&mut tableau);
        prob.k = 1;
        prob.batch = vec![BatchElement::new(
            RowIndex(0),
            0,
            false,
            true,
            prob.tableau.subspace_bitsize,
        )];
        let non_zero_el = prob.find_next_non_zero_element(target_column);
        assert_eq!(
            Some(NonZeroElement::Extra { row: RowIndex(1) }),
            non_zero_el
        );

        let target_row = prob.create_target_column(target_column, non_zero_el.unwrap());
        let target_tableau = Tableau::build(
            array![
                [false, false, true, false, false],
                [false, false, false, true, false],
                [true, false, false, true, false],
                [true, true, false, true, false],
            ]
            .view(),
            Some(array![false, true, true, false].view()),
        );
        assert_eq!(target_tableau, *prob.tableau);
        prob.format_row_and_add_to_batch(target_row, target_column);
        assert_eq!(
            BatchElement::new(RowIndex(1), 1, true, true, prob.tableau.subspace_bitsize),
            prob.batch[1]
        );
        prob.k += 1;

        let target_tableau = Tableau::build(
            array![
                [false, false, true, false, false],
                [false, true, false, true, false],
                [true, true, false, true, false],
                [true, false, false, true, false],
            ]
            .view(),
            Some(array![false, true, true, false].view()),
        );
        assert_eq!(target_tableau, *prob.tableau);
        prob.zero_non_subspace_bits(true);
        let target_tableau = Tableau::build(
            array![
                [false, false, false, false, false],
                [false, true, false, false, false],
                [true, true, false, true, false],
                [true, false, false, true, false],
            ]
            .view(),
            Some(array![false, false, true, false].view()),
        );
        assert_eq!(target_tableau.cols, prob.tableau.cols);
        assert_eq!(
            target_tableau.signs.as_ref().map(|signs| &signs.signs),
            prob.tableau.signs.as_ref().map(|signs| &signs.signs)
        );
        assert_eq!(
            prob.tableau.signs.as_ref().map(|signs| &signs.extra_col),
            Some(&Column::new(
                col_to_col(array![false, false, true, true].view()),
                4
            ))
        );
    }

    fn validate_bijection(problem: &Problem) {
        for (content, row) in &problem.bijection {
            assert_eq!(
                BitVec::from_iter(
                    problem
                        .tableau
                        .get_row(*row)
                        .take(problem.tableau.subspace_bitsize),
                )
                .value(),
                *content
            )
        }
    }

    #[test]
    fn test_run_with_signs() {
        let mut tableau = Tableau::build(
            array![
                [false, false, false, false, false],
                [false, true, false, false, false],
                [true, true, false, true, true],
                [true, false, false, true, false],
            ]
            .view(),
            Some(array![false, false, true, false].view()),
        );
        let mut prob = Problem::new(&mut tableau);
        prob.run(false);
        validate_bijection(&prob);
    }

    #[test]
    fn test_run_without_signs() {
        let mut tableau = Tableau::build(
            array![
                [false, false, false, false, false],
                [false, true, false, false, false],
                [true, true, false, true, true],
                [true, false, false, true, false],
            ]
            .view(),
            None,
        );
        let mut prob = Problem::new(&mut tableau);
        prob.run(false);
        validate_bijection(&prob);
    }

    #[test]
    fn test_run_via_subproblems() {
        let mut tableau = create_test_tableau();
        let mut prob = Problem::new(&mut tableau);
        prob.run_via_subproblems(1);
        validate_bijection(&prob);
    }

    #[test]
    fn test_double_end_element() {
        let mut tableau = Tableau::build(
            array![
                [false, true, true, false, true, true, true],
                [true, false, false, true, true, true, false],
                [false, false, false, true, true, false, false],
                [false, false, false, true, false, false, true],
                [true, false, false, false, false, true, false],
                [true, true, false, true, true, false, true],
                [false, false, true, false, true, true, false],
                [false, true, true, true, false, true, true],
                [true, true, true, false, true, true, false],
                [true, true, true, false, true, true, true]
            ]
            .view(),
            None,
        );
        let mut prob = Problem::new(&mut tableau);
        prob.run(false);
        validate_bijection(&prob);
    }
}
