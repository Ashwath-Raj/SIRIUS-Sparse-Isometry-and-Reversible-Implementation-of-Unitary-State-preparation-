# Paper Interpretation and Discrepancies

Sources inspected: the local published PDF `reference/sources/q-2026-09-10-2208.pdf`, its searchable text, the repository's detailed study guide, and the verified authors' artifact archive (`reference/authors-artifact/official-artifact.zip`, MD5 `c58634ba415b4e3fb729648460f32ad7`). The artifact's figure source is also inspected where relevant.

## Equation (3): two-Toffoli arithmetic mismatch — `UNRESOLVED`

**Location and printed statements.** Paper page 6 (PDF page index 5), the prose immediately before Equation (3), states that the final Malvetti-style correction costs `ceil(log2(s)) + 1` Toffolis. Equation (3) prints the total as `s - ceil(s/m) + log2(tilde{s}/2)`, with `tilde{s} = 2^ceil(log2(s))`.

**Independent calculation.** Let `ell = ceil(log2(s))`. The prose term is `ell + 1`. The displayed logarithm is `log2(2^ell / 2) = ell - 1`. The two differ by exactly two Toffolis. The displayed Equation (3) is also carried into the paper's later upper-bound discussion; the local master guide records the same arithmetic.

**Authors' implementation.** `src/lib.rs` in the official source counts the emitted `BatchCreationData` and `BatchZeroingData` operations. Its `BatchZeroingData::num_toffolis` uses `changing_size - 2` when `fixed_len == 0`, which underflows `usize` for a zero-operation bucket. The official binary returns `18446744073709551614` for observed small fixtures in this environment. This is an implementation defect in those cases, not evidence resolving which paper expression was intended.

**SIRIUS interpretation.** The implementation keeps paper-accounted, coherent, and emitted counts separate. It does not patch Equation (3) to match observed artifact output. The adapter preserves the raw reference counter and labels values above `sys.maxsize` `suspected_usize_underflow`; it does not publish those wrapped values as costs.

**Selected interpretation.** Keep the printed Equation (3) and the prose statement distinct. Do not claim algebraic equivalence. `UNRESOLVED`: the PDF and the buggy counter do not establish whether the prose's `+1` or the printed `/2` is the typographical error. The matched small smoke uses an artifact case whose counter is finite; it does not resolve the discrepancy.

## Figure 9 restricted/unrestricted labels — likely caption inversion

**Location and original caption.** Paper page 13 (PDF page index 12), Figure 9 caption says “Algorithm 1 (restr.)” and “Algorithm 3 (unrest.)”.

**Derivation / cross-checks.** Section 4's discussion around page 13 says Algorithm 3 replaces unrestricted PUI with restricted PUI and adds a marker ancilla. The Algorithm 3 pseudocode and the paper's stated reason for the marker agree. In the official Figure 9 plotting source, `isometry_modes = ["unrestricted", "restricted"]`; the loop zips `[False, True]` with those labels and passes the boolean into `SparseStatePreparation`. The labels therefore identify the first plotted isometry as unrestricted and the second as restricted, consistent with the prose's algorithm distinction.

**SIRIUS interpretation.** Treat the caption's Algorithm 1/3 parentheticals as swapped: Algorithm 1 is unrestricted; Algorithm 3 is restricted and sign/marker aware. The authors' plot-generation source supports this interpretation. This resolves the labeling interpretation with high confidence; the published caption remains a source typo and is not silently rewritten in SIRIUS.
