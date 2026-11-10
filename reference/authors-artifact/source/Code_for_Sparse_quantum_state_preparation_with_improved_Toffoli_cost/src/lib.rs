// SPDX-FileCopyrightText: 2025 German Aerospace Center (DLR)
//
// SPDX-License-Identifier: Apache-2.0

use numpy::{PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;

mod isometry_algorithms;
use isometry_algorithms::{gates::Gate, problem::Problem, tableau::Tableau};

type BijectionWithCircuit = (Vec<[u32; 2]>, Vec<(BatchCreationData, BatchZeroingData)>);

/// Find the bijection and the circuit mapping the ``state`` into a
/// logarithmically sized subspace and fixing the ``signs`` if there are any.
///
/// Parameters
/// ----------
/// - state : np.ndarray:
///     A 2-D ``numpy`` array of ``bool`` representing the tableau
///     (rows x columns).
/// - signs : np.ndarray | None:
///     Optional 1-D ``numpy`` array of ``bool`` containing the
///     sign information for each row.
/// - sub_problem_size : int | None:
///     Optional integer controlling the sub-problem sizes used by the
///     underlying classical algorithm.  When omitted the algorithm runs in a
///     single pass.
///
/// Returns
/// -------
/// - tuple[list[int], list[Tuple[BatchCreationData, BatchZeroingData]]]:
///     - bijection - a list of pairs ``(subspace_content, row)``
///     where ``subspace_content`` is the content ``|subspabe_content>``
///     of the subspace at the end of the algorithm and ``row`` is the
///     index of the original basis vector in the tableau.
///     - circuit - a list of batches.  Each batch is a tuple
///     ``(BatchCreationData, BatchZeroingData)`` describing how to create
///     and subsequently zero the batch.
#[pyfunction]
fn find_bijection_and_circuit(
    state: PyReadonlyArray2<bool>,
    signs: Option<PyReadonlyArray1<bool>>,
    sub_problem_size: Option<usize>,
) -> BijectionWithCircuit {
    let mut tableau = Tableau::build(
        state.as_array(),
        signs.as_ref().map(|signs| signs.as_array()),
    );
    let mut problem = Problem::new(&mut tableau);

    if let Some(sub_problem_size) = sub_problem_size {
        problem.run_via_subproblems(sub_problem_size);
    } else {
        problem.run(false);
    };

    problem
        .bijection
        .sort_by_key(|&(subspace_content, _)| subspace_content);

    let bijection = problem
        .bijection
        .iter()
        .map(|(subspace_content, row)| [*subspace_content, row.0])
        .collect();

    (bijection, parse_circuit(&problem.circuit))
}

#[pyfunction]
/// Return an upper-bound estimate of the total number of Toffoli gates needed.
///
/// The function walks through a quantum-circuit description (a list of
/// ``(create_batch, zero_batch)`` tuples) and adds together the Toffoli-gate
/// counts reported by each batch.  The result is only an upper bound.
///
/// Parameters
/// ----------
/// - circuit : list[tuple[BatchCreationData, BatchZeroingData]] :
///     A list representing the quantum circuit.  Each element is a two-item
///     tuple:
///
///     -  ``create_batch`` - an instance of :class:`BatchCreationData` that
///     knows how many Toffoli gates are required to create the batch.
///     -  ``zero_batch`` - an instance of :class:`BatchZeroingData` that knows
///     how many Toffoli gates are required to reset (zero) the batch.
///
/// Returns
/// -------
/// - int:
///     The summed upper-bound count of Toffoli gates for the whole circuit.
///
fn fast_toffoli_counter(circuit: Vec<(BatchCreationData, BatchZeroingData)>) -> usize {
    circuit
        .iter()
        .map(|(create_batch, zero_batch)| create_batch.num_toffolis() + zero_batch.num_toffolis())
        .sum()
}

/// For performance reasons we store the circuit in the classical algorithm as a list of gates that are small and can be inlined.
/// However for further processing within Qualtran we want the circuit to be represented by larger bloqs.
fn parse_circuit(circuit: &[Gate]) -> Vec<(BatchCreationData, BatchZeroingData)> {
    circuit
        .split(|gate| *gate == Gate::EndZeroing)
        .filter(|batch| !batch.is_empty())
        .map(|batch| {
            let mut parts = batch.split(|gate| *gate == Gate::EndBatch);
            let pivoting = parts.next().expect("Should have a pivoting part");
            let zeroing = parts.next().expect("Should have a zeroing part");
            (
                BatchCreationData::build(pivoting),
                BatchZeroingData::build(zeroing),
            )
        })
        .collect()
}

/// Types of fixes that may be applied to create a target column
/// that has a non-zero element.
#[pyclass(eq, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ColumnFix {
    /// Swap the target column with a non-trivial column.
    Swap(usize),
    /// Apply a Toffoli with the target column as target and
    /// one column with positive control and another column with positive
    /// or negative control.
    Toffoli {
        control0: usize,
        control1: (usize, bool),
    },
    /// Apply first a CX gate controlled on the extra column on the
    /// target column. Then fix potential bit flips in batch columns
    /// by applying CX gates with controls on the respective target columns
    /// of those batch elements on the target column.
    ExtraCX(Vec<usize>),
}

