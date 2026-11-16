# Quantum Implementation Methodology — SIRIUS

**Implementation Reference:** Felix Rupprecht and Sabine Wölk (2026), *Sparse quantum state preparation with improved Toffoli cost*, Quantum 10, 2208. DOI: [10.22331/q-2026-09-10-2208](https://doi.org/10.22331/q-2026-09-10-2208)

---

## 1. Problem Formulation

The goal is to prepare an arbitrary $s$-sparse quantum state $|\psi\rangle$ on $n$ data qubits:

\[
|\psi\rangle = \sum_{i=0}^{s-1} a_i c_i |x_i\rangle
\]

where:
- $\mathcal{S} = \{x_0, x_1, \dots, x_{s-1}\} \subset \{0, 1\}^n$ is the support set of $s$ pairwise distinct $n$-bit computational-basis states.
- $c_i \in \mathbb{C}$ are arbitrary complex coefficients satisfying $\sum_{i=0}^{s-1} |c_i|^2 = 1$.
- $a_i \in \{+1, -1\}$ are optional real-sign metadata (useful in Hamiltonian simulation and real-state embedding).
- $\ell = \lceil \log_2(s) \rceil$ denotes the subspace register width.
- $r = n - \ell$ denotes the residual register width.

The $n$ data qubits are partitioned into:
1. **Subspace register:** wires $0, \dots, \ell - 1$.
2. **Residual register:** wires $\ell, \dots, n - 1$.

Big-endian bit ordering is maintained throughout: wire 0 corresponds to the most significant bit.

---

## 2. Isometry Finding: Malvetti Baseline vs. Batched Isometry

### 2.1 Malvetti et al. Baseline
The sequential isometry baseline operates row-by-row on the target basis states. For each basis state $|x_i\rangle$:
1. Identifies if the state is already in the subspace ($x_{i,\ell \dots n-1} = 0$).
2. If not, uses multi-target CX gates to match its subspace prefix to an unused address $f(i) \in \{0, \dots, 2^\ell - 1\}$.
3. Emits an $\ell$-controlled X gate targeting the residual wire to zero out the residual bit.
4. Worst-case Toffoli cost: $s(\ell - 1)$ using an AND-ladder with $\ell - 2$ clean ancillas.

### 2.2 Rupprecht & Wölk Batched Isometry
Instead of individual controlled-X operations, Rupprecht & Wölk group basis states into batches of size at most $2^r$. By leveraging Partial Unary Iteration (PUI), multiple states are zeroed simultaneously:
- Partitions the support $\mathcal{S}$ into batches that share residual patterns or address intervals.
- Constructs reversible PUI trees over address ranges $[a, b] \subseteq [0, 2^\ell - 1]$.
- Employs two types of PUI operations:
  - **Unrestricted PUI:** Maps intervals when extra addresses outside the active support are available. Cost is upper-bounded by $2(b - a)$ Toffolis (Equation 7 of paper).
  - **Restricted PUI:** Strict interval isolation without polluting unallocated address space. Cost is upper-bounded by $4(b - a)$ Toffolis (Equation 8 of paper).

---

## 3. PUI Tree Synthesis (`pui_tree.py`)

A PUI tree recursively splits the address interval $[a, b]$ into left and right subtrees:
- Evaluates tree split points aligned with powers of two.
- Uses depth-reused clean ancillas (at most $w - 1$ ancillas for interval width $w = \lceil \log_2(b - a + 1) \rceil$).
- Uncomputes intermediate ladder ancillas deterministically, ensuring that every workspace qubit returns to $|0\rangle$.
- Emits exact reversible gate sequences consisting of `X`, `CX`, `Toffoli`, and negative-control Toffoli gates.

---

## 4. Algorithm 3: Sign- and Marker-Aware Construction (`algorithm3.py`)

Algorithm 3 from Rupprecht & Wölk integrates real-sign handling directly into the batched isometry:
1. Divides the support into positive ($a_i = +1$) and negative ($a_i = -1$) subsets.
2. Allocates a marker ancilla wire $|m\rangle$ initialized to $|0\rangle$.
3. When zeroing residual wires, flips the marker wire for negative states.
4. Applies a single $Z$ gate on the marker wire to imprint the $(-1)$ phase simultaneously across all negative states.
5. Inverts the marker entangling sequence to uncompute $|m\rangle$ back to $|0\rangle$.

---

## 5. Phase Synthesis (`phase_synthesis.py`)

When complex phases or non-subspace signs cannot be eliminated by Algorithm 3:
1. Synthesizes a diagonal phase oracle $U_\phi$ implementing:
   \[
   U_\phi |x\rangle = e^{i \phi(x)} |x\rangle
   \]
2. Real signs ($\pm 1$) are implemented using multi-controlled $Z$ operations decomposed into clean-ancilla ladders.
3. Complex coefficient phases $\arg(c_i)$ are applied via controlled phase rotations on the compact address register during dense state loading.

---

## 6. End-to-End Logical Preparation Pipeline (`state_preparation.py`)

The full state preparation circuit $U_{prep}$ acts on $|0\rangle^{\otimes n} |0\rangle^{\otimes m_{anc}}$:

\[
U_{prep} |0\rangle^{\otimes n} |0\rangle^{\otimes m_{anc}} = |\psi\rangle |0\rangle^{\otimes m_{anc}}
\]

Pipeline execution stages:
1. **Dense Subspace Loading:**
   Prepares the normalized compact state $\sum_{i=0}^{s-1} |c_i| |f(i)\rangle$ on the $\ell$ subspace qubits via a tree of Givens rotations ($R_y$ gates).
2. **Phase Injection:**
   Applies diagonal phases: $\theta_i = \arg(c_i)$ and real-sign oracle $a_i$.
3. **Isometry Expansion ($G^\dagger$):**
   Applies the inverse of the batched isometry $G$, mapping compact labels $|f(i)\rangle|0^r\rangle \mapsto |x_i\rangle$.
4. **Workspace Uncomputation:**
   Verifies all auxiliary, ladder, and marker qubits return to $|0\rangle$.

---

## 7. Verification Methodology

Verification operates on three independent levels:

1. **Tableau Invariant Verification:**
   Checks that the forward circuit $G$ maps all $s$ support states injectively into the subspace register ($x_{i, \ell \dots n-1} = 0$) and that $G^\dagger G = I$.
2. **CPU Exact Statevector Verification:**
   Computes the full $2^n$ statevector for instances where $n + m_{anc} \le 20$.
   Computes fidelity:
   \[
   F = |\langle \psi_{target} | \psi_{prepared} \rangle|^2 \ge 1 - 10^{-7}
   \]
   Verifies zero probability leakage outside support and zero workspace leakage.
3. **GPU Basis-Batch Parity:**
   Validates that the CuPy uint64 batch simulator matches CPU basis-state simulation for arbitrary batches of input words up to $n = 63$.
