---
title: "Sparse Quantum State Preparation with Improved Toffoli Cost — Master Study Guide"
source: "Rupprecht & Wölk, Quantum (2026), 22-page PDF supplied by the user"
format: "Interactive Markdown study guide"
---

# Sparse Quantum State Preparation with Improved Toffoli Cost

## A page-by-page, derivation-first guide for a first quantum-computing research project

**Primary source:** Felix Rupprecht and Sabine Wölk, *Sparse quantum state preparation with improved Toffoli cost*, 22-page PDF supplied with this conversation. References such as `PDF p. 6` below mean the page number printed in that PDF, not an unrelated web version.

**Original PDF included in this bundle:** [source_paper.pdf](source_paper.pdf). The page images below are rendered from this exact PDF; use the PDF for sharp zooming and selectable text.

**Level:** A mathematically careful first pass for a student who knows basic algebra and binary numbers, but may not yet be comfortable with quantum circuits, reversible logic, or fault-tolerant resource estimates.

**What this guide is trying to achieve:** by the end, you should be able to explain the paper's problem, reconstruct its circuit logic, derive its central resource bounds, distinguish theorems from numerical observations, explain the implementation assumptions, and identify what the paper does *not* establish.

> **Reading rule:** do not treat a highlighted equation as understood until you can explain every symbol, say what is being counted, state the assumptions, and reproduce at least one numerical example without looking.

---

## How to use this interactive Markdown file

This file uses ordinary Markdown, LaTeX mathematics, task-list checkboxes, Mermaid diagrams, and collapsible `<details>` sections. It works best in a Markdown viewer that supports LaTeX math and HTML details (for example, a modern GitHub or Obsidian view). A plain-text editor will still show all explanations, but the collapsible answers will appear as raw markup.

- Check a box only after you can do the task without copying.
- Open a **Derivation / answer** section only after attempting it yourself.
- Use the PDF beside this guide whenever a circuit figure is discussed. The guide explains what the figure means; it does not replace the source diagram.
- If a statement is marked **Paper statement**, it is what the paper says. If it is marked **Teaching interpretation**, it is an explanation added here to make the statement understandable.
- If something in the PDF appears internally inconsistent, it is called out explicitly in the source-consistency section. It is not silently repaired.

### Navigation