impl ColumnFix {
    /// Get the number of Toffoli gates required for the fix.
    fn num_toffolis(&self) -> usize {
        match self {
            Self::Toffoli {
                control0: _,
                control1: _,
            } => 1,
            _ => 0,
        }
    }
}

/// Store data for preapring a row.
#[pyclass(eq, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct PrepareRowData {
    /// Target column, i.e. a column with a non-zero element
    /// we can use as the control to write the desired row content.
    #[pyo3(get)]
    pub target_column: usize,
    /// A potentially needed fix to create the target column.
    #[pyo3(get)]
    pub column_fix: Option<ColumnFix>,
    /// Rows we need to toggle controlled on target_column such that
    /// we get the correct row content.
    #[pyo3(get)]
    pub toggles: Vec<usize>,
}

impl PrepareRowData {
    /// Parse a slice of `gates` that prepare a row.
    fn build(gates: &[Gate]) -> Option<Self> {
        if gates.is_empty() {
            return None;
        }

        // Find a potentially needed column fix, i.e. a a gate such that there is a non-zero element in the target column.
        let (target_column, mut column_fix) = match gates[0] {
            Gate::Swap { target, non_target } => (target.0, Some(ColumnFix::Swap(non_target.0))),
            Gate::Toffoli {
                target,
                control_positive,
                control_with_bool,
            } => (
                target.0,
                Some(ColumnFix::Toffoli {
                    control0: control_positive.0,
                    control1: (control_with_bool.0.0, control_with_bool.1),
                }),
            ),
            Gate::CXExtra(target) => (target.0, Some(ColumnFix::ExtraCX(Vec::new()))),
            Gate::CX { target: _, control } => (control.0, None), // No fix required.
            _ => panic!("Should be one of the gates from above."),
        };

        // If a CX from the extra column to the target column was applied
        // we might need to fix rows that are already in the batch.
        if let Some(ColumnFix::ExtraCX(controls)) = column_fix.as_mut() {
            controls.extend(gates[1..].iter().filter_map(|gate| {
                if let Gate::CX {
                    target: t,
                    control: c,
                } = gate
                    && t.0 == target_column
                {
                    Some(c.0)
                } else {
                    None
                }
            }));
        }

        // Columns for CXs controlled on the target column to write the correct row content.
        let toggles = gates
            .iter()
            .filter_map(|gate| {
                if let Gate::CX {
                    target: t,
                    control: c,
                } = gate
                    && c.0 == target_column
                {
                    Some(t.0)
                } else {
                    None
                }
            })
            .collect();

        Some(Self {
            target_column,
            column_fix,
            toggles,
        })
    }

