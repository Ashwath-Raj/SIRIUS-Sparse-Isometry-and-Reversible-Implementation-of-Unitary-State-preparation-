# Phase 3 acceptance checklist

- [ ] Model validation: positive `n`, nonempty distinct support, exact widths, finite normalized coefficients, signs in `{+1,-1}`.
- [ ] Big-endian convention: `100` maps to integer 4 for width 3.
- [ ] Integer-safe `ell`, padded support size and residual width.
- [ ] `s=1` handled as a special case; invalid batch-width derivation raises.
- [ ] Every primitive gate truth table and inverse round-trip passes.
- [ ] PUI remains symbolic with explicit kind, interval, `L`, and `g`; no premature simulator claim.
- [ ] Tableau preserves stable row IDs, original strings and independent phase signs.
- [ ] All support generators produce distinct strings deterministically.
- [ ] Resource histogram does not count CX/CMX as Toffoli; decomposition count is unknown until a decomposition exists.
- [ ] CuPy CUDA device smoke and CPU/GPU parity pass on RTX 3050; if environment lacks CuPy/CUDA, record as blocked rather than claiming parity.
- [ ] Commit reviewed Phase 3 code and test evidence locally; do not push.