1. [The paper in 90 seconds](#1-the-paper-in-90-seconds)
2. [Prerequisites and notation](#2-prerequisites-and-notation)
3. [Page-by-page walkthrough](#3-page-by-page-walkthrough)
4. [Derivation workbook](#4-derivation-workbook)
5. [Assumptions, scope, and source-consistency checks](#5-assumptions-scope-and-source-consistency-checks)
6. [Implementation and reproduction checklist](#6-implementation-and-reproduction-checklist)
7. [Mastery examination](#7-mastery-examination)
8. [References: short summary and why each is cited](#8-references-short-summary-and-why-each-is-cited)
9. [Glossary](#9-glossary)

---

# 1. The paper in 90 seconds

The paper studies how to prepare a quantum state that has only a small number of non-zero computational-basis amplitudes.

An `n`-qubit register has `2^n` computational-basis states. A state is called `s`-sparse when only `s` of those basis states have non-zero amplitudes, with `s` much smaller than `2^n`:

$$
|\Theta\rangle=\sum_{i=0}^{s-1}c_i|C_i\rangle,
\qquad s\ll 2^n.
$$

The paper follows a two-stage architecture:

1. Prepare the coefficients in a compact register of
   $$\ell=\lceil\log_2 s\rceil$$
   qubits.
2. Expand that compact representation into the desired `n`-qubit basis strings using an isometry.

The paper's main improvement is in the **isometry**. Earlier sparse-isometry methods can zero the non-subspace part of each basis state separately, using a multi-controlled-X. Rupprecht and Wölk organize states into batches and use **partial unary iteration (PUI)** to zero a whole batch more efficiently.

The main worst-case isometry bound is Equation (1), on PDF page 3:

$$
\boxed{
T_{\mathrm{iso}}\leq
\left\lceil\frac{s}{m}\right\rceil
\left(2m+\frac12\log_2\frac{\widetilde{s}}{m}-3\right)
+
\log_2\left(\frac{\widetilde{s}^{3/2}}{2\sqrt m}\right)
}
\tag{1}
$$

where

$$
\ell=\lceil\log_2s\rceil,
\qquad \widetilde{s}=2^\ell,
\qquad
m=\max\{2^p:2^p\leq n-\ell\}.
$$

For sufficiently large available `n`, the leading term behaves like `2s`. In numerical tests on random sparse states, the measured isometry cost approaches `s`. Those are **not the same claim**: `2s` is the leading behaviour of an analytical worst-case upper bound; `s` is an empirical trend for the tested random instances.

The paper then optimizes the *whole* preparation circuit. It studies Grover–Rudolph-style dense-state preparation, QROM/QROAM data loading, measurement-induced sign correction, and a special optimization when the target coefficients are purely real.

## What the paper does not claim

- It does not claim that every sparse state costs exactly `s` Toffolis.
- It does not claim the full end-to-end preparation cost is always `2s`.
- It does not optimize every possible hardware metric; its principal metrics are Toffoli count and qubit count.
- It does not provide a universal runtime guarantee for a physical quantum processor.
- Its classical isometry-finding algorithm has a separate stated complexity, `O(s^2 n)`; quantum gate count and classical preprocessing time must not be conflated.

---

# 2. Prerequisites and notation

This chapter is deliberately before the page-by-page reading. The paper uses these ideas without teaching them from first principles.

## 2.1 Classical bitstrings and computational-basis states

A classical bitstring of length `n` is a sequence such as:

$$
10110.
$$

An `n`-qubit computational-basis state uses the same bit pattern, written as a ket:

$$
|10110\rangle.
$$

For `n` qubits there are `2^n` such basis states. For example, three qubits have:

$$
|000\rangle,|001\rangle,|010\rangle,|011\rangle,
|100\rangle,|101\rangle,|110\rangle,|111\rangle.
$$

The paper uses big-endian ordering for address intervals: the leftmost bit is the most significant bit. Thus `|100> = |4>` for a three-bit address register.

## 2.2 Superposition, amplitudes, and normalization

A general two-qubit pure state can be written as:

$$
|\psi\rangle=a|00\rangle+b|01\rangle+c|10\rangle+d|11\rangle.
$$

The coefficients `a,b,c,d` are complex amplitudes. Their squared absolute values are measurement probabilities:

$$
P(00)=|a|^2.
$$

A valid state is normalized:

$$
|a|^2+|b|^2+|c|^2+|d|^2=1.
$$

For the paper, the target is

$$
|\Theta\rangle=\sum_{i=0}^{s-1}c_i|C_i\rangle,
\qquad \sum_i|c_i|^2=1,
$$
where the `|C_i>` are distinct computational-basis states and exactly `s` coefficients are non-zero.

**Why distinct basis states matter:** the support of a state is a set of distinct computational-basis labels. Repeating the same basis state in a list would require combining its coefficients before counting `s`.

## 2.3 What “sparse” means here

The full Hilbert space has dimension `2^n`, but the target state has support size `s`:

$$
s\ll 2^n.
$$

For example, when `n=8`, the system has 256 basis states. If only four coefficients are non-zero, then `s=4` and the state is sparse.

Do not confuse:

- **Hilbert-space dimension:** `2^n`.
- **Number of non-zero amplitudes:** `s`.
- **Number of qubits needed to label `s` objects:** `ell = ceil(log_2 s)`.

## 2.4 Why `ceil(log2(s))` qubits are enough to label `s` states

A register of `ell` qubits has `2^ell` possible bitstrings. We need at least `s` distinct labels, so choose the smallest integer `ell` satisfying:

$$
2^\ell\geq s.
$$

Taking base-two logarithms gives:

$$
\ell\geq\log_2s.
$$

The smallest integer that satisfies this is:

$$
\boxed{\ell=\lceil\log_2s\rceil.}
$$

The register may have unused labels when `s` is not a power of two. The paper therefore defines:

$$
\widetilde{s}=2^\ell.
$$

Example: `s=13` gives `ell=4` and `tilde{s}=16`. There are 16 available labels, of which 13 are used.

## 2.5 The two registers: subspace and non-subspace

Every target bitstring is split after its first `ell` bits:

$$
|C_i\rangle=|C_i'\rangle_s|C_i''\rangle_r.
$$

- `|C_i'>_s` is the `ell`-qubit **subspace register**.
- `|C_i''>_r` is the remaining `(n-ell)`-qubit **non-subspace register**.

The subscripts `s` and `r` here label registers. They are not multiplication by the sparsity `s` or residual variable `r`.

The isometry-construction algorithm tries to transform every target basis state into:

$$
|f(i)\rangle_s|0\rangle_r.
$$

All information needed to distinguish the target basis states is then in the compact subspace label; the residual register is zero.

### Small register-splitting example

Let `n=6` and `s=4`. Then:

$$
\ell=\lceil\log_2 4\rceil=2.
$$

Every six-bit basis state is split into a two-bit subspace part and a four-bit residual part:

```text
six-bit basis string
┌──────────────┬─────────────────────┐
│ first 2 bits │ remaining 4 bits    │
│ subspace     │ non-subspace        │
└──────────────┴─────────────────────┘
```

For example:

$$
|101011\rangle=|10\rangle_s|1011\rangle_r.
$$

The desired compressed form has the same two-bit label register but four zero residual bits, e.g. `|01>_s|0000>_r` for whichever unique label the algorithm assigns.

## 2.6 Bijection: why the mapping can be chosen

A bijection is a one-to-one correspondence. Here the paper defines a mapping

$$
f:[s]\longrightarrow S\subseteq[2^\ell],
$$

where `[s] = {0,1,...,s-1}` and `S` is a set of `s` distinct compact labels.

The `i`-th target state is assigned the compact label `f(i)`. The coefficient `c_i` stays attached to that target state; the labels are only a representation choice.

**Why this freedom helps:** the algorithm can choose labels that make the reversible basis-state transformation cheaper. If it were forced to preserve an arbitrary pre-existing numbering, it could need to implement a more complicated permutation.

## 2.7 Isometry versus unitary: the direction is easy to mix up

An isometry preserves inner products while embedding one space (or subspace) into another. A quantum circuit on a fixed register is unitary, but its action restricted to the relevant subspace can implement the required isometric embedding.

There are two directions in this paper:

**Direction used by the classical circuit-finding algorithm in Section 2:**

$$
G|C_i\rangle=|f(i)\rangle_s|0\rangle_r.
$$

This maps target states *into* the compact subspace.

**Direction used for actual sparse-state preparation:**

$$
G^\dagger\bigl(|f(i)\rangle_s|0\rangle_r\bigr)=|C_i\rangle.
$$

This is the inverse mapping: it expands the compact prepared state into the target basis strings.

The linearity check is:

$$
G|\Theta\rangle
=G\sum_i c_i|C_i\rangle
=\sum_i c_iG|C_i\rangle
=\sum_i c_i|f(i)\rangle_s|0\rangle_r
=|\theta\rangle_s|0\rangle_r.
$$

Therefore:

$$
\boxed{G^\dagger(|\theta\rangle_s|0\rangle_r)=|\Theta\rangle.}
$$

This is the cleanest way to remember the direction: **the paper's classical algorithm finds `G`; the preparation circuit uses `G†`.**

## 2.8 Gates used in the paper

### X gate

The Pauli-X gate flips a computational-basis bit:

$$
X|0\rangle=|1\rangle,\qquad X|1\rangle=|0\rangle.
$$

### CNOT / CX

A CNOT flips a target bit when the control bit is 1:

$$
|a,t\rangle\mapsto|a,t\oplus a\rangle.
$$

### Toffoli / CCX

A Toffoli has two control bits and one target bit:

$$
|a,b,t\rangle\mapsto|a,b,t\oplus(a\land b)\rangle.
$$

The target flips only when both controls are 1. A negative control means the operation fires when that control is 0; it can be implemented by surrounding the control with X gates.

### Multi-controlled X (MCX)

An MCX has more than two controls and one target. The paper decomposes these using AND/Toffoli constructions. The exact cost depends on the number of controls and the available ancillas.

### Multi-target controlled-X (CMX)

A CMX has one control and several targets. If the control is 1, all selected targets are flipped. Figure 5 uses this to change several bits of a selected row in one controlled operation.

The PDF caption for Figure 5 says the upper indices label target qubits and lower indices label control qubits.

### AND with a clean ancilla

The reversible AND primitive used in unary iteration is:

$$
|a\rangle|b\rangle|0\rangle\longmapsto
|a\rangle|b\rangle|a\land b\rangle.
$$

The third qubit stores the AND of the first two. This is a Toffoli acting on a clean target ancilla.

## 2.9 Ancillas and uncomputation

An **ancilla** is a workspace qubit. A clean ancilla begins in a known state, usually `|0>`. A dirty ancilla may begin in an unknown state, but a valid construction must account for it and preserve the required input/output behaviour.

When a circuit computes a temporary condition into an ancilla, it often must erase that temporary information before returning the ancilla to its required state. Reversing the computation is called **uncomputation**.

The paper uses measurement-based uncomputation for the adjoint of its AND primitive. Under the paper's resource accounting, that adjoint can be implemented with zero additional Toffoli cost. This does **not** mean the ancilla is simply discarded: the measurement and correction procedure is what makes the cleanup valid.

## 2.10 Why Toffoli count is the metric

The authors decompose circuits into a Clifford+Toffoli gate set and count:

1. Toffoli gates.
2. Qubits required.

In fault-tolerant quantum computing, non-Clifford resources such as T/CCZ states are usually more demanding to prepare than Clifford operations. The paper therefore treats Toffoli count as a useful resource proxy. It also cautions in the conclusion that future hardware and magic-state advances may make Toffoli count alone an incomplete proxy for runtime.

**Do not overstate this:** a lower Toffoli count is a resource improvement under the paper's model. It is not automatically proof of lower wall-clock runtime on every architecture.

## 2.11 Notation collisions to watch for

The paper reuses a few letters in different sections. This guide uses extra names where necessary.

| Symbol in paper | Meaning in context | Potential confusion |
|---|---|---|
| `s` | Sparsity / number of target basis states | Also appears as a register subscript in `|C'>_s` |
| `ell` | Usually `ceil(log2 s)`, subspace width | Section 3 also uses a similar glyph as an exponent for `m=2^ell` |
| `m` | Batch size; a power of two no larger than `n-ell` | Not the number of batch elements if the final batch is incomplete |
| `w` | Number of address-register qubits in Section 3 | In the isometry application, `w=ceil(log2 s)` |
| `S` | Full address space size `2^w` in Section 3 | The image of the bijection is also denoted by `S` in Section 1 |
| `r` | Non-subspace-register label, interval endpoint, or QROAM parameter depending on context | Always read the local definition |
| `b` | Current batch size in Algorithm 1, or angle-precision bits in Section 4 | These are different variables |

For derivations in this guide, `q=log2(m)` is used for the PUI subtree depth, to avoid confusing it with the subspace width `ell`.

---

# 3. Page-by-page walkthrough

Each section follows this pattern:

1. **What the page says.**
2. **Why the authors need it.**
3. **How to read the equations or figures.**
4. **What you should be able to explain afterward.**

## PDF page 1 — Title, abstract, and research objective

<details>
<summary><strong>Open the original supplied PDF page 1 / 22</strong></summary>

![Original PDF page 1](assets/pdf_page_01.png)

</details>


### 3.1 What the page says

The authors are Felix Rupprecht and Sabine Wölk. Their affiliations are the Institute of Quantum Technologies at the German Aerospace Center and the Center for Integrated Quantum Science and Technology at Ulm University.

The abstract says that sparse-state preparation is useful for quantum simulation and linear-system algorithms. The paper proposes an improved way to prepare an `s`-sparse state on `n` qubits, reducing the Toffoli cost compared with earlier methods.

The abstract presents four central points:

1. The state has only `s` non-zero computational-basis amplitudes.
2. The algorithm first prepares a state on an `ell=ceil(log2 s)`-qubit sub-register.
3. It then maps that compact state into the target state through an isometry.
4. The authors improve the isometry by constructing it more efficiently.

### 3.2 Why sparse states matter

The state space grows exponentially with the number of qubits. A generic `n`-qubit state can have support on all `2^n` basis strings. A sparse state may use only `s` strings.

The algorithm's opportunity is not that the computer has fewer physical qubits; it is that the target state's *support* has a compact set of labels.

### 3.3 Why Toffoli, not just CNOT count?

The introduction distinguishes gate-count objectives. Some prior work optimizes one- and two-qubit gates or circuit depth. This paper focuses on fault-tolerant non-Clifford resource estimates. Toffoli and T gates are connected to CCZ/T resource states and magic-state production, which can be expensive in fault-tolerant architectures.

The authors also note a relationship between T and CCZ resource states in reference [19]. The point is not that every hardware platform has one fixed conversion ratio; it is that Toffoli/T counts are meaningful non-Clifford cost measures under the paper's model.

### 3.4 The paper's exact target

The target is:

$$
|\Theta\rangle=\sum_{i=0}^{s-1}c_i|C_i\rangle.
$$

The `|C_i>` are computational-basis states and `c_i` are their amplitudes. Sparsity means `s` is much smaller than `2^n`.

### 3.5 The result preview

The abstract says that the isometry's worst-case Toffoli cost is essentially `2s` for sufficiently large `n`. It also says random numerical benchmarks tend toward `s`.

Keep the distinction precise:

- **Worst-case bound:** analytical, valid for the stated construction and assumptions.
- **Random-instance behaviour:** observed in numerical experiments, not a universal worst-case theorem.

### Checkpoint — page 1

- [ ] I can define an `s`-sparse state.
- [ ] I can say why `ell=ceil(log2 s)` is enough to label its support.
- [ ] I can explain why the paper counts Toffolis and qubits.
- [ ] I can distinguish a worst-case bound from a numerical trend.

<details>
<summary><strong>Test yourself: what is the paper actually optimizing?</strong></summary>

It is optimizing the number of Toffoli gates and the number of qubits required for sparse-state preparation under the paper's fault-tolerant resource model. It is not directly optimizing every physical runtime or noise metric.
</details>

---

## PDF page 2 — Figure 1, previous approaches, and Figure 2

<details>
<summary><strong>Open the original supplied PDF page 2 / 22</strong></summary>

![Original PDF page 2](assets/pdf_page_02.png)

</details>


### 3.6 Figure 1: two-stage sparse-state preparation

The figure shows the conceptual pipeline:

```mermaid
flowchart LR
    A[All-zero n-qubit input] --> B[DensePrep on ell = ceil(log2 s) qubits]
    B --> C[Compact state |theta>]
    C --> D[Isometry: expand labels into target basis strings]
    D --> E[Target sparse state |Theta>]
```

The dense-preparation stage encodes the coefficient list in a compact register. The isometry turns each compact label into the desired full-length basis string.

The `ell`-qubit register has `2^ell` possible labels. If `s` is not a power of two, some labels are unused. The paper's bijection `f` maps `[s]` to an `s`-element subset of those labels.

**Important wording:** the paper calls this a dense state on the compact sub-register. If `s<2^ell`, not every one of the `2^ell` labels necessarily has non-zero amplitude. “Dense” here describes the compact-register preparation framework, not a claim that all `2^ell` labels must be occupied in every case.

### 3.7 Two families of earlier approaches

The introduction groups prior methods into two broad families.

#### Family A: build one target basis state at a time

These methods perform approximately `s` iterative steps. Each step prepares one basis state with its coefficient. The cost is dominated by multi-controlled rotations or equivalent constructions.

The number of control qubits differs by method:

- [21]: worst case `n` controls.
- [12]: `ceil(n/log2 n)+1` controls.
- [13]: `ceil(log2 s)` controls.
- [22]: controls related to the Hamming weight of the current basis string.

A `w`-controlled operation can be built using an AND ladder and a controlled rotation. The paper states that, for overall approximation error `epsilon`, the phase-gradient implementation of a controlled rotation has Toffoli cost approximately `ceil(log2(s/epsilon))-2`. The total for this family exceeds `s ceil(log2 s)` under the paper's analysis.

#### Family B: dense preparation plus isometry

These methods first prepare

$$
|\theta\rangle=\sum_{i=0}^{s-1}c_i|f(i)\rangle
$$

and then apply an isometry

$$
|f(i)\rangle\mapsto|C_i\rangle.
$$

The total Toffoli cost is the dense-preparation cost plus the isometry cost.

The freedom to select `f` matters. If `f` is forced to be the identity, the isometry may need to implement a generic permutation. A non-trivial `f` can make the mapping easier.

### 3.8 Figure 2: how to read the two graphs

**Left graph — analytical worst-case improvement.** The vertical axis is the Toffoli-cost improvement factor of the new isometry over reference [20]. The curves correspond to sparsities from `10^2` through `10^8`. The horizontal axis is the total qubit number `n`.

The paper points out that Equation (1) can be loose when `s` and `m` are close. Consequently, the raw ratio of the two upper bounds can rise and then fall, even though the actual improvement is expected to grow toward an asymptote. To avoid that misleading visual behaviour, the plot uses the maximum improvement factor over all `n' <= n` at each `n`.

**Right graph — random-state numerical results.** The vertical axis is measured isometry Toffolis divided by `s`. As `n` increases, the ratio approaches 1 for the tested random states.

This graph is empirical evidence for the construction's practical behaviour. It is not a proof that every sparse support achieves `s` Toffolis.

### 3.9 What page 2 establishes

The paper has chosen a strong architecture and a meaningful freedom (`f`) to optimize the basis mapping. Its problem is now concentrated in the isometry, which the authors will improve.

### Checkpoint — page 2

- [ ] I can draw the two-stage architecture.
- [ ] I can explain the difference between iterative preparation and dense-prep-plus-isometry.
- [ ] I can explain what the bijection `f` does.
- [ ] I can explain why Figure 2's right graph is numerical rather than a proof.

<details>
<summary><strong>Derivation check: why is the label register ell qubits wide?</strong></summary>

A register of `ell` qubits has `2^ell` orthogonal computational-basis labels. We need at least `s` labels, so `2^ell >= s`. Taking logs gives `ell >= log2(s)`. The smallest integer satisfying this is `ceil(log2(s))`.
</details>

---

## PDF page 3 — Equation (1), batch-size definition, and Table 1

<details>
<summary><strong>Open the original supplied PDF page 3 / 22</strong></summary>

![Original PDF page 3](assets/pdf_page_03.png)

</details>


### 3.10 The baseline from reference [20]

The paper identifies Malvetti, Iten, and Colbeck [20] as the best Toffoli-count baseline in the dense-prep-plus-isometry family that it compares against.

Its worst-case isometry Toffoli count is:

$$
\boxed{T_{[20]}=s(\ell-1).}
$$

The AND-ladder implementation requires `ell-2` ancilla qubits, as stated in the paper.

The point of choosing [20] as the main baseline is methodological: compare a new construction against a strong relevant method, not an unnecessarily weak one.

### 3.11 Equation (1): the headline upper bound

The paper's bound is:

$$
\boxed{
T_{\mathrm{iso}}\leq
\left\lceil\frac{s}{m}\right\rceil
\left(2m+\frac{1}{2}\log_2\frac{\widetilde{s}}{m}-3\right)
+
\log_2\left(\frac{\widetilde{s}^{3/2}}{2\sqrt m}\right)
}
\tag{1}
$$

The variables are:

- `s`: number of non-zero basis states.
- `ell = ceil(log2 s)`: number of subspace-register qubits.
- `tilde{s}=2^ell`: full power-of-two address capacity.
- `m`: largest power of two satisfying `m <= n-ell`.
- `ceil(s/m)`: number of batches needed for `s` items.

`m` is both the selected one-hot batch width and the batch size in the construction. It is **not** the number of leftover qubits. The non-subspace register has `n-ell` qubits; `m` is chosen as a power of two no greater than that number, so the construction has enough residual-register positions `e_0,...,e_{m-1}` for a full batch.

### 3.12 Worked numerical evaluation

Take:

$$
s=64,\qquad n=20.
$$

Then:

$$
\ell=\lceil\log_2 64\rceil=6,
\qquad \widetilde{s}=64,
\qquad n-\ell=14.
$$

The largest power of two no greater than 14 is:

$$
m=8.
$$

The baseline is:

$$
T_{[20]}=64(6-1)=320.
$$

For Equation (1):

$$
\left\lceil\frac{64}{8}\right\rceil=8,
\qquad
\log_2(64/8)=3.
$$

The batch term is:

$$
8\left(2(8)+\frac{3}{2}-3\right)
=8(14.5)=116.
$$

The final term is:

$$
\log_2\left(\frac{64^{3/2}}{2\sqrt 8}\right)
=\log_2\left(\frac{512}{2\sqrt 8}\right)
\approx6.5.
$$

So the displayed real-valued upper-bound expression evaluates to approximately:

$$
T_{\mathrm{iso}}\leq122.5.
$$

A physical circuit cannot contain half a Toffoli gate. This is an analytically evaluated upper-bound expression; the actual gate count is an integer and must satisfy the stated bound. Do not report “122.5 gates” as an actual circuit count.

### 3.13 Interpreting the two parts of Equation (1)

The factor `ceil(s/m)` counts batches. The leading `2m` captures the batch-scale work: the PUI cost and the state/batch construction overhead. The logarithmic part inside the parentheses is the address-tree/prefix-selection overhead per batch. The final logarithm collects the remaining worst-case correction terms after combining the batch construction with the last-PUI restriction.

The derivation is given fully in [Derivation 6](#44-derivation-of-equation-1-the-final-combination).

### 3.14 Table 1: what is being compared

Table 1 compares upper bounds for:

- Isometry Toffoli count.
- Isometry qubit count.
- Reference/variant.
- Dense-state-preparation Toffoli count.
- Dense-state-preparation qubit count.

It separates **generic complex-coefficient states** from **real-coefficient states**. The rows without a literature reference correspond to the paper's variants:

1. Restricted PUI with integrated QROAM sign-fix.
2. Unrestricted PUI.
3. Restricted PUI with integrated phase encoding for real states.

The important interpretation is not just “which row has the smallest Toffoli expression.” It is a Toffoli/ancilla trade-off. QROAM's parameter `r` and the rotation-angle precision `b` affect both count and workspace.

The table notes several assumptions:

- A single QROAM parameter `r` is used for all clean QROAM calls for simplicity.
- `b` is the number of bits used for rotation-angle data.
- The cost of preparing the phase-gradient state is excluded.
- The phase-gradient register is excluded from the qubit count.
- The maximum qubit count is assumed to occur during QRO(A)M use rather than during the rotations.
- For the first two literature isometry approaches, the leading dense-preparation prefactor may be reduced from 3 to 2 by a slight isometry modification that allows the dense-preparation registers to be uncomputed at no additional cost.

These assumptions matter when reproducing Table 1. It is not a universal end-to-end hardware bill independent of the implementation model.

### Checkpoint — page 3

- [ ] I can define `tilde{s}` and `m` precisely.
- [ ] I can calculate the baseline and new bound for `s=64,n=20`.
- [ ] I can explain what Table 1 compares.
- [ ] I can name at least three resource assumptions used in Table 1.

---

## PDF page 4 — Isometry problem, tableau, and Malvetti baseline

<details>
<summary><strong>Open the original supplied PDF page 4 / 22</strong></summary>

![Original PDF page 4](assets/pdf_page_04.png)

</details>


### 3.15 First: the two versions of PUI are previewed

The paper says that restricted PUI acts non-trivially only inside the requested address interval. Unrestricted PUI lowers Toffoli cost by allowing some extra effects on address values **greater than** the interval's upper endpoint. Those extra effects must be tracked when later parts of the circuit are constructed.

This distinction is developed fully on pages 8–10.

### 3.16 The tableau representation

The authors turn the target support into a classical tableau:

- `s` rows, one per target basis state.
- `n` columns, one per qubit.
- Each entry is 0 or 1.

They index columns from left to right starting at zero. They define `|e_k>` as the one-hot basis state on the non-subspace register with the `k`-th residual bit set to 1 and all other residual bits zero.

For example, in a four-qubit residual register:

$$
|e_0\rangle=|1000\rangle,\quad
|e_1\rangle=|0100\rangle,\quad
|e_2\rangle=|0010\rangle,\quad
|e_3\rangle=|0001\rangle,
$$

following the paper's left-to-right bit indexing.

### 3.17 The isometry-finding task

Split each row:

$$
|C_i\rangle=|C_i'\rangle_s|C_i''\rangle_r.
$$

Find a reversible circuit `G` and a bijection `f` such that:

$$
\boxed{G|C_i\rangle=|f(i)\rangle_s|0\rangle_r.}
$$

The isometry used for state preparation is `G†`.

### 3.18 Malvetti et al. [20]: the baseline logic

The baseline processes the target basis states one by one.

**Case A: residual part is already zero.**

If `|C_i''>_r = |0>_r`, the basis state is already in the subspace. Assign its existing subspace value as its compressed label.

**Case B: residual part is non-zero.**

The algorithm applies CX gates controlled on non-zero residual bits to transform the state into a form

$$
|k\rangle_s|e_j\rangle_r,
$$

where `k` is a subspace label not already used by a state in the subspace. Then it applies an `ell`-controlled-X, controlled on the subspace value `k`, to flip the one remaining residual 1 to zero:

$$
|k\rangle_s|e_j\rangle_r
\longmapsto
|k\rangle_s|0\rangle_r.
$$

The unique new `k` is recorded as `f(i)`.

### 3.19 Why the baseline cost is `s(ell-1)`

The main expensive action is the `ell`-controlled-X used to zero the residual one-hot bit. Using the AND-ladder construction cited by the paper, the Toffoli cost per such operation is `ell-1`. In the worst case this is done for all `s` states:

$$
T_{[20]}=s(\ell-1).
$$

This is a worst-case count. Some states may already lie in the subspace and may not require the operation.

### 3.20 Figure 3

Figure 3 shows an example input tableau and the resulting tableau after the Malvetti procedure. Every output row has a zero residual register. The subspace labels are distinct.

Read the figure as two synchronized data tables:

- Left: original subspace/residual bitstrings.
- Right: transformed subspace label/residual-zero bitstrings.

The figure is a baseline example. It is not yet the new batched construction.

### Checkpoint — page 4

- [ ] I can explain what a tableau is.
- [ ] I can define a one-hot state `|e_j>`.
- [ ] I can state the target mapping `G|C_i>=|f(i)>|0>`.
- [ ] I can explain why the preparation circuit uses `G†`.
- [ ] I can derive the baseline count `s(ell-1)`.

---

## PDF page 5 — The new idea: batches and Figure 4

<details>
<summary><strong>Open the original supplied PDF page 5 / 22</strong></summary>

![Original PDF page 5](assets/pdf_page_05.png)

</details>


### 3.21 What the authors want to remove

The baseline uses one multi-controlled-X zeroing operation per target state. The authors ask whether several such zeroing operations can be combined into a single structured operation.

Their answer is to construct batches of the form:

$$
\boxed{
\bigl(
|k\rangle_s|e_0\rangle_r,
|k+1\rangle_s|e_1\rangle_r,
\ldots,
|k+m-1\rangle_s|e_{m-1}\rangle_r
\bigr).
}
$$

The subspace address and one-hot residual position advance together. This regular pattern is what lets a PUI apply the right X operation to each address.

### 3.22 The batch-zeroing transformation

A PUI over address interval `[k,k+m-1]` applies the operation corresponding to each address. The intended action on the batch is:

$$
\begin{aligned}
|k\rangle_s|e_0\rangle_r&\mapsto|k\rangle_s|0\rangle_r,\\
|k+1\rangle_s|e_1\rangle_r&\mapsto|k+1\rangle_s|0\rangle_r,\\
&\vdots\\
|k+m-1\rangle_s|e_{m-1}\rangle_r&\mapsto|k+m-1\rangle_s|0\rangle_r.
\end{aligned}
\tag{2}
$$

The batch has `m` elements; the PUI performs `m` address-dependent target operations. It replaces `m` separate high-control zeroing operations with one structured unary-iteration construction.

### 3.23 Why choose `m` as a power of two?

Unary iteration is naturally implemented using a balanced binary tree. A power-of-two interval corresponds to a complete subtree. Arbitrary-length intervals can force some tree nodes to be visited more than once across adjacent batches, increasing Toffoli count.

The paper therefore chooses the largest power of two no greater than the residual-register width `n-ell`:

$$
m=\max\{2^p:2^p\leq n-\ell\}.
$$

If the final batch is incomplete, the algorithm uses its actual number of elements for that last PUI.

### 3.24 How the batch is created

Let `k` be the next unused compact subspace label. It starts at zero and increments once for every state added to a batch.

1. Find a target state with the first relevant residual bit equal to 1. If necessary, swap residual qubits to place a usable 1 at the next desired position.
2. Use a multi-target CX to put this state into the first batch form `|k>_s|e_0>_r`.
3. Find another suitable state and transform it into `|k+1>_s|e_1>_r`.
4. Continue until the batch is full or no more unprocessed states remain.
5. Apply PUI over the corresponding address interval to zero the residual one-hot bits.
6. Update the classical tableau to reflect every transformation, including any extra effects of unrestricted PUI.
7. Start the next batch.

### 3.25 Figure 4

Figure 4 uses a three-qubit subspace register and seven target basis states. The first batch contains four states with compact labels 0 through 3 and one-hot residual positions 0 through 3. It is zeroed by `PUI_0^3` (notation direction follows the paper's interval notation). The remaining three states form the next batch with labels 4 through 6 and residual one-hot positions 0 through 2. That batch is zeroed by a second PUI.

The key visual point: the state labels on the right are all distinct and every residual register is zero.

### 3.26 A subtle point: unrestricted-PUI side effects

The PUI used for a batch may also affect some later address values above the current interval. The classical tableau is updated after the PUI; the algorithm does not pretend those states stayed unchanged.

### Checkpoint — page 5

- [ ] I can write the structured batch state.
- [ ] I can explain why the residual part is one-hot before zeroing.
- [ ] I can explain why a PUI can zero several batch elements.
- [ ] I can explain why `m` is a power of two.
- [ ] I can explain why the tableau must be updated after PUI.

<details>
<summary><strong>Quick check: is m the number of leftover qubits?</strong></summary>

No. There are `n-ell` qubits in the non-subspace register. `m` is the largest power of two not exceeding that width, and it is used as the maximum one-hot batch width and batch size.
</details>

---

## PDF page 6 — Difficult batch construction, Figure 5, Equation (3), and classical complexity

<details>
<summary><strong>Open the original supplied PDF page 6 / 22</strong></summary>

![Original PDF page 6](assets/pdf_page_06.png)

</details>


### 3.27 Why the ideal batch-building assumption can fail

The simple description on page 5 assumes that, when adding the next batch element, there is an unprocessed state with the next residual bit equal to 1. That may not be true.

The algorithm must create the required state without changing:

- states already in the current batch;
- states already in the subspace;
- the distinctness of the labels that have already been assigned.

### 3.28 The two ways to get the next residual 1

The authors describe two situations.

**Situation 1: a usable 1 exists further to the right.**

A SWAP can exchange the required residual position with a later position that contains 1.

**Situation 2: no such later 1 exists.**

Choose an unprocessed state outside the batch and outside the subspace. It has a 1 in one of the already-used residual positions. By construction, a corresponding one-hot state exists in the batch. The two full strings must differ in at least one qubit position `u`.

A Toffoli is applied with controls chosen so that the selected unprocessed state is changed while the relevant batch state is not. The target is the next residual qubit. If the selected state has 0 at the differing control position, use a negative control.

The PDF labels the operations in Figure 5 as `CMX^{0,3}_4`, then `Tof^5_{2,3}`, then `CMX^{1,2,3}_5`, followed by `PUI_4^6`. The upper indices are target qubits and the lower indices are controls. The second operation is the Toffoli: its controls distinguish the selected row from the relevant already-batched row, and its target is the next residual position. The third CMX finishes converting that row into the next one-hot batch element.

The caption explains the logical purpose of the Toffoli's controls:

- one control is the third qubit where the purple states differ;
- the other is the first subspace qubit where they coincide.

If the differing qubit is zero in the selected state, the control is negative. The target is the next residual qubit.

### 3.29 Figure 5, row by row

The figure begins the second batch in Figure 4. It shows three rows:

```text
Row 1: |100>_s |1000>_r
Row 2: |001>_s |1100>_r
Row 3: |101>_s |1000>_r
```

The first row already has the desired first-element structure:

$$
|4\rangle_s|e_0\rangle_r.
$$

The second row is transformed by a CMX into the second batch element:

$$
|5\rangle_s|e_1\rangle_r.
$$

The third row needs the Toffoli and subsequent CMX sequence to become:

$$
|6\rangle_s|e_2\rangle_r.
$$

Then `PUI_4^6` maps the three residual one-hot states to zero. The final rows have subspace labels 4, 5, and 6, each with residual `0000`.

Do not try to infer the meaning of the gate subscripts from their visual placement alone: the Figure 5 caption specifies that upper indices are targets and lower indices are controls.

### 3.30 Why the last batch needs special care

Suppose an address already exists in the subspace but was never part of a batch. If the last batch is zeroed with unrestricted PUI, that non-batch state can be affected and moved out of the subspace.

The authors use a **restricted PUI** for the final zeroing operation in the relevant case. A possible collision is then repaired with one Malvetti-style step.

### 3.31 Equation (3): extra cost of batch construction

The paper states that the total Toffoli cost is the PUI cost plus at most:

$$
\boxed{
T_{\mathrm{extra}}\leq
s-\left\lceil\frac{s}{m}\right\rceil
+\log_2\left(\frac{\widetilde{s}}{2}\right).
}
\tag{3}
$$

Why the first two terms?

- There are `s` states.
- There are `ceil(s/m)` batches.
- The first element of each batch is guaranteed not to require the extra Toffoli in the batch-building step.
- Therefore at most `s-ceil(s/m)` later elements contribute that part of the overhead.

The final logarithmic term accounts for the exceptional final Malvetti-style correction in the paper's bound. **There is a typographical inconsistency in the prose immediately before Equation (3); see [source-consistency checks](#53-source-consistency-checks-and-apparent-pdf-typos).**

### 3.32 Why multi-target CX is mentioned

The authors note that, in a surface-code implementation using lattice surgery, a CX with multiple targets need not take longer than a single-target CX [31]. This is an architecture-specific observation used to motivate why CMX operations are reasonable in the circuit design. It is not a universal statement about all hardware and compilation models.

### 3.33 Classical complexity: `O(s^2 n)`

This is the runtime of the classical algorithm that finds the isometry, not the quantum circuit's Toffoli count.

The tableau has `s` rows and `n` columns, so one full tableau update costs `O(sn)`. Each basis state causes at most a constant number of updates/scans. There are `O(s)` state-processing iterations. Therefore:

$$
O(s)\times O(sn)=\boxed{O(s^2n)}.
$$

The paper reports a Rust implementation using SIMD intrinsics. Page 6 describes an `s=10^7` run as approximately 10–20 minutes on a CPU node with two AMD EPYC 7452 processors. Figure 10 on page 14 separately lists 1488.7 seconds (unrestricted) and 813.22 seconds (restricted), averaged over different `n` values under the figure's stated threading setup; page 15 summarizes the capability as a few minutes on reasonable hardware. Treat these as reported implementation measurements with different contexts, not as one universal runtime guarantee. The authors note that multi-threading is non-trivial and that GPU implementations may improve classical preprocessing time.

### Checkpoint — page 6

- [ ] I can explain why a SWAP may be sufficient.
- [ ] I can explain why a Toffoli is needed in the difficult case.
- [ ] I can read Figure 5 as a sequence of state transformations.
- [ ] I can explain why the final batch may need restricted PUI.
- [ ] I can derive the `s-ceil(s/m)` part of Equation (3).
- [ ] I can explain why the classical complexity is `O(s^2 n)`.

---

## PDF page 7 — Standard unary iteration and Figure 6

<details>
<summary><strong>Open the original supplied PDF page 7 / 22</strong></summary>

![Original PDF page 7](assets/pdf_page_07.png)

</details>


### 3.34 The problem PUI solves

The paper now defines PUI formally. Given an address register with `w` qubits, and an interval of address values from `l` through `r`, the circuit must apply a corresponding target unitary `U_i` for each address `i` in that interval:

$$
U(|i\rangle_a\otimes|t\rangle_t)
=
|i\rangle_a\otimes(U_i|t\rangle_t).
\tag{4}
$$

The address register selects the operation; the target register receives it. The address itself is preserved.

### 3.35 Full unary iteration

If the interval is the entire address space, from 0 through `2^w-1`, standard unary iteration can traverse a balanced binary tree. The paper uses the construction from [23], while noting an alternative based on skew trees in [32].

The cost stated for the full construction is:

$$
2^w-2
$$

Toffolis, or `2^w-1` if the operation is controlled, using `w-1` ancilla qubits.

### 3.36 How the binary tree creates controls

Take `w=3`, so there are eight addresses:

```text
                         0 ... 7
                       /        \
                    0 ... 3    4 ... 7
                   /     \      /    \
                 0..1   2..3  4..5  6..7
                 / \     ...   / \    ...
                0   1         4   5
```

Each internal node represents an interval. An ancilla stores the condition that the address lies in that interval. A subsequent address bit splits that interval into its left and right halves.

For the example on page 7, the ancilla `d0` records whether the first two address bits equal `10`. Under the paper's big-endian convention, that selects the interval `[4,7]`. A new AND condition using the next address bit separates address 4 from address 5. The target operations `U4` and `U5` can then be applied under the appropriate ancilla conditions.

The important design idea is **shared prefix computation**. The circuit does not construct every full address comparison independently; it reuses intermediate interval conditions along the tree.

### 3.37 Why uncompute the ancillas?

Temporary AND ancillas are used to route the operation. They must be returned to the required clean state. The paper uses the measurement-based adjoint of the AND primitive (Appendix A), which can be performed at zero additional Toffoli cost under its accounting.

### 3.38 Figure 6

Figure 6 is a full unary-iteration circuit for a three-qubit address register. The target register has four qubits, and `U0` through `U6` are chosen as X gates on different target qubits; `U7` is identity.

The left and right portions can be interpreted as restricted PUIs on `[0,3]` and `[4,6]`. The purple control dots are important: removing them creates the unrestricted simplifications shown later in Figure 7.

### Checkpoint — page 7

- [ ] I can explain Equation (4) in words.
- [ ] I can draw a three-level binary address tree.
- [ ] I can explain what an interval-selecting ancilla records.
- [ ] I can explain why the address register is unchanged.
- [ ] I can explain why an AND ancilla must be uncomputed.

---

## PDF page 8 — Restricted and unrestricted PUI; Figure 7

<details>
<summary><strong>Open the original supplied PDF page 8 / 22</strong></summary>

![Original PDF page 8](assets/pdf_page_08.png)

</details>


### 3.39 Restricted PUI

To iterate only over an interval `[l,r]`, the circuit recursively explores a left or right half only when that half overlaps the target interval.

At a leaf inside the interval, it applies the required `U_i`. Outside the interval, it acts trivially on the target register.

So a restricted PUI provides the guarantee:

$$
i\notin[l,r]\quad\Longrightarrow\quad U_i=I
$$

for the address values outside the requested interval.

### 3.40 Why unrestricted PUI can be cheaper

In the isometry algorithm, batches are processed in increasing address intervals. The target operations are X gates on residual bits. If an operation also affects some address values greater than the current interval, those extra bit flips can be recorded in the tableau and accounted for later.

This gives the circuit designer permission to remove certain controls, reducing Toffoli cost.

### 3.41 The unrestricted operation

The paper writes the unrestricted unitary as:

$$
U=
\sum_{i=l}^{r}|i\rangle\langle i|_a\otimes U_i
+
\sum_{i\in L}|i\rangle\langle i|_a\otimes U_{g(i)},
$$

where:

- `L` is a subset of address values strictly greater than `r`;
- `g:L -> {l,...,r}` says which in-interval operation is additionally applied to each extra address.

Thus an address `j>r` may receive `U_{g(j)}` rather than identity.

The paper guarantees that addresses **below** the lower endpoint remain untouched. The extra effects are only above the interval's upper endpoint.

### 3.42 When is this safe?

The paper gives two types of situations where it is meaningful:

1. The input state is known to have no support on address values above the interval.
2. The algorithm processes address intervals from left to right and can track/undo unwanted effects once a value becomes part of a later active interval.

The second condition is what the isometry algorithm exploits. The unwanted effects are simple bit flips, so the classical tableau can track them.

### 3.43 Figure 7

Figure 7 displays unrestricted PUIs on `[0,3]` and `[4,6]`, built by simplifying the restricted circuits from Figure 6 after removing selected purple controls.

The caption gives a concrete example: in `PUI_0^3`, the first target-X gate is applied not only at address 0 but also at address 4, because the most-significant address bit that would distinguish those values is no longer controlled. Similar extra effects occur for the other target-X gates of that batch.

The right PUI `[4,6]` is structured to leave values below 4 untouched while potentially affecting address 7 according to the relaxed control structure.

### 3.44 Keep the distinction exact

| Property | Restricted PUI | Unrestricted PUI |
|---|---|---|
| Intended interval | Applies `U_l,...,U_r` | Applies `U_l,...,U_r` |
| Address values below `l` | Untouched | Untouched |
| Address values above `r` | Target operation is identity | May receive an extra `U_{g(i)}` |
| Toffoli cost | Higher in the repeated-interval construction | Lower in the repeated-interval construction |
| Bookkeeping | No extra-address map needed | Must track `L` and `g` |

### Checkpoint — page 8

- [ ] I can state the restricted-PUI guarantee.
- [ ] I can explain exactly which outside addresses unrestricted PUI may affect.
- [ ] I can explain the role of `L` and `g`.
- [ ] I can explain why the extra effects do not automatically invalidate the isometry algorithm.

---

## PDF page 9 — How Algorithm 2 branches; deriving the full-address PUI costs

<details>
<summary><strong>Open the original supplied PDF page 9 / 22</strong></summary>

![Original PDF page 9](assets/pdf_page_09.png)

</details>


### 3.45 The three recursion cases

The current binary-tree interval is split into left and right halves. Depending on which halves intersect the requested target interval, Algorithm 2 takes one of three paths.

| Left half intersects? | Right half intersects? | Action |
|---|---|---|
| Yes | Yes | Use the normal branch primitive and recurse into both halves |
| Yes | No | For unrestricted PUI, omit the split-bit control and recurse left; that bit becomes free |
| No | Yes | Select the right half and recurse right |

The second case is the critical unrestricted simplification. Ignoring the split bit means some addresses in the right half can receive the same target operation. Those addresses are later added to `L` and mapped by `g`.

### 3.46 Building the extra-address set `L`

When a leaf address `j` is reached, the algorithm examines the path from the root to that leaf. For every bit position that was ignored, it forms all address strings that:

1. Match `j` at all non-free bit positions.
2. Have at least one `1` in the free positions.

Those strings are the extra address values mapped to `j` under `g`.

This is an exact bookkeeping construction, not a heuristic.

### 3.47 PUI resource analysis setup

For this repeated-interval analysis, the paper considers an address register of `w` qubits and full address-space size:

$$
S_{\mathrm{addr}}=2^w.
$$

It processes consecutive intervals of size `m`, starting at address 0. To avoid colliding with the paper's `ell` for subspace width, this guide defines:

$$
q=\log_2m,
\qquad k=w-q=\log_2(S_{\mathrm{addr}}/m).
$$

There are:

$$
R=\frac{S_{\mathrm{addr}}}{m}=2^k
$$

intervals.

Each interval fixes the upper `k` address bits and performs a unary iteration on the lower `q` bits.

### 3.48 Restricted PUI full-address cost

For the restricted version, each interval's controlled unary-iteration part costs `m-1` Toffolis. Selecting the upper `k`-bit interval value costs `k-1` AND/Toffoli operations in the construction described by the paper.

So the per-interval count is:

$$
(m-1)+(k-1)=m+k-2.
$$

With `R=S_addr/m` intervals:

$$
\boxed{
T_{\mathrm{rPUI,full}}
=\frac{S_{\mathrm{addr}}}{m}
\left(m+\log_2\frac{S_{\mathrm{addr}}}{m}-2\right).
}
$$
This is the full-address version of the restricted bound later written as Equation (8).

### 3.49 Unrestricted PUI: count prefix-selection Toffolis

For a prefix bitstring of length `k`, let its Hamming weight be `h(x)`, the number of ones in it.

The unrestricted construction needs `h(x)-1` Toffolis if `h(x)>=2`, and zero prefix-selection Toffolis if the prefix has zero or one 1.

Why?

- With zero ones, the all-zero prefix needs no non-trivial AND chain.
- With one 1, that bit itself can act as the selector.
- With `h>=2`, the circuit has to combine conditions; the AND ladder contributes `h-1` Toffolis.

The total over all `2^k` prefixes is:

$$
\sum_{x:h(x)>1}(h(x)-1).
$$

Appendix B proves an expression/bound for this sum. For the full power-of-two address space, the paper gives Equation (5):

$$
\boxed{
T_{\mathrm{prefix,unrestricted}}
=2^k\left(\frac{k}{2}-1\right)+1.
}
\tag{5}
$$

The initial all-zero prefix uses the uncontrolled unary iteration, which costs `m-2`; the other `R-1` intervals use the controlled form, costing `m-1` each. The internal-iteration total is therefore:

$$
(R-1)(m-1)+(m-2)=R(m-1)-1.
$$

Add Equation (5), with `R=2^k`:

$$
\begin{aligned}
T_{\mathrm{uPUI,full}}
&=R(m-1)-1+R\left(\frac{k}{2}-1\right)+1\\
&=R\left(m+\frac{k}{2}-2\right).
\end{aligned}
$$

Hence:

$$
\boxed{
T_{\mathrm{uPUI,full}}
=\frac{S_{\mathrm{addr}}}{m}
\left(m+\frac12\log_2\frac{S_{\mathrm{addr}}}{m}-2\right).
}
$$

The factor one-half on the logarithmic term is the key cost advantage of the unrestricted prefix selection in this repeated-interval setting.

### Checkpoint — page 9

- [ ] I can describe the three recursion cases.
- [ ] I can explain what a free address bit means.
- [ ] I can derive the number of intervals `S_addr/m`.
- [ ] I can derive Equation (5) from Hamming-weight counting.
- [ ] I can explain why the first interval's uncontrolled unary iteration is one Toffoli cheaper.

---

## PDF page 10 — Equations (6), (7), (8), Equation (1) assembled, and Section 4 begins

<details>
<summary><strong>Open the original supplied PDF page 10 / 22</strong></summary>

![Original PDF page 10](assets/pdf_page_10.png)

</details>


### 3.50 Why the full-address assumption is not enough

The derivation on page 9 assumed that all `S_addr=2^w` address values were processed. In the isometry application, there are only `s` target states, and `s` need not be a power of two.

The paper assumes:

$$
2^{w-1}<s<2^w=S_{\mathrm{addr}}.
$$

So the used address range is a prefix of the full address space, not necessarily the entire space.

### 3.51 Equation (6): prefix-selection bound for incomplete address space

The paper uses the induction argument from Appendix B to upper-bound the prefix-selection Toffolis by:

$$
\boxed{
\left\lceil\frac{s}{m}\right\rceil
\left(\frac{w-q}{2}-1\right)+1.
}
\tag{6}
$$

The reason is that intervals closer to the upper endpoint `s` can contribute more Toffolis than intervals near zero. Appendix B proves a bound on the accumulated Hamming-weight contributions for every prefix length `r` in the relevant range.

### 3.52 Equation (7): unrestricted PUI bound for `s` addresses

Combining the incomplete-prefix bound with the within-interval unary-iteration cost yields:

$$
\boxed{
T_{\mathrm{uPUI}}
\leq
\left\lceil\frac{s}{m}\right\rceil
\left(m+\frac12\log_2\frac{S_{\mathrm{addr}}}{m}-2\right).
}
\tag{7}
$$

In the isometry application, `w=ell`, so `S_addr=2^ell=tilde{s}`.

### 3.53 Equation (8): restricted PUI bound for `s` addresses

For restricted PUI, the paper obtains:

$$
\boxed{
T_{\mathrm{rPUI}}
\leq
\left\lceil\frac{s}{m}\right\rceil
\left(m+\log_2\frac{S_{\mathrm{addr}}}{m}-2\right).
}
\tag{8}
$$

Compare Equations (7) and (8): the unrestricted bound has half the logarithmic prefix term. The restricted circuit has the stronger no-extra-address-effects guarantee, but pays more for that guarantee.

### 3.54 Why the analytical bound can be loose

The paper explicitly warns that, for small `s/m`, the derived upper bounds can be loose. As a function of `m`, the analytical upper bound may reach a minimum and then increase. The actual Toffoli count in the construction is observed to decrease monotonically with increasing `m`.

This is not a contradiction. A loose upper bound can behave differently from the actual count it bounds.

### 3.55 Combine Equation (3) and Equation (7): derive Equation (1)

This is the central algebraic assembly. Let:

$$
R=\left\lceil\frac{s}{m}\right\rceil,
\qquad
L=\log_2\frac{\widetilde{s}}{m}.
$$

The unrestricted PUI contribution is bounded by:

$$
R\left(m+\frac{L}{2}-2\right).
$$

The last PUI may need to be restricted. The paper bounds the extra cost of making that last PUI restricted by `L/2`.

The batch-construction/correction overhead from Equation (3) is:

$$
s-R+\log_2(\widetilde{s}/2).
$$

Adding these pieces gives the paper's intermediate total:

$$
T_{\mathrm{iso}}
\leq
R\left(m+\frac{L}{2}-2\right)
+\frac{L}{2}
+s-R+\log_2(\widetilde{s}/2).
$$

Now use the elementary ceiling inequality:

$$
Rm\geq s.
$$

Thus:

$$
s-R\leq Rm-R.
$$

Substitute that upper bound:

$$
\begin{aligned}
T_{\mathrm{iso}}
&\leq R\left(m+\frac{L}{2}-2\right)
+\frac{L}{2}+Rm-R+\log_2(\widetilde{s}/2)\\
&=R\left(2m+\frac{L}{2}-3\right)
+\frac{L}{2}+\log_2(\widetilde{s}/2).
\end{aligned}
$$

Combine the final logarithms:

$$
\begin{aligned}
\frac{L}{2}+\log_2(\widetilde{s}/2)
&=\frac12\log_2\frac{\widetilde{s}}{m}
+\log_2\frac{\widetilde{s}}{2}\\
&=\log_2\left(\sqrt{\frac{\widetilde{s}}{m}}\cdot\frac{\widetilde{s}}{2}\right)\\
&=\log_2\left(\frac{\widetilde{s}^{3/2}}{2\sqrt m}\right).
\end{aligned}
$$

Therefore:

$$
\boxed{
T_{\mathrm{iso}}\leq
\left\lceil\frac{s}{m}\right\rceil
\left(2m+\frac12\log_2\frac{\widetilde{s}}{m}-3\right)
+
\log_2\left(\frac{\widetilde{s}^{3/2}}{2\sqrt m}\right).
}
$$

This is Equation (1). The derivation shows exactly where its terms come from:

- Equation (7): unrestricted PUI cost.
- `L/2`: cost increase for the final restricted PUI.
- Equation (3): batch-construction and final correction overhead.
- `Rm>=s`: ceiling inequality used to simplify the total bound.

### 3.56 Qubit requirement and reuse

The paper states that `ell-1` ancilla qubits are needed for the isometry. Those ancillas can also be used for dense-state preparation. Hence the dense-preparation step can have up to `n+ell-1` total qubits available without increasing the overall peak beyond that combined allocation, subject to the paper's assumptions about when registers are live.

The broader point is that state preparation is often a subroutine inside a larger algorithm. The number of available ancillas is determined by the rest of the algorithm, so the authors analyze Toffoli/qubit trade-offs rather than only a single fixed ancilla budget.

### 3.57 Section 4 starts: dense state preparation

The authors now explain the Grover–Rudolph strategy. Given:

$$
|\theta\rangle=\sum_{i=0}^{2^\ell-1}c_i|f(i)\rangle,
$$

they separate amplitude magnitudes from phases:

$$
|\theta'\rangle=\sum_i|c_i||f(i)\rangle,
$$

then encode the phases using `R_z` rotations. The amplitude magnitudes are prepared using a sequence of controlled `R_y` rotations.

The important shift is that, after reducing the isometry cost, dense-state preparation is no longer automatically negligible. The full circuit has to be optimized jointly.

### Checkpoint — page 10

- [ ] I can distinguish the full address space `S_addr=2^w` from the `s` used addresses.
- [ ] I can explain Equations (6), (7), and (8).
- [ ] I can derive Equation (1) line by line.
- [ ] I can explain why the final PUI may need to be restricted.
- [ ] I can explain why dense-state preparation becomes a major cost after isometry improvement.

---

## PDF page 11 — Figure 8, Grover–Rudolph preparation, phase-gradient states, and sign correction

<details>
<summary><strong>Open the original supplied PDF page 11 / 22</strong></summary>

![Original PDF page 11](assets/pdf_page_11.png)

</details>


### 3.58 Amplitude magnitude and phase are different tasks

Each complex coefficient can be written as:

$$
c_i=|c_i|e^{i\phi_i}.
$$

The magnitude `|c_i|` controls the probability weight. The phase `phi_i` controls relative phase relationships between basis components.

The paper separates these tasks:

1. Prepare the correct magnitudes using a sequence of `ell-1` sequential `R_y` rotations, as stated in Section 4.
2. Encode the desired phases using `R_z` rotations.

In Figure 8's three-system-qubit example, the initial angle is encoded using X gates as explained in the caption; later conditional angles are loaded using QRO(A)M. The paper says the angle/phase-gradient register size `b` is logarithmic in the desired rotation-angle accuracy and is around 20 in many practical examples.

### 3.59 What an `R_y` rotation does

The matrix is:

$$
R_y(\theta)=
\begin{pmatrix}
\cos(\theta/2)&-\sin(\theta/2)\\
\sin(\theta/2)&\cos(\theta/2)
\end{pmatrix}.
$$

Applied to `|0>`:

$$
R_y(\theta)|0\rangle
=\cos(\theta/2)|0\rangle+\sin(\theta/2)|1\rangle.
$$

It redistributes amplitude magnitude between the two basis outcomes. A sequence of appropriately controlled `R_y` rotations builds the required probability distribution over the compact labels.

The paper uses a Grover–Rudolph-style tree of conditional rotations. The angle at a given stage depends on the already-set prefix of system qubits.

### 3.60 What an `R_z` rotation does

The Z rotation is:

$$
R_z(\phi)=
\begin{pmatrix}
e^{-i\phi/2}&0\\
0&e^{i\phi/2}
\end{pmatrix}.
$$

It changes phase relationships without moving population between `|0>` and `|1>` in the computational basis. This is why it is used for phase encoding.

### 3.61 Figure 8: the circuit ingredients

Figure 8 shows a three-system-qubit example. It contains:

- the system register;
- an angle register of `b` bits;
- a `b`-qubit phase-gradient state `|psi>`;
- QRO(A)M loading blocks for conditional rotation angles;
- `R_y` rotations for amplitudes;
- an `R_z` rotation for phases;
- X-basis measurements of the angle register (`M_X`);
- final sign fixes.

The first angle `phi_0` is encoded using X gates according to the figure caption. Later angles depend on the values of earlier system qubits and are loaded using QRO(A)M.

### 3.62 Why the angle lookup is controlled by earlier qubits

At rotation stage `i`, the rotation angle depends on the bitstring `j` already stored in system qubits `0,...,i-1`. The circuit needs a family of rotations:

$$
\sum_{j\in[2^i]}|j\rangle\langle j|\otimes R(\phi_i^j).
$$

A QRO(A)M operation loads the appropriate angle `phi_i^j` into the angle register, controlled by the address `j`. The phase-gradient rotation then applies the desired controlled rotation.

### 3.63 What is a phase-gradient state?

A phase-gradient state is a reusable quantum resource that allows rotations to be implemented via controlled addition/subtraction between the angle register and the phase-gradient register. The paper refers to [5] and [25] for the full phase-gradient construction and rotation-angle details.

The paper's resource accounting makes two explicit simplifications:

- The `b` Toffolis used by a phase-gradient rotation are considered negligible compared with the dominating QRO(A)M costs and are omitted from the count.
- The cost of preparing the reusable phase-gradient state is excluded, and its register is not counted in the qubit total.

These are assumptions of the resource model, not statements that the phase-gradient resource is physically free.

### 3.64 X-basis measurement and induced signs

After a rotation, the angle register is measured in the X basis rather than fully uncomputed as in the original approach the authors compare against. The measurement returns the angle register to a clean `|0>` state, but it induces `+1` or `-1` phases on the main-register basis states.

The sign can be inferred from the measurement results and the angle-register data. QROAM junk/workspace registers are treated analogously. The accumulated signs must eventually be corrected.

### 3.65 Why sign correction becomes an optimization target

The sign fixes can be implemented using a lookup-table method, as discussed with reference [33]. But this increases the dense-preparation cost. The authors propose moving those sign fixes into a modified isometry, using restricted PUI to ensure the necessary basis states are visited.

### Checkpoint — page 11

- [ ] I can separate magnitude preparation from phase preparation.
- [ ] I can explain what `R_y` and `R_z` do.
- [ ] I can explain why rotation angles depend on previous qubit values.
- [ ] I can explain what the phase-gradient state is used for.
- [ ] I can explain why X-basis measurement causes sign bookkeeping.
- [ ] I can name the phase-gradient cost assumptions.

---

## PDF page 12 — QROM, QROAM, Toffoli–ancilla trade-offs, and Figure 9 setup

<details>
<summary><strong>Open the original supplied PDF page 12 / 22</strong></summary>

![Original PDF page 12](assets/pdf_page_12.png)

</details>


### 3.66 QROM: a simple lookup construction

QROM is a reversible lookup mechanism. An address register selects classical data (here, rotation-angle bits), which is loaded into a quantum data register in a reversible way.

The paper gives the original QROM cost for an address register of `k` bits:

$$
T_{\mathrm{QROM}}(k)=2^k-2,
\qquad A_{\mathrm{clean}}(k)=k-1.
$$

For the sequence of lookups in Figure 8, the total is:

$$
\begin{aligned}
\sum_{k=2}^{\ell}(2^k-2)
&=\left(\sum_{k=2}^{\ell}2^k\right)-2(\ell-1)\\
&=(2^{\ell+1}-4)-2\ell+2\\
&=2^{\ell+1}-2\ell-2\\
&<2\widetilde{s}.
\end{aligned}
$$

If the final sign-fix lookup is implemented separately with a table of size `ell-1`, the paper adds `2^(ell-1)-2` Toffolis. The combined bound is less than `2.5 tilde{s}`.

This explains why the sign-fix stage matters: it raises the leading dense-preparation cost.

### 3.67 QROAM: trade workspace for fewer Toffolis

The paper then considers a clean QROAM construction based on QROM plus controlled swaps. For an address register with `k` bits and `b` data bits, the Toffoli cost is:

$$
\boxed{T_{\mathrm{QROAM}}(k,r,b)=2^{k-r}+b(2^r-1),}
$$

with clean-ancilla cost:

$$
\boxed{A_{\mathrm{QROAM}}(k,r,b)=b(2^r-1)+(k-r).}
$$

Here `r` is a tunable parameter. Increasing `r` increases workspace but can reduce the leading `2^{k-r}` term.

### 3.68 Derive the approximate optimum for one QROAM lookup

Let:

$$
x=2^r.
$$

Ignoring the `-1` inside the smaller term for a leading-order estimate:

$$
T(x)\approx\frac{2^k}{x}+bx.
$$

Differentiate with respect to positive real `x`:

$$
\frac{dT}{dx}=-\frac{2^k}{x^2}+b.
$$

Set the derivative to zero:

$$
-\frac{2^k}{x^2}+b=0
\quad\Longrightarrow\quad
x^2=\frac{2^k}{b}.
$$

Therefore:

$$
\boxed{2^r\approx\sqrt{\frac{2^k}{b}}.}
$$

At this value, the two leading terms are balanced:

$$
\frac{2^k}{x}\approx bx\approx\sqrt{b2^k}.
$$

So the approximate minimum is:

$$
\boxed{T_{\min}\approx2\sqrt{b2^k}.}
$$

This is the trade-off in one line: a square-root-like Toffoli reduction is obtained by spending additional clean ancillas.

### 3.69 Sum across rotation-angle lookups

Using a common `r` for the `ell-1` clean QROAM calls, the paper obtains:

$$
T_{\mathrm{dense,QROAM}}
= b(\ell-1)(2^r-1)+(2^\ell-2)2^{1-r},
$$

which is upper-bounded in the paper by an expression with leading term proportional to `2 tilde{s}/2^r`. With a separate QROAM-based sign-fix scheme, the paper gives a different prefactor and an additional term proportional to `(2^r-1)`.

The exact aggregate formulas are listed in Table 1. The central concept is that the lookup Toffoli count can be reduced by increasing `r`, at the cost of more ancillas.

The paper also notes that some of the `b(2^r-1)` ancillas can be dirty, depending on the implementation and accepted cost prefactors; see [5].

### 3.70 An additional dense-preparation variant

Reference [3] offers another angle-loading variant using multiple angle registers and controlled swaps. The authors do not analyze it further because the minimum ancilla requirement is less controllable in the clean-QROAM trade-off they want to study.

### 3.71 Why the dominant stage changes

With QROM, the dense-preparation cost is around `2.5 tilde{s}` in the stated model. The isometry's worst-case upper bound is around `2s`, but random-instance isometry costs often approach `s`. Thus, in practical instances, QROM-based dense preparation can become the dominant term.

As `r_max` increases and QROAM is used more aggressively, dense-preparation cost becomes smaller compared with the isometry. Beyond some point, extra ancillas give diminishing overall benefit.

### Checkpoint — page 12

- [ ] I can derive the sum of QROM costs.
- [ ] I can derive the approximate QROAM optimum `2^r ≈ sqrt(2^k/b)`.
- [ ] I can explain why QROAM trades ancillas for Toffolis.
- [ ] I can explain why optimizing the isometry alone is no longer enough.

---

## PDF page 13 — Figure 9, Algorithm 3 motivation, and real-state phase optimization

<details>
<summary><strong>Open the original supplied PDF page 13 / 22</strong></summary>

![Original PDF page 13](assets/pdf_page_13.png)

</details>


### 3.72 Figure 9: end-to-end resource comparison

Figure 9 compares end-to-end sparse-state preparation for:

- a random generic (complex-coefficient) sparse state;
- a random purely real sparse state.

The paper's figure uses `n=80` and `s=10,000` (the typeset caption shows `s=10^4`). It varies `r_max`, the maximum QROAM parameter considered. `r_max=0` corresponds to QROM.

The upper plots show Toffoli counts broken into contributions. The lower plots show qubit counts. The result illustrates the cost/space trade-off as more QROAM workspace is allowed.

### 3.73 Why Algorithm 1 is not enough for sign fixing

Algorithm 1's unrestricted-PUI procedure does not guarantee that every basis state is visited in a PUI. A state may already start in the subspace or may be mapped into the subspace before it becomes part of a batch.

If the goal is to perform a sign fix for every relevant state, a state that is never visited is a problem.

### 3.74 Algorithm 3's key change

Algorithm 3 modifies the isometry construction:

1. Add one extra marker qubit to the tableau, initialized to `|1>` for every row.
2. Replace unrestricted PUI with restricted PUI.
3. When a PUI visits a basis state's subspace address, it also sets the marker qubit to zero.
4. If a state is already in the subspace but has not yet been part of a batch, the marker lets the algorithm identify it and move it into the processing logic.
5. The algorithm can then guarantee the required iteration/sign-fix coverage.

The paper also describes undoing the counter-effects of later CX gates on previously batched states. This bookkeeping is visible in Algorithm 3 on page 21.

### 3.75 Using a Z gate for a sign

The Pauli-Z gate acts as:

$$
Z|0\rangle=|0\rangle,
\qquad
Z|1\rangle=-|1\rangle.
$$

A marker/ancilla prepared in `|1>` can therefore acquire a `-1` phase when the state needs a sign correction. The algorithm's additional bookkeeping makes this phase fix part of the isometry.

### 3.76 Purely real target states

If a coefficient is real and non-zero, its phase is only a sign:

$$
c_i\in\mathbb{R}\setminus\{0\}
\quad\Longrightarrow\quad
\frac{c_i}{|c_i|}\in\{+1,-1\}.
$$

Equivalently, the phase is either `0` or `pi` modulo `2pi`. The final phase-encoding part of the dense preparation can be removed, and the sign information can be incorporated into the isometry.

This does **not** mean arbitrary complex phases are handled by the same sign-only trick. A general complex coefficient may have a phase anywhere on the unit circle.

### 3.77 Restricted-PUI cost for the real-state variant

The adapted real-state isometry uses restricted PUI, so the logarithmic PUI term is more expensive than unrestricted PUI. The paper gives:

$$
\boxed{
T_{\mathrm{iso,real}}
\leq
\left\lceil\frac{s}{m}\right\rceil
\left(2m+\log_2\frac{\widetilde{s}}{m}-3\right).
}
$$

The final `log(tilde{s}/2)` term from Equation (3) can be omitted because Algorithm 3 iterates over all states and does not need the separate final fix-up operation described in Section 2.

### Checkpoint — page 13

- [ ] I can explain why Algorithm 1 may skip some basis states.
- [ ] I can explain why the extra marker ancilla helps.
- [ ] I can explain why Algorithm 3 uses restricted PUI.
- [ ] I can explain why real coefficients reduce phase information to signs.
- [ ] I can explain why the real-state isometry has a different logarithmic term.

---

## PDF page 14 — Figure 10 benchmarks and conclusion begins

<details>
<summary><strong>Open the original supplied PDF page 14 / 22</strong></summary>

![Original PDF page 14](assets/pdf_page_14.png)

</details>


### 3.78 Figure 10, left: empirical Toffoli behaviour

Figure 10 compares Algorithm 1 (unrestricted) and Algorithm 3 (restricted) on random `s`-sparse states. The vertical axis is the Toffoli count divided by `s`.

For sufficiently large `n`, the restricted variant also approaches `s` in the tested random instances. However, for a given sparsity there are regimes where restricted PUI costs substantially more than unrestricted PUI.

Therefore the authors recommend considering both variants, together with the available qubit budget, for a given target state.

### 3.79 Figure 10, right: classical runtime table

The table reports classical implementation times for Algorithm 1 (unrestricted) and Algorithm 3 (restricted):

| `s` | Unrestricted (seconds) | Restricted (seconds) |
|---:|---:|---:|
| `10^2` | 0.0004 | 0.0003 |
| `10^3` | 0.0043 | 0.0037 |
| `10^4` | 0.0897 | 0.0981 |
| `10^5` | 4.5485 | 4.7399 |
| `10^6` | 26.056 | 22.356 |
| `10^7` | 1488.7 | 813.22 |

The table was measured on a CPU node with two AMD EPYC 7452 processors. The implementations use one thread for `s <= 10^5` and multithreading for larger cases. The caption says the restricted implementation is faster in the multithreaded regime because of how multithreading is implemented.

**Do not confuse these numbers with quantum Toffoli counts.** They are wall-clock times for classical preprocessing that constructs the isometry.

### 3.80 What the conclusion begins to say

The authors summarize the key contribution: refine the Malvetti et al. sparse-isometry method by grouping individual multi-controlled-X zeroing operations into partial unary iterations.

They present restricted and unrestricted PUI as primitives that may be useful independently.

They also summarize the full-circuit optimization: move angle-register uncomputation and, for real states, phase encoding into the isometry.

### Checkpoint — page 14

- [ ] I can explain both panels of Figure 10.
- [ ] I can separate quantum resource counts from classical preprocessing time.
- [ ] I can explain why no one PUI variant is best for every instance.

---

## PDF page 15 — Conclusion, limitations, future work, acknowledgements, and author contributions

<details>
<summary><strong>Open the original supplied PDF page 15 / 22</strong></summary>

![Original PDF page 15](assets/pdf_page_15.png)

</details>


### 3.81 The authors' stated contribution

The paper claims improved Toffoli cost for sparse-state preparation through a batched isometry construction. It says the resulting circuits are, to the authors' knowledge, the most efficient sparse-state preparation circuits in the literature in terms of Toffoli and qubit counts at the time of writing.

This is a literature-positioning statement, not a mathematical theorem that no better algorithm can exist.

### 3.82 Toffoli count may become an incomplete runtime proxy

The authors note that advances in magic-state cultivation and distillation can change the time/space cost of non-Clifford resource production. If that cost changes, a fixed Toffoli count may be a less reliable proxy for algorithm runtime.

They point to more adapted runtime/resource models in [36]–[38].

The distinction:

- Gate count is a circuit-level resource metric.
- Runtime is a schedule/architecture-level metric that depends on more than gate count.

### 3.83 The sublinear-in-s question

The conclusion initially says that whether sparse state preparation can achieve a Toffoli cost sublinear in `s` with practically limited ancillas remains open.

Then the paper adds a note: after the preprint appeared, references [39] and [40] answered the question affirmatively with algorithms whose Toffoli count scales as:

$$
O(\sqrt{s}),
$$

using Toffoli/ancilla trade-offs.

This note is essential. Do not present the earlier “open question” sentence as the final state of the literature described by this paper. The note itself says later work resolves it.

### 3.84 Implementation status described by the paper

The circuits are available as Qualtran Bloqs [30]. The classical isometry-finding code is written in SIMD-accelerated, multithreaded Rust. The authors say the implementation can find isometries for `s=10^7` in a few minutes on reasonable hardware and suggest GPU code as a path to larger instances.

### 3.85 Acknowledgements and contributions

The paper acknowledges funding from the Ministry of Economic Affairs, Labour and Tourism Baden-Württemberg through the Competence Center Quantum Computing Baden-Württemberg, and thanks Benjamin Desef.

Author contributions:

- Felix Rupprecht developed the idea, implemented it, and wrote the manuscript.
- Sabine Wölk supervised the work and provided feedback.

The paper discloses that open-weight LLMs were used for language checking and minor coding assistance. It does not attribute the central research idea or implementation to an LLM.

### Checkpoint — page 15

- [ ] I can state the paper's contributions without overstating them.
- [ ] I can explain why Toffoli count may not equal runtime.
- [ ] I know that references [39] and [40] are reported as later `O(sqrt(s))` results.
- [ ] I can describe what the authors say about their released implementation.

---

## PDF pages 16–17 — Bibliography

These pages list references [1]–[41]. The compact annotated bibliography is provided in [Section 8](#8-references-short-summary-and-why-each-is-cited).

The key way to read the bibliography is by role:

- [1]–[4] situate state preparation in applications such as linear systems, QML, simulation, and quantum chemistry.
- [5], [17]–[19], [34]–[38] provide resource-accounting and fault-tolerant context.
- [12]–[16], [20]–[22], [28] are sparse-state-preparation alternatives or baselines.
- [23], [24], [25], [32], [33] support circuit primitives, unary iteration, ancilla methods, phase-gradient rotations, QROM/QROAM, and sign correction.
- [29], [30], [41] are software/artifact/typesetting references.
- [39], [40] are the later sublinear-scaling results mentioned in the conclusion.

**Reference-reading priority for understanding this paper:** read [20] first (baseline), then [23]/[24] (circuit primitives), then [33] (QROAM/sign-fix context), and then [39]/[40] for the later research landscape.

---

## PDF page 18 — Appendix A (AND gates) and Appendix B (proof of Equation 6)

<details>
<summary><strong>Open the original supplied PDF page 18 / 22</strong></summary>

![Original PDF page 18](assets/pdf_page_18.png)

</details>


### 3.86 Appendix A: AND gate and its measurement-based adjoint

Figure 11 recalls the AND primitive:

$$
|a\rangle|b\rangle|0\rangle
\longmapsto
|a\rangle|b\rangle|a\land b\rangle.
$$

The figure also shows the measurement-based inverse/adjoint. The important idea is that the operation computes a reversible temporary condition into an ancilla, and the measurement-based procedure removes that temporary information while restoring the ancilla as required.

The paper attributes this construction to [23] and [24].

### 3.87 Appendix B: why a Hamming-weight sum appears

The proof supports Equation (6). Let `h(x)` be the Hamming weight of the binary representation of integer `x`.

Define:

$$
C_r=\{x\in\mathbb{N}_{<r}:h(x)>1\},
$$

and:

$$
S_r=\sum_{x\in C_r}(h(x)-1).
$$

Why this exact sum? In unrestricted prefix selection, a prefix with `h(x)` ones needs `h(x)-1` Toffolis when it has at least two ones. Prefixes of weight zero or one require no such Toffoli chain. So `S_r` is a count of the relevant prefix-selection cost over integers below `r`.

### 3.88 The lemma

For `2^(k-1) <= r <= 2^k`, the paper proves:

$$
\boxed{S_r\leq r\left(\frac{k}{2}-1\right)+1.}
$$

It proves this by induction on `k`.

### 3.89 Base case

For `k=1`, there are only a few integers in the range. The sum can be checked directly, so the inequality holds.

### 3.90 Inductive step: split the integers into lower and upper halves

Assume the lemma holds for the relevant smaller value `k-1`.

Split the set into:

- `x < 2^(k-1)`;
- `x >= 2^(k-1)`.

For the upper half, write:

$$
x=2^{k-1}+y.
$$

In binary, this adds a leading 1. Therefore:

$$
h(x)=h(y)+1.
$$

So:

$$
h(x)-1=h(y).
$$

The upper-half values correspond to `y>0`, so there are `r-2^(k-1)-1` such values under the paper's endpoint convention. If `h(y)=1`, then `h(y)-1=0`; these terms contribute zero and may be omitted from the sum. Thus the remaining non-zero contribution can be written over `C_{r-2^(k-1)}`.

Applying the induction hypothesis to that lower-dimensional sum yields the bound for `S_r`.

### 3.91 Finish the algebra

The paper's displayed proof combines the lower-half induction bound and upper-half contribution to obtain an expression no greater than:

$$
r\left(\frac{k}{2}-\frac12\right)-\frac{2^k}{2}+1.
$$

Since `r <= 2^k`, the subtracted term `-2^(k-1)` can only make the expression smaller, and in particular:

$$
S_r\leq r\left(\frac{k}{2}-1\right)+1.
$$

This is the lemma needed to bound the prefix-selection cost for an incomplete address range.

### What this proof is *not* doing

It is not proving the correctness of the whole quantum state-preparation circuit. It proves a combinatorial upper bound on a Toffoli-count contribution. Circuit correctness is handled by the reversible construction and the algorithmic bookkeeping; this lemma supports the resource estimate.

### Checkpoint — page 18

- [ ] I can define Hamming weight.
- [ ] I can explain why `h(x)-1` counts Toffolis for a prefix with at least two ones.
- [ ] I can explain why the proof uses `x=2^(k-1)+y`.
- [ ] I can explain what Equation (6)'s inductive bound is used for.

---

## PDF page 19 — Algorithm 1: finding the isometry and bijection

<details>
<summary><strong>Open the original supplied PDF page 19 / 22</strong></summary>

![Original PDF page 19](assets/pdf_page_19.png)

</details>


### 3.92 Inputs and outputs

**Input:** a tableau of `s` distinct `n`-bit target basis strings, split into `ell` subspace bits and `n-ell` residual bits.

**Output:** a circuit `G` and a bijection `f` satisfying:

$$
G|C_i\rangle=|f(i)\rangle_s|0\rangle_r.
$$

### 3.93 Initialization

The pseudocode initializes:

- `G = []`: empty circuit list;
- `k = 0`: next compact label;
- `batch = []`: row indices in the current batch;
- `m`: largest power of two with `m <= n-ell`.

### 3.94 Main loop: what the algorithm is tracking

The variable `b` is the current batch size (`b=|batch|`). Do not confuse it with the angle precision `b` in Section 4; they are separate uses of the same letter.

At each stage the algorithm must:

1. Flush a full batch through unrestricted PUI.
2. Decide whether the remaining tableau can be completed with a restricted final PUI.
3. If an exceptional collision appears, add a CMX/MCX correction.
4. Otherwise, find a new target row and transform it into the next one-hot batch element.
5. Update the tableau and increment `k`.

### 3.95 Full-batch branch

When `b=m`, append an unrestricted PUI over the current interval that maps all batch rows:

$$
|k_j\rangle_s|e_{q_j}\rangle_r
\mapsto
|k_j\rangle_s|0\rangle_r.
$$

Apply that PUI to every row of the classical tableau so the data structure reflects the circuit's action, including unrestricted side effects. Then clear the batch.

### 3.96 Final restricted branch

When all rows outside the current batch already lie in the subspace, use a restricted PUI so higher subspace states are left untouched. If the specific collision described in the pseudocode occurs, the algorithm uses a CMX followed by an MCX to repair the state. Then it reads the compact labels from the finished tableau and returns `G,f`.

### 3.97 Adding a new row

If an unprocessed row has a usable residual 1 further to the right, swap it into the next desired position. Otherwise, use a Toffoli with the carefully selected controls described on page 6. Then apply CMX to put the row into the next batch form, append the row index to `batch`, and increment `k`.

### 3.98 Why the pseudocode updates the whole tableau

A quantum gate acts on the entire Hilbert space, not just the one classical row that the compiler had in mind. The algorithm knows the target support, so it tracks how every listed basis string is transformed. This is especially important for unrestricted PUI because some non-batch rows may also be affected.

### 3.99 A compiler analogy

A useful analogy is a compiler that has a list of input states and a sequence of reversible gate instructions. After appending each instruction, it updates its classical representation of every supported basis state. The output is a gate sequence plus a mapping from original row identity to final compressed label.

### Checkpoint — page 19

- [ ] I can explain every initialization variable.
- [ ] I can explain when a full batch is flushed.
- [ ] I can explain why the final batch may use restricted PUI.
- [ ] I can explain the row-selection and correction branches.
- [ ] I can explain how the final bijection is read from the tableau.

---

## PDF page 20 — Algorithm 2: constructing unrestricted PUI recursively

<details>
<summary><strong>Open the original supplied PDF page 20 / 22</strong></summary>

![Original PDF page 20](assets/pdf_page_20.png)

</details>


### 3.100 Input/output

Algorithm 2 receives:

- a requested address interval `S=[l,r]` in a `w`-qubit address register;
- target operations `U_l,...,U_r`.

It returns:

- circuit `G`;
- extra-address set `L`;
- map `g:L -> {l,...,r}`.

The resulting action is:

$$
G=
\sum_{i=l}^{r}|i\rangle\langle i|\otimes U_i
+
\sum_{i\in L}|i\rangle\langle i|\otimes U_{g(i)}.
$$

### 3.101 Initialization

The recursion starts from the entire address register interval:

$$
I=[0,2^w-1].
$$

The algorithm recursively splits this interval into left and right halves until it reaches a leaf (a single address value).

### 3.102 Parameters in the recursive function

The recursive function `UPUI(interval, control, free)` tracks:

- `interval`: the current binary-tree interval;
- `control`: an existing control condition selecting this interval, if one exists;
- `free`: the set of address-bit positions whose controls were intentionally omitted.

### 3.103 Leaf case

If the interval is a single address `i`, append `U_i`, controlled if necessary by the current control. If some address positions are free, construct all other address values that match `i` on non-free positions and contain at least one 1 in the free positions. Add those extra addresses to `L` and set `g(j)=i` for each.

### 3.104 Internal-node cases

The algorithm tests whether the left and right halves intersect the requested interval.

- **Both overlap:** build the normal branch condition, recurse left and right, and uncompute the AND condition.
- **Only left overlaps:** recurse left but add the current split bit to `free`. This is the unrestricted shortcut; it creates possible extra effects in the right half.
- **Only right overlaps:** construct a right-branch condition if needed and recurse right.

### 3.105 Why Algorithm 2 matters

Algorithm 1 uses unrestricted PUI. Algorithm 2 is what constructs the circuit *and* tells Algorithm 1 exactly which extra addresses receive which target operations. Without the returned `L` and `g`, the compiler could not reliably update the tableau.

### Checkpoint — page 20

- [ ] I can state Algorithm 2's input and output.
- [ ] I can explain the role of the `free` set.
- [ ] I can describe the three branch cases.
- [ ] I can explain how `L` and `g` are generated at leaves.

---

## PDF page 21 — Algorithm 3: isometry with phase fixing

<details>
<summary><strong>Open the original supplied PDF page 21 / 22</strong></summary>

![Original PDF page 21](assets/pdf_page_21.png)

</details>


### 3.106 Different result from Algorithm 1

Algorithm 1 returns a map without an explicit sign:

$$
G|C_i\rangle=|f(i)\rangle_s|0\rangle_r.
$$

Algorithm 3 receives a list of signs `a_i in {+1,-1}` and returns:

$$
\boxed{G|C_i\rangle=a_i|f(i)\rangle_s|0\rangle_r.}
$$

It is designed to incorporate sign correction into the isometry.

### 3.107 Extra marker column

Algorithm 3 extends the tableau with an extra qubit (the `(n+1)`-th column), initialized to `|1>` for every basis-state row:

$$
|D_i\rangle_e=|1\rangle_e.
$$

This is a processing marker. It is not one of the original `n` data qubits in the target state.

### 3.108 Restricted PUI and complete visitation

Algorithm 3 uses restricted PUI instead of unrestricted PUI. When a PUI iterates over a basis state's subspace content, it also maps the marker qubit from `|1>` to `|0>` and applies the associated sign `a_j`.

If there are multiple states with the same subspace label, the marker bookkeeping ensures that the algorithm can track them consistently. States that were in the subspace without being part of a batch are not silently skipped; the marker is used to bring them into the required processing sequence.

### 3.109 Undoing counter-effects of later CX gates

The pseudocode includes a loop over already-batched rows whose marker remains `|1>`. It applies CX corrections to the relevant residual positions to undo the counter-effect of later CX operations before continuing. Then it uses a CX from the marker column to the next residual position and applies the CMX that constructs the next batch member.

This is more involved than Algorithm 1 because the algorithm must preserve both the state mapping and the sign/marker bookkeeping.

### 3.110 Why Algorithm 3 is useful for real coefficients

For purely real coefficients, each coefficient's phase is only `+1` or `-1`. Algorithm 3 can encode this sign as part of the isometry, avoiding a separate final phase-encoding stage in dense-state preparation.

The algorithm's output is an isometry map with the correct sign, not a claim that arbitrary complex phases can be represented by a single sign bit.

### Checkpoint — page 21

- [ ] I can write Algorithm 3's input/output relation.
- [ ] I can explain why the marker starts at `|1>`.
- [ ] I can explain why restricted PUI is used.
- [ ] I can explain how a sign is applied with a Z operation.
- [ ] I can distinguish a real coefficient's sign from an arbitrary complex phase.

---

## PDF page 22 — Appendix D: resource comparison of prior algorithms

<details>
<summary><strong>Open the original supplied PDF page 22 / 22</strong></summary>

![Original PDF page 22](assets/pdf_page_22.png)

</details>


### 3.111 Why Appendix D exists

Many earlier sparse-state-preparation papers optimized asymptotic circuit size. This paper wants constant-factor Toffoli estimates and ancilla counts. Appendix D recalculates comparable resource costs under those metrics.

### 3.112 Family 1: iterative preparation, one basis state at a time

The methods in [12], [13], [21], and [22] each prepare one basis state with its coefficient, requiring a controlled rotation and a multi-controlled-X or equivalent operation.

The paper uses the standard AND construction: a `w`-controlled-X can be implemented with `w-1` Toffolis and `w-2` ancillas.

- **[12] BE-QRAM:** batches computational-basis states and uses controls whose count depends on `k=floor(log2 n - log2 log2 n)`. Appendix D counts the per-state and per-batch controlled-X operations.
- **[13]:** uses a halving procedure, giving at most `ceil(log2 d)` controls.
- **[21]:** the cited work declares an `O(n)` cost without details sufficient for the authors' comparison, so the appendix assumes an `n`-controlled-X.
- **[22] CVO-QRAM:** controls are the qubits where the current basis state has 1. Summing Hamming weights over all `s` states gives a worst-case lower bound of `ns/2`.

### 3.113 Family 2: dense preparation plus isometry

This includes [4], [14], [16], and [20]. Appendix D compares the isometry part.

**Reference [14].** Its isometry is a permutation decomposed into cycles. A cycle of length `w` is implemented using `w+1` multi-controlled-X gates with `n` controls. The stated worst-case Toffoli cost is:

$$
3s(n-1),
$$

with `n-1` ancillas.

**Reference [16].** Its permutation is represented by at most `s` disjoint transpositions. The appendix derives a Toffoli expression for a batch of `m` transpositions:

$$
\left\lceil\frac{s}{m}\right\rceil
\left(n-\lfloor\log_2(2m)\rfloor-1
+2m(\lceil\log_2(2m)\rceil-1)\right).
$$

For Toffoli count, the appendix says the expression is minimized at `m=s` (one batch), giving:

$$
2s(\lceil\log_2(2s)\rceil-1)+n-\lfloor\log_2(2s)\rfloor-1.
$$

The table drops the final `-1` for brevity and uses the stated ancilla approximation under `s<<2^n`.

**Reference [20].** This is the Malvetti sparse-isometry method analyzed in Section 2, with worst-case isometry cost `s(ell-1)` and `ell-2` ancillas under its AND-ladder implementation.

### 3.114 The point of Appendix D

The appendix is not merely a literature list. It tries to make different algorithms comparable under one resource model. It shows why the authors choose [20] as their baseline and why gate-count claims from papers using different metrics must be compared carefully.

### Checkpoint — page 22

- [ ] I can explain why Appendix D recalculates resource estimates.
- [ ] I can describe the broad distinction between the two families.
- [ ] I can explain why [20] is the main baseline.
- [ ] I can explain why an asymptotically good circuit-size result may not imply the best Toffoli/ancilla trade-off.

---

# 4. Derivation workbook

This section gathers the main mathematical derivations in one place. It is intended for active work: try each derivation first, then open the worked steps.

## 4.1 Derivation: the compact register width

**Question:** why `ell=ceil(log2 s)`?

<details>
<summary><strong>Open derivation</strong></summary>

A register of `ell` qubits has `2^ell` basis labels. Need at least `s` labels:

$$2^\ell\geq s.$$

Take base-two logarithms:

$$\ell\geq\log_2s.$$

The smallest integer satisfying this is:

$$\boxed{\ell=\lceil\log_2s\rceil.}$$

Then `tilde{s}=2^ell` is the capacity of the compact register. If `s` is not a power of two, unused labels remain.
</details>

## 4.2 Derivation: baseline Toffoli cost

**Question:** why does reference [20] have worst-case `s(ell-1)` Toffolis?

<details>
<summary><strong>Open derivation</strong></summary>

The baseline makes one `ell`-controlled-X zeroing operation for every target state outside the subspace. The paper decomposes that multi-controlled-X using an AND-ladder construction with `ell-1` Toffolis. In the worst case all `s` states need it:

$$
T_{\mathrm{baseline}}=s(\ell-1).
$$

This is a worst-case isometry count, not the whole end-to-end state-preparation cost.
</details>

## 4.3 Derivation: number of batches and why the ceiling appears

**Question:** why does the number of batches equal `ceil(s/m)`?

<details>
<summary><strong>Open derivation</strong></summary>

Each full batch holds `m` states. The minimum integer number `B` such that `Bm >= s` is:

$$B=\left\lceil\frac{s}{m}\right\rceil.$$

Example: if `s=100` and `m=16`, then `ceil(100/16)=7`. Six full batches hold 96 states and the last batch holds four.
</details>

## 4.4 Derivation: Equation (3), batch-building overhead

**Question:** why is the non-PUI overhead bounded by `s-ceil(s/m)+log2(tilde{s}/2)`?

<details>
<summary><strong>Open derivation</strong></summary>

There are `s` total batch elements and `B=ceil(s/m)` batches. The first element of every batch is guaranteed not to require the extra Toffoli in the stated batch-construction accounting. Therefore the other elements contribute at most:

$$s-B=s-\left\lceil\frac{s}{m}\right\rceil.$$

The paper adds a final exceptional correction bounded by `log2(tilde{s}/2)`. Thus:

$$
T_{\mathrm{extra}}\leq s-\left\lceil\frac{s}{m}\right\rceil+\log_2(\widetilde{s}/2).
$$

This is Equation (3). The final logarithmic term is tied to the special final-batch collision/correction described on page 6.
</details>

## 4.5 Derivation: Equation (4) is a controlled family of operations

**Question:** what does the PUI specification mean?

<details>
<summary><strong>Open derivation</strong></summary>

The address register is a selector. If its value is `i`, the target register receives `U_i`, while the address is preserved:

$$U(|i\rangle_a|t\rangle_t)=|i\rangle_a(U_i|t\rangle_t).$$

This is a compact mathematical specification for a circuit that performs different operations for different address values. The equation itself does not say how many Toffolis are needed; the binary-tree construction and its control bookkeeping determine that.
</details>

## 4.6 Derivation: Equation (5), Hamming-weight count

**Question:** why does the full unrestricted prefix-selection count equal `2^k(k/2-1)+1`?

<details>
<summary><strong>Open derivation</strong></summary>

Let the prefix length be `k`. Across all `2^k` bitstrings, each bit is 1 in exactly half of them. There are `k` bit positions, so the total number of 1-bit occurrences is:

$$
2^{k-1}k.
$$

The prefixes with exactly one 1 contribute `k` such occurrences, one for each possible position. Those prefixes require no Toffoli prefix-selection chain. Remove them:

$$
2^{k-1}k-k.
$$

Now count how many prefixes have at least two ones. There are `2^k` total strings; remove the all-zero string and the `k` strings of Hamming weight one:

$$
2^k-k-1.
$$

For each remaining prefix with Hamming weight `h`, the cost is `h-1`. Therefore:

$$
\begin{aligned}
T_{\mathrm{prefix}}
&=(\text{total relevant ones})-(\text{number of relevant strings})\\
&=(2^{k-1}k-k)-(2^k-k-1)\\
&=2^{k-1}k-2^k+1\\
&=2^k\left(\frac{k}{2}-1\right)+1.
\end{aligned}
$$

That is Equation (5), with `k=w-q=log2(S_addr/m)` in this guide's notation.
</details>

## 4.7 Derivation: full-address unrestricted PUI cost

**Question:** how do Equation (5) and the per-interval unary-iteration cost combine?

<details>
<summary><strong>Open derivation</strong></summary>

There are `R=S_addr/m=2^k` intervals. The first (all-zero prefix) interval uses the uncontrolled unary iteration costing `m-2`; the other `R-1` intervals use the controlled form costing `m-1`:

$$
(R-1)(m-1)+(m-2)=R(m-1)-1.
$$

Add Equation (5):

$$
R\left(\frac{k}{2}-1\right)+1.
$$

The `-1` and `+1` cancel:

$$
\begin{aligned}
T_{\mathrm{uPUI,full}}
&=R(m-1)-1+R(k/2-1)+1\\
&=R(m+k/2-2)\\
&=\frac{S_{\mathrm{addr}}}{m}
\left(m+\frac12\log_2\frac{S_{\mathrm{addr}}}{m}-2\right).
\end{aligned}
$$
</details>

## 4.8 Derivation: restricted PUI full-address cost

**Question:** why does the restricted version have a full logarithmic term?

<details>
<summary><strong>Open derivation</strong></summary>

For restricted PUI, every interval is selected with the full prefix-control construction. The paper counts `m-1` Toffolis for the controlled unary iteration over the `m` addresses and `k-1` Toffolis for selecting the upper `k`-bit prefix. Thus the per-interval count is:

$$
(m-1)+(k-1)=m+k-2.
$$

There are `R=S_addr/m` intervals, so:

$$
T_{\mathrm{rPUI,full}}=
\frac{S_{\mathrm{addr}}}{m}
\left(m+\log_2\frac{S_{\mathrm{addr}}}{m}-2\right).
$$

Compare with unrestricted PUI: the restricted variant pays `k` rather than `k/2` in the logarithmic term.
</details>

## 4.9 Derivation: Equation (6) and the incomplete address range

**Question:** why can the full-address prefix count be replaced by an inductive upper bound when `s` is not a power of two?

<details>
<summary><strong>Open derivation</strong></summary>

The isometry only needs to visit the first `s` address values, with `2^(w-1)<s<2^w`. Prefixes near `s` can contribute more Toffolis than prefixes near zero, so the full-power-of-two average is not enough by itself.

Appendix B defines `h(x)` as Hamming weight and proves:

$$
\sum_{x<r,\ h(x)>1}(h(x)-1)
\leq r\left(\frac{k}{2}-1\right)+1
$$

whenever `2^(k-1)<=r<=2^k`.

Set `k=w-q` and `r=ceil(s/m)`. Since `m=2^q`, the bound on prefix selection becomes:

$$
\left\lceil\frac{s}{m}\right\rceil
\left(\frac{w-q}{2}-1\right)+1.
$$

Adding the interval unary-iteration costs yields Equation (7):

$$
T_{\mathrm{uPUI}}
\leq\left\lceil\frac{s}{m}\right\rceil
\left(m+\frac12\log_2\frac{S_{\mathrm{addr}}}{m}-2\right).
$$
</details>

## 4.10 Derivation of Equation (1): the final combination

This is the most important derivation. It was shown in full on page 10 and is reproduced here as a compact derivation to practice.

Let:

$$R=\lceil s/m\rceil,\qquad L=\log_2(\widetilde{s}/m).$$

Combine:

- Equation (7): `R(m+L/2-2)`;
- final restricted-PUI adjustment: `L/2`;
- Equation (3): `s-R+log2(tilde{s}/2)`.

So:

$$
T\leq R(m+L/2-2)+L/2+s-R+\log_2(\widetilde{s}/2).
$$

Use `s<=Rm`:

$$
T\leq R(2m+L/2-3)+L/2+\log_2(\widetilde{s}/2).
$$

Combine the logs:

$$
\frac{L}{2}+\log_2(\widetilde{s}/2)
=\log_2\left(\frac{\widetilde{s}^{3/2}}{2\sqrt m}\right).
$$

That gives Equation (1).

## 4.11 Derivation: why the leading worst-case term is approximately `2s`

**Question:** where does the `2s` headline come from?

<details>
<summary><strong>Open derivation</strong></summary>

For sufficiently large available `n`, the allowed power-of-two batch size `m` can be large enough that the leading `2m` term dominates the logarithmic and constant terms inside the parentheses. Then:

$$
\left\lceil\frac{s}{m}\right\rceil(2m)
\approx\frac{s}{m}(2m)=2s.
$$

The remaining terms are lower-order in the regime described. Thus the leading worst-case isometry behaviour is essentially `2s`.

This is the isometry bound. It is not, by itself, the complete state-preparation cost: dense-state preparation and any remaining phase/sign work also matter.
</details>

## 4.12 Derivation: approximate improvement factor over [20]

The baseline behaves as:

$$
s(\ell-1)\approx s\log_2s.
$$

The new worst-case leading behaviour is approximately `2s`. Their ratio is therefore approximately:

$$
\frac{s(\ell-1)}{2s}=\frac{\ell-1}{2}\approx\frac12\log_2s.
$$

This explains the abstract's “roughly `log(s)/2` improvement factor” for sufficiently large `n`.

## 4.13 Derivation: QROM sum

For address sizes `k=2,...,ell`, the paper's QROM cost per lookup is `2^k-2`.

<details>
<summary><strong>Open derivation</strong></summary>

$$
\begin{aligned}
T_{\mathrm{QROM}}
&=\sum_{k=2}^{\ell}(2^k-2)\\
&=\left(2^{\ell+1}-4\right)-2(\ell-1)\\
&=2^{\ell+1}-2\ell-2\\
&<2\widetilde{s}.
\end{aligned}
$$

The separate sign-fix lookup adds `2^(ell-1)-2`, yielding the paper's bound below `2.5 tilde{s}`.
</details>

## 4.14 Derivation: QROAM's tunable parameter

For one QROAM lookup:

$$
T(r)=2^{k-r}+b(2^r-1).
$$

Put `x=2^r` and ignore the small `-1` correction to obtain:

$$
T(x)\approx 2^k/x+bx.
$$

Differentiating and setting to zero gives:

$$
x\approx\sqrt{2^k/b},
$$

or:

$$
2^r\approx\sqrt{2^k/b}.
$$

At the optimum, the two leading terms balance and the cost is roughly:

$$
2\sqrt{b2^k}.
$$

More ancillas allow a larger `r`, and fewer Toffolis are required. The resource decision is a time/space-like trade-off in the circuit cost model.

## 4.15 Derivation: why a real coefficient has only a sign phase

Write a non-zero coefficient in polar form:

$$
c_i=|c_i|e^{i\phi_i}.
$$

If `c_i` is real and positive, its phase is 0. If `c_i` is real and negative, its phase is `pi` modulo `2pi`. Therefore:

$$
e^{i\phi_i}\in\{+1,-1\}.
$$

This is why a Z-type sign correction can encode the phase for real coefficients. It does not extend to an arbitrary complex phase without a more general rotation.

## 4.16 Derivation: classical `O(s^2 n)` is not quantum Toffoli cost

The tableau contains `s*n` bits. A constant number of full-tableau scans/updates per row costs `O(sn)` per row, and there are `O(s)` rows/iterations:

$$
O(s)\cdot O(sn)=O(s^2n).
$$

This is classical preprocessing complexity. The quantum Toffoli count is a separate resource estimate.

---

# 5. Assumptions, scope, and source-consistency checks

This chapter is deliberately explicit. A research explanation becomes unreliable when assumptions, approximations, and source typos are silently blended together.

## 5.1 Mathematical and algorithmic assumptions made in the paper

1. The target is supplied classically as a list/tableau of `s` distinct computational-basis bitstrings and their coefficients/signs.
2. The support size `s` is known for the construction.
3. The compact subspace width is `ell=ceil(log2 s)`.
4. The PUI address register has `w=ell` in the isometry application.
5. The batch width `m` is a power of two and satisfies `m<=n-ell`.
6. The `m` residual one-hot basis states `e_0,...,e_{m-1}` must fit in the non-subspace register.
7. The cost formulas are Toffoli/ancilla resource bounds in the paper's Clifford+Toffoli accounting.
8. The full-circuit dense-state-preparation estimates use specified QROM/QROAM variants and parameters.
9. Phase-gradient-state preparation and its register are excluded from the table's resource totals.
10. The phase-gradient rotation's `b` Toffoli cost is neglected compared with QRO(A)M costs.
11. Table 1 uses a single `r` for clean QROAM calls for simplicity.
12. Table 1 assumes the qubit peak occurs during QRO(A)M operations, not during rotations.
13. Numerical benchmarks use random sparse states; they are not worst-case proofs.
14. The classical algorithm's stated asymptotic complexity is `O(s^2 n)`.

## 5.2 Claims versus evidence

| Statement | Type of support in the paper |
|---|---|
| Baseline [20] worst-case isometry cost `s(ell-1)` | Analytical resource count under the stated decomposition |
| New Equation (1) | Analytical worst-case upper bound |
| Leading worst-case behaviour around `2s` | Asymptotic interpretation of Equation (1) in the relevant regime |
| Random-instance cost approaches `s` | Numerical benchmark observation |
| Classical search cost `O(s^2 n)` | Algorithmic complexity analysis |
| `s=10^7` implementation runtime | Specific CPU benchmark reported by the authors |
| QROAM can reduce Toffolis by using ancillas | Resource formula and parameter optimization |
| Real-state phase integration reduces dense-prep prefactor | Construction and resource analysis for real coefficients |
| Later `O(sqrt(s))` algorithms | Note in the paper citing [39] and [40] |

## 5.3 Source-consistency checks and apparent PDF typos

The supplied PDF contains at least two apparent internal inconsistencies worth flagging. They are recorded here rather than silently corrected.

### A. PDF page 6: final correction cost equality

The prose appears to print a line of the form:

$$
\lceil\log_2s\rceil+1=\log_2(\widetilde{s}/2).
$$

But the paper defines `tilde{s}=2^ell` with `ell=ceil(log2 s)`. Therefore:

$$
\log_2(\widetilde{s}/2)=\ell-1,
\qquad
\log_2(2\widetilde{s})=\ell+1.
$$

The printed equality is arithmetically inconsistent by two Toffolis. The displayed Equation (3) and the page-10 derivation of Equation (1) use `+log2(tilde{s}/2)`. The page-6 prose, however, says the exceptional correction costs `ell+1`. The PDF alone does not let us prove whether the `+1` on the left or the `/2` inside the logarithm is the typo. **For faithful reproduction, keep Equations (3) and (1) exactly as printed, but report this unresolved two-Toffoli discrepancy whenever you discuss the final correction term.** Do not present the page-6 equality as valid algebra.

### B. PDF page 13: Figure 9 caption labels Algorithm 1/3 inconsistently

The Figure 9 caption's final sentence appears to label Algorithm 1 as restricted and Algorithm 3 as unrestricted. However:

- the prose immediately below says Algorithm 1 does not guarantee that all basis states are visited and introduces Algorithm 3 to fix this;
- the page 13 prose says Algorithm 3 replaces unrestricted PUI with restricted PUI;
- Algorithm 3 on page 21 explicitly uses restricted PUI;
- Figure 10's caption on page 14 identifies Algorithm 1 as unrestricted and Algorithm 3 as restricted.

Therefore, the consistent interpretation is **Algorithm 1 = unrestricted PUI; Algorithm 3 = restricted PUI with phase fixing**. The page 13 Figure 9 caption appears to reverse the labels.

### C. Do not over-correct beyond the source

When an equation or caption is ambiguous, state the ambiguity and use the surrounding derivation/pseudocode only when it resolves the intended meaning. Do not silently invent a corrected published version.

## 5.4 Terminology that must remain distinct

- **Isometry-finding circuit `G`:** maps target basis states to compact labels.
- **State-preparation isometry `G†`:** maps compact labels to target basis states.
- **Restricted PUI:** preserves the identity action outside its requested interval.
- **Unrestricted PUI:** may perform extra operations above the interval and returns/induces a map `g` for bookkeeping.
- **Dense-preparation sign fixes:** measurement-induced signs from X-basis measurement of angle/QROAM registers.
- **Target-state phases:** the phases of the coefficients `c_i` themselves. For real states these are only signs.
- **Classical runtime:** time to construct the circuit from the tableau.
- **Quantum resource count:** Toffolis and qubits in the circuit model.

---

# 6. Implementation and reproduction checklist

The paper provides Qualtran Bloqs and Rust code through reference [30]. This guide does not claim to have run that artifact. The following is a source-aligned reproduction plan, not a report of completed execution.

## 6.1 Reproduce before rewriting

- [ ] Obtain the paper's official artifact from reference [30].
- [ ] Read its README and environment instructions before installing anything.
- [ ] Identify the Qualtran Bloqs used for the circuits.
- [ ] Identify the Rust implementation of the classical isometry-finding algorithm.
- [ ] Run the introductory notebook or smallest supplied example.
- [ ] Record exact dependency versions and command outputs.
- [ ] Reproduce one small instance before attempting a large `s`.

## 6.2 Build a small independent validation case

Choose small values, for example:

$$
n=6,\qquad s=4,\qquad \ell=2,\qquad n-\ell=4,\qquad m=4.
$$

Use four distinct six-bit target strings. For each state, store:

- original row identity `i`;
- original bitstring `C_i`;
- subspace part `C_i'`;
- residual part `C_i''`;
- current tableau representation after each operation;
- final compressed label `f(i)`.

## 6.3 Assertions your implementation should check

- [ ] Every input target basis string is distinct.
- [ ] The split point is exactly `ell=ceil(log2 s)`.
- [ ] `m` is a power of two and `m<=n-ell`.
- [ ] Each batch has no more than `m` rows.
- [ ] Each batch row has the expected one-hot residual form before its PUI.
- [ ] After the relevant PUI, the batch residual registers are zero.
- [ ] Any unrestricted-PUI side effects are reflected in the tableau.
- [ ] Every target row ends with a zero residual register.
- [ ] Final subspace labels are pairwise distinct.
- [ ] The resulting `f` is injective and maps all `s` input rows to `s` labels.
- [ ] The circuit is reversible on the supported states.
- [ ] The inverse circuit maps each compact label back to its original target bitstring.

## 6.4 Statevector validation for a tiny case

For a small number of qubits, construct the statevector of the dense compact state:

$$
|\theta\rangle=\sum_i c_i|f(i)\rangle_s|0\rangle_r.
$$

Apply the inverse isometry `G†` and compare the result with the target state. A standard comparison is fidelity:

$$
F=|\langle\Theta_{\mathrm{target}}|\Theta_{\mathrm{prepared}}\rangle|^2.
$$

For a correct exact statevector simulation (ignoring any intentional approximations in rotations), the fidelity should be 1 up to numerical precision and global-phase conventions.

## 6.5 What to benchmark separately

Record at least these distinct metrics:

| Metric | What it measures |
|---|---|
| Isometry Toffoli count | Quantum non-Clifford cost of the isometry circuit |
| Dense-prep Toffoli count | Quantum cost of preparing compact amplitudes/phases |
| Ancilla count | Workspace requirement |
| Peak qubit count | Maximum simultaneously live qubits under the chosen scheduling model |
| Classical compile time | Time to construct the circuit from the input tableau |
| Random-instance ratio | Empirical `Toffolis/s` over a stated instance distribution |
| Worst-case upper bound | Analytical guarantee from the formula |

Never mix classical construction time with quantum Toffoli count in a single unlabeled “runtime” value.

---

# 7. Mastery examination

Attempt the questions before opening the answers. The goal is not to memorize the prose; it is to reconstruct the reasoning.

## 7.1 Concept questions

1. What exactly makes a state `s`-sparse on `n` qubits?
2. Why can `s` amplitudes be stored in `ceil(log2 s)` qubits?
3. Why is a non-trivial bijection `f` useful?
4. Why does the classical algorithm construct `G` while the actual state-preparation circuit uses `G†`?
5. Why does the Malvetti baseline cost `s(ell-1)` in the worst case?
6. What makes a batch structured rather than arbitrary?
7. Why are the residual states one-hot before PUI?
8. Why must `m` be a power of two?
9. What is the difference between restricted and unrestricted PUI?
10. What are the roles of `L` and `g`?
11. Why can unrestricted-PUI side effects be tolerated in the isometry algorithm?
12. What does Algorithm 3's marker ancilla record?
13. Why are purely real coefficients special?
14. Why does QROAM use more ancillas to lower Toffoli count?
15. Why is `O(s^2 n)` not the same thing as `O(s)` Toffoli cost?
16. Which statements are analytical bounds and which are numerical observations?
17. What costs does Table 1 explicitly exclude?
18. What does the paper say about later `O(sqrt(s))` work?

## 7.2 Derivation questions

- [ ] Derive `ell=ceil(log2 s)` from the number of possible labels.
- [ ] Derive the baseline count `s(ell-1)`.
- [ ] Derive Equation (5) from Hamming-weight counting.
- [ ] Derive the full-address unrestricted PUI cost.
- [ ] Derive Equations (6), (7), and (8) at a high level.
- [ ] Derive Equation (1) from Equations (3) and (7).
- [ ] Derive the approximate QROAM optimum.
- [ ] Derive the `2s` leading worst-case behaviour.

## 7.3 Worked-answer panels

<details>
<summary><strong>Answer 1 — What is the paper's central improvement?</strong></summary>

The authors refine the Malvetti et al. sparse-isometry approach. Instead of zeroing the residual one-hot bit of each state with an individual multi-controlled-X, they construct structured batches and apply a partial unary iteration over a consecutive interval of subspace addresses to zero the batch together.
</details>

<details>
<summary><strong>Answer 2 — Why does unrestricted PUI not automatically break correctness?</strong></summary>

It can affect address values above the requested interval, but the isometry algorithm processes intervals in order and tracks the extra bit flips in its classical tableau. The algorithm does not assume those states were untouched. The extra effects are represented by the map `g` and set `L`.
</details>

<details>
<summary><strong>Answer 3 — What is the difference between `2s` and `s`?</strong></summary>

`2s` is the leading behaviour of the analytical worst-case isometry upper bound in the relevant regime. `s` is the empirical limit approached by the paper's random-state numerical benchmarks. It is not a universal guarantee for every sparse support.
</details>

<details>
<summary><strong>Answer 4 — Why does the real-state variant help?</strong></summary>

For real non-zero coefficients, the coefficient phase is only `+1` or `-1`. The authors can encode that sign during the isometry with a restricted-PUI/marker-ancilla construction, removing the separate target phase-encoding stage from dense-state preparation.
</details>

<details>
<summary><strong>Answer 5 — What is the most important resource caveat?</strong></summary>

The paper's resource tables exclude the phase-gradient-state preparation cost and its register from the counts, neglect the phase-gradient rotation's `b` Toffolis as small compared with QRO(A)M, and make assumptions about the peak qubit count. Those choices must be stated when comparing resource totals.
</details>

## 7.4 Oral-defence prompts

Try to answer each prompt in 60–90 seconds, using equations where useful:

1. “Explain the architecture without using the phrase ‘it compresses the state’ until you have defined what is compressed.”
2. “Why is `f` an algorithmic degree of freedom rather than merely a relabeling?”
3. “Explain Figure 5 to me row by row.”
4. “Derive Equation (1), and tell me where every term came from.”
5. “What breaks if you use unrestricted PUI but fail to update the tableau?”
6. “Why does the real-state variant use restricted PUI even though unrestricted PUI is cheaper?”
7. “What assumptions would you challenge if you were estimating this algorithm for a particular fault-tolerant architecture?”
8. “What would you reproduce first, and what would count as a valid correctness test?”

---

# 8. References: short summary and why each is cited

The summaries below are intentionally short. They explain the role each reference plays **as used by this paper**, not a full review of the cited work. The reference numbers match the paper's bibliography on PDF pages 15–17.

## 8.1 Applications and broader state-preparation context

| Ref. | Work (short title) | Why it is relevant here |
|---:|---|---|
| [1] | Morales et al., *Quantum linear system solvers: a survey* (2026) | Supports linear-system solvers as an application area where efficient state preparation matters. |
| [2] | Schuld, Sinayskiy & Petruccione, *Introduction to quantum machine learning* (2015) | Gives the QML application context for state preparation. |
| [3] | Berry et al., *Rapid initial-state preparation for quantum simulation of strongly correlated molecules* (2025) | Supports modern dense-state preparation and phase-gradient rotation techniques used in Section 4. |
| [4] | Fomichev et al., *Initial state preparation for quantum chemistry on quantum computers* (2024) | A major prior state-preparation/isometry approach compared in the introduction and Table 1. |
| [6] | Sun et al., *Asymptotically optimal circuit depth for state preparation and unitary synthesis* (2023) | Represents work optimizing circuit depth rather than the specific Toffoli metric emphasized here. |
| [7] | Zhang, Li & Yuan, *Quantum state preparation with optimal circuit depth* (2022) | Another state-preparation approach cited as broader context and an alternative resource trade-off. |
| [8] | Gui et al., *Spacetime-efficient low-depth state preparation* (2024) | Adds space/time and low-depth context to the state-preparation landscape. |

## 8.2 Structured states and matrix-product states

| Ref. | Work (short title) | Why it is relevant here |
|---:|---|---|
| [9] | Schön et al., *Sequential generation of entangled multiqubit states* (2005) | Background for structured multiqubit-state generation. |
| [10] | Malz et al., *Preparation of matrix product states with log-depth circuits* (2024) | Shows a structured-state preparation family distinct from generic sparse-state support. |
| [11] | Smith et al., *Constant-depth preparation of matrix product states* (2024) | Further context on alternative state formats and circuit-depth objectives. |

These are not central prerequisites for PUI. They situate the paper among methods that exploit structure in quantum states.

## 8.3 Earlier sparse-state-preparation methods

| Ref. | Work (short title) | Why it is relevant here |
|---:|---|---|
| [12] | Mao, Tian & Sun, *Toward optimal circuit size for sparse state preparation* (2024) | One of the iterative sparse-preparation approaches analyzed in the introduction and Appendix D; uses BE-QRAM. |
| [13] | Gleinig & Hoefler, *An efficient algorithm for sparse quantum state preparation* (2021) | Iterative approach whose control count is based on a halving procedure. |
| [14] | Ramacciotti et al., *Simple quantum algorithm to efficiently prepare sparse states* (2024) | Alternative isometry/permutation approach; its Toffoli and ancilla costs are recalculated in Appendix D. |
| [15] | Mozafari, De Micheli & Yang, *Efficient deterministic preparation using decision diagrams* (2022) | Another structured representation for state preparation; cited as related literature. |
| [16] | Li & Luo, *Nearly optimal circuit size for sparse state preparation* (ICALP 2025) | Alternative permutation/transposition-based isometry method; compared under Toffoli and ancilla metrics. |
| [20] | Malvetti, Iten & Colbeck, *Quantum Circuits for Sparse Isometries* (2021) | **The main baseline** refined by this paper. Its worst-case isometry cost is `s(ell-1)` in the paper's analysis. |
| [21] | Tubman et al., *Postponing the orthogonality catastrophe* (2018) | Sparse-state preparation for electronic-structure simulations; used as one iterative-method comparison. |
| [22] | de Veras, da Silva & da Silva, *Double sparse quantum state preparation* (2022) | CVO-QRAM-style control structure related to the Hamming weights of basis strings; analyzed in Appendix D. |
| [28] | Vilmart, Ty & Mang, *Resource-efficient synthesis of sparse quantum states* (2025) | Another related proposal; cited among alternatives that may use fewer gates but require substantial extra qubits. |
| [39] | Li et al., *Optimal T Counts under Sparsity: from QROM to State Preparation and Block Encoding* (2026) | Later work cited in the note that reports sublinear `O(sqrt(s))` scaling using Toffoli/ancilla trade-offs. |
| [40] | Luo & Li, *Sparse Quantum State Preparation with Sublinear T-Count* (2026) | A second later result cited for `O(sqrt(s))` scaling. |

## 8.4 Fault-tolerant resource theory and non-Clifford costs

| Ref. | Work (short title) | Why it is relevant here |
|---:|---|---|
| [5] | Low, Kliuchnikov & Schaeffer, *Trading T gates for dirty qubits* (2024) | Supports phase-gradient methods and Toffoli/T versus dirty-ancilla trade-offs. |
| [17] | Litinski, *Magic State Distillation: Not as Costly as You Think* (2019) | Background for why non-Clifford resources matter in fault-tolerant quantum computation. |
| [18] | Gidney, Shutty & Jones, *Magic state cultivation* (2024) | A magic-state cultivation method cited in the non-Clifford resource discussion. |
| [19] | Beverland et al., *Lower bounds on non-Clifford resources* (2020) | Supports the relationship and resource-theoretic context for T/CCZ/Toffoli costs. |
| [34] | Sahay et al., *Fold-transversal surface code cultivation* (2026) | Cited as a later advance in magic-state cultivation that may change runtime/space estimates. |
| [35] | Ruiz et al., *Unfolded distillation* (2026) | Another advanced magic-state preparation method supporting the conclusion's warning about changing costs. |
| [36] | Huggins, Khattar & Wiebe, *Productionizing Quantum Mass Production* (2025) | Motivates more practical resource/runtime metrics beyond simple Toffoli count. |
| [37] | McArdle et al., *The Fast for the Curious* (2025) | Cited for future models of accelerating fault-tolerant quantum applications. |
| [38] | Huggins et al., *FLASQ cost model* (2025) | A surface-code resource model cited as a more adapted cost metric. |

## 8.5 Circuit primitives, rotations, and data loading

| Ref. | Work (short title) | Why it is relevant here |
|---:|---|---|
| [23] | Babbush et al., *Encoding electronic spectra with linear T complexity* (2018) | Source for AND/unary-iteration circuit primitives used in the PUI construction. |
| [24] | Gidney, *Halving the cost of quantum addition* (2018) | Supports efficient AND/Toffoli constructions and measurement-based uncomputation. |
| [25] | Sanders et al., *Compilation of fault-tolerant quantum heuristics* (2020) | Supports phase-gradient rotation and fault-tolerant circuit compilation techniques. |
| [26] | Ross & Selinger, *Ancilla-free Clifford+T approximation of Z rotations* (2016) | Rotation synthesis alternative discussed for controlled rotations. |
| [27] | Kliuchnikov et al., *Shorter circuits via single-qubit gate approximation* (2023) | Another single-qubit rotation approximation reference. |
| [31] | Litinski & von Oppen, *Lattice surgery with a twist* (2018) | Supports the surface-code/lattice-surgery remark about multi-target CX cost. |
| [32] | Khattar & Gidney, *Conditionally clean ancillae* (2025) | Relevant to unary-iteration constructions and the marker/conditionally-clean ancilla discussion. |
| [33] | Berry et al., *Qubitization of arbitrary-basis quantum chemistry* (2019) | Supports QROAM and sign-correction techniques used in dense-state preparation. |

## 8.6 Software and circuit representation

| Ref. | Work (short title) | Why it is relevant here |
|---:|---|---|
| [29] | Harrigan et al., *Expressing and analyzing quantum algorithms with Qualtran* (2024) | Framework used to express the paper's quantum circuits and calculate resource counts. |
| [30] | Rupprecht & Wölk, *Code and Assets for the paper* (Zenodo, 2026) | The authors' own artifact: Qualtran Bloqs and SIMD-accelerated Rust isometry-finding code. |
| [41] | Desef, *Yquant* (2021) | Circuit-typesetting package used to create the diagrams in the paper. |

---

## Final completion checklist

Before claiming that you understand the paper well enough to discuss it with a research mentor, confirm all of the following:

- [ ] I can explain the whole architecture without notes.
- [ ] I can derive Equation (1) from Equations (3) and (7).
- [ ] I can explain the three unrestricted-PUI recursion cases.
- [ ] I can reconstruct the batch logic in Algorithm 1.
- [ ] I can explain the marker-ancilla logic in Algorithm 3.
- [ ] I can explain QROM versus QROAM and derive the approximate optimal `r`.
- [ ] I can explain why real coefficients permit sign-only phase encoding.
- [ ] I can separate classical preprocessing time from quantum circuit resources.
- [ ] I can state the assumptions and source inconsistencies recorded in Section 5.
- [ ] I can summarize the purpose of references [20], [23], [24], [29], [30], [33], [39], and [40].
- [ ] I can use the glossary precisely rather than substituting similar-sounding terms.

**The standard is not “I recognize every equation.” The standard is “I can re-derive the important equations, explain why the circuit is correct on the target support, and defend the assumptions behind the resource counts.”**

# 9. Glossary

This is the final section by design. Use it as the quick lookup at the end of a study session.

| Term / symbol | Meaning in this paper |
|---|---|
| **Address register** | Register whose computational-basis value selects which target operation a unary-iteration circuit applies. |
| **Address interval `[l,r]`** | Consecutive integer-valued computational-basis labels from `l` through `r`, in the paper's big-endian ordering. |
| **Adjoint `G†`** | The inverse of a unitary circuit `G`; applying the adjoint reverses the circuit's gate order and replaces each gate by its inverse. |
| **AND ladder** | A chain of reversible AND computations into ancillas, used to combine many control conditions for a multi-controlled gate. |
| **Binary-tree traversal** | Recursive splitting of an address interval into left and right halves; the structure used to build unary iteration. |
| **Bra `⟨psi|`** | The conjugate-transpose row-vector associated with ket `|psi⟩`; inner products are written `⟨phi|psi⟩`. |
| **Controlled-controlled-Z (CCZ)** | A diagonal three-qubit gate that applies a minus sign only when all three qubits are 1; locally Clifford-equivalent to Toffoli. |
| **Support / support set** | The set of computational-basis labels whose amplitudes are non-zero; its size is `s`. |
| **Projective measurement** | Measurement in a specified orthonormal basis. The paper measures angle/work registers in the X basis and tracks the induced signs. |
| **`[k]`** | The paper's shorthand for `{0,1,...,k-1}`; it is not the closed interval from 0 through `k`. |
| **`|C_i′⟩_s`** | The first `ell` bits of target basis state `C_i`, held in the subspace register. |
| **`|C_i″⟩_r`** | The remaining `n-ell` bits of `C_i`, held in the non-subspace/residual register. |
| **`U_i`** | The target-register unitary selected when the PUI address register equals `i`. |
| **`R_y(θ)`** | Rotation around the Bloch-sphere Y axis; the paper uses controlled `R_y` rotations to construct amplitude magnitudes. |
| **`R_z(φ)`** | Rotation around the Bloch-sphere Z axis; the paper uses it to encode phase information. |
| **`q` (guide notation)** | Exponent with `m=2^q` in the PUI cost derivation; introduced to avoid overloading the paper's `ell`. |
| **`k` (context-dependent)** | Running compact label in Algorithm 1; in the derivation workbook it may also denote a prefix bit length. Read the local definition. |
| **Basis state** | One computational-basis ket labelled by a bitstring, such as `|0101>`. |
| **Clifford gate** | A gate in the Clifford group; in the paper's resource model these are treated as easier to fault-tolerantly implement than non-Clifford resources. |
| **Controlled rotation** | A rotation applied to a target qubit only when a specified control condition is satisfied. |
| **Fault-tolerant quantum computing** | Quantum computation with error correction and logical operations designed to suppress physical errors. |
| **Global phase** | A common phase factor multiplying the entire state; it does not change measurement probabilities or the physical pure state. |
| **Grover–Rudolph preparation** | A tree of conditional rotations used to prepare a specified amplitude distribution. |
| **Hilbert space** | The vector space of quantum states; an `n`-qubit register has dimension `2^n`. |
| **Normalization** | The condition that the sum of squared amplitude magnitudes is 1. |
| **Surface code** | A quantum error-correction code family; the paper cites lattice-surgery considerations when discussing multi-target CX operations. |
| **Unitary** | A linear operation whose inverse is its adjoint; quantum circuit gates are unitary before measurement. |
| **Amplitude** | Complex coefficient multiplying a computational-basis state. Its squared magnitude is the measurement probability for that basis state. |
| **Ancilla** | Additional workspace qubit used to hold temporary information or enable a circuit construction. |
| **AND ancilla** | Clean target qubit used to store the logical AND of two control bits. |
| **Batch** | A group of up to `m` target states arranged as `|k+j>_s |e_j>_r`, so one PUI can zero their residual one-hot parts. |
| **Big-endian order** | Bit ordering in which the leftmost bit is most significant; the paper orders address intervals this way. |
| **Bijection `f`** | One-to-one map from original support indices `[s]` to a set of `s` compact subspace labels. |
| **CCZ** | Controlled-controlled-Z gate; related to Toffoli through local Clifford/Hadamard transformations. |
| **CNOT / CX** | Controlled-X gate that flips a target bit when its control bit is 1. |
| **CMX** | Multi-target controlled-X: one control bit flips several target bits. |
| **Clean ancilla** | Workspace qubit initialized in a known state, typically `|0>`. |
| **Computational basis** | Orthogonal basis states labelled by bitstrings, such as `|0101>`. |
| **DensePrep** | Dense-state-preparation stage that prepares the coefficient amplitudes in the compact subspace register. |
| **Dirty ancilla** | Workspace qubit whose initial state is not assumed to be `|0>`, but which is used under a construction that accounts for its unknown state. |
| **Hamming weight `h(x)`** | Number of 1s in the binary representation of `x`. |
| **Isometry** | Inner-product-preserving embedding from the compact subspace into the full target space. |
| **Isometry-finding circuit `G`** | Circuit found classically that maps target basis states into compact labels with zero residual register. |
| **Isometry used for preparation `G†`** | Inverse of `G`; maps compact labels into target basis strings. |
| **KET `|psi>`** | Dirac notation for a quantum state vector. |
| **MCX** | Multi-controlled-X: an X target controlled by several qubits. |
| **Magic state** | Special resource state used to implement non-Clifford operations fault-tolerantly. |
| **Measurement-based uncomputation** | A method to erase temporary computed information using measurement and corrections rather than a direct inverse gate sequence. |
| **Non-Clifford gate** | Gate outside the Clifford group; T/CCZ/Toffoli resources are important in fault-tolerant cost estimates. |
| **Non-subspace register** | The last `n-ell` qubits after splitting the target bitstring; the isometry aims to make these all zero. |
| **One-hot state `|e_j>`** | Bitstring with exactly one 1 at residual position `j`, all other residual bits zero. |
| **Phase** | Argument `phi_i` in `c_i=|c_i|e^{i phi_i}`. |
| **Phase-gradient state `|psi>`** | Reusable resource state used with an angle register to implement rotations through controlled addition/subtraction. |
| **PUI** | Partial Unary Iteration: address-dependent target operations for an interval of address values. |
| **QROM** | Reversible quantum read-only-memory lookup construction. |
| **QROAM** | QROM-style lookup with controlled swaps and a tunable ancilla/Toffoli trade-off. |
| **Restricted PUI** | PUI that acts non-trivially only within its requested interval. |
| **Unrestricted PUI** | PUI that may also apply known target operations to some address values above the requested interval. |
| **Residual register** | Another name for the non-subspace register in the isometry construction. |
| **Sign fix** | Correction of a `+1` or `-1` phase induced by measurement or required by a real target coefficient. |
| **Sparse state** | State with only `s` non-zero computational-basis amplitudes, where `s << 2^n`. |
| **Subspace register** | First `ell=ceil(log2 s)` qubits used to encode compact labels. |
| **Tableau** | Classical `s`-row by `n`-column bitstring representation of the target basis states, updated as the circuit is constructed. |
| **T gate** | A non-Clifford single-qubit gate; its fault-tolerant implementation is often resource-intensive. |
| **Toffoli / CCX** | Two-controlled-X gate; target flips iff both control bits are 1. |
| **`ell`** | Compact-register width, `ceil(log2 s)`. |
| **`m`** | Largest power of two no greater than `n-ell`; maximum batch size/one-hot residual width. |
| **`n`** | Number of system qubits in the target state. |
| **`s`** | Number of non-zero target basis states. |
| **`S_addr`** | Full address-register capacity `2^w` in the PUI resource derivation. |
| **`tilde{s}`** | `2^ell`, the smallest power of two at least `s`. |
| **`w`** | Number of address-register qubits in the general PUI discussion; equals `ell` in the isometry application. |
| **`L`** | Set of address values above the requested interval that receive extra operations under unrestricted PUI. |
| **`g`** | Mapping from each extra address in `L` to the intended interval address/operation it receives. |
| **`epsilon`** | Overall approximation-error parameter used in the controlled-rotation cost discussion. |
| **`b`** | Context-dependent: current batch size in Algorithm 1 or number of bits in a rotation-angle register in Section 4. |
| **`r`** | Context-dependent: interval endpoint, residual-register label, or QROAM tunable parameter. |

---