    /// Get the number of Toffoli gates required for row creation.
    fn num_toffolis(&self) -> usize {
        self.column_fix
            .as_ref()
            .map(|fix| fix.num_toffolis())
            .unwrap_or_default()
    }
}

#[pymethods]
impl PrepareRowData {
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!("{:?}", self))
    }
}

/// Store data for creating a batch.
#[pyclass(eq, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct BatchCreationData {
    /// Row preparations needed for creating a batch.
    /// If for a row we do not need to do anything store None.
    #[pyo3(get)]
    pub rows_preparations: Vec<Option<PrepareRowData>>,
}

impl BatchCreationData {
    /// Parse a slice of `gates` that create a batch.
    fn build(gates: &[Gate]) -> Self {
        Self {
            rows_preparations: gates
                .split(|gate| *gate == Gate::EndRow)
                .map(PrepareRowData::build)
                .collect(),
        }
    }

    /// Get the number of Toffoli gates required for batch creation.
    fn num_toffolis(&self) -> usize {
        self.rows_preparations
            .iter()
            .map(|row_prep| {
                row_prep
                    .as_ref()
                    .map(|row| row.num_toffolis())
                    .unwrap_or_default()
            })
            .sum()
    }
}

#[pymethods]
impl BatchCreationData {
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!("{:?}", self))
    }
}

/// Store data for zeroing a batch.
#[pyclass(eq, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct BatchZeroingData {
    /// Iterval start of the PUI.
    #[pyo3(get)]
    pub interval_start: u32,

    /// Control qubits and control values that are
    /// fixed for all elements in the batch.
    #[pyo3(get)]
    pub fixed: Vec<(usize, bool)>,

    /// Operations to apply. First element is the qubit to toggle,
    /// Second entry indicates whether to apply a sign-flip and
    /// the last element whether to toggle the extra qubit.
    #[pyo3(get)]
    pub operations: Vec<(usize, bool, bool)>,

    /// Indicates whether the PUI is restricted or not.
    #[pyo3(get)]
    pub restricted: bool,
}

#[pymethods]
impl BatchZeroingData {
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!("{:?}", self))
    }
}

impl BatchZeroingData {
    /// Parse a slice of `gates` that zero a batch.
    fn build(zeroing_gates: &[Gate]) -> Self {
        let (interval_start, restricted, fixed) = if let Gate::ToffoliPUIFixed {
            controls,
            k,
            use_restricted,
        } = zeroing_gates[0]
        {
            (
                k,
                use_restricted,
                controls
                    .controls()
                    .map(|(column, positive)| (column.0, positive))
                    .collect(),
            )
        } else {
            panic!("First zeroing gate needs to be a ToffoliPUIFixed.")
        };

        let operations = zeroing_gates[1..]
            .iter()
            .map(|gate| {
                if let Gate::ToffoliPUIRest {
                    target_col,
                    controls: _,
                    toggle_sign,
                    toggle_extra_col,
                } = gate
                {
                    (target_col.0, *toggle_sign, *toggle_extra_col)
                } else {
                    panic!("Can only have ToffoliPUIRest gates.")
                }
            })
            .collect();

        Self {
            interval_start,
            operations,
            restricted,
            fixed,
        }
    }

    /// Get an upper bound on the number of Toffoli gates required for batch zeroing.
    fn num_toffolis(&self) -> usize {
        let fixed_len = self.fixed.len();
        let changing_size = self.operations.len().next_power_of_two();

        if fixed_len == 0 {
            changing_size - 2
        } else {
            fixed_len - 1 + changing_size - 1
        }
    }
}

#[pymodule]
fn _isometry_algorithms(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(find_bijection_and_circuit, m)?)?;
    m.add_function(wrap_pyfunction!(fast_toffoli_counter, m)?)?;
    m.add_class::<PrepareRowData>()?;
    m.add_class::<BatchCreationData>()?;
    m.add_class::<BatchZeroingData>()?;
    m.add_class::<ColumnFix>()?;
    Ok(())
}
