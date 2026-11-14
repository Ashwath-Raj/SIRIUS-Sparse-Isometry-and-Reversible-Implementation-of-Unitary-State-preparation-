# Phase 5 Acceptance Checklist

- [ ] PUI intervals are inclusive and validated against address width.
- [ ] Restricted PUI applies only the requested interval operations.
- [ ] Unrestricted PUI leaves addresses below `l` untouched and computes exact extra-address map `g:L->[l,r]` above `r`.
- [ ] Figure 7 `[0,3]` and `[4,6]` examples match the paper's extra-address behaviour.
- [ ] The address register is unchanged by the PUI operation.
- [ ] Every basis input matches the PUI address-to-unitary map.
- [ ] Inverse PUI restores every tested basis state.
- [ ] Coherent MCX ladders handle positive and negative controls correctly.
- [ ] Coherent MCX ladders return every clean ancilla to zero.
- [ ] Paper measurement-based cleanup accounting is distinct from coherent unitary uncompute.
- [ ] Repeated-interval bounds implement the paper's Equations 7 and 8.
- [ ] Full test suite passes on the local project environment, including CUDA parity.
- [ ] No official reference source or lockfile was modified.
- [ ] The MCX-per-address oracle is not represented as the optimized shared-prefix PUI circuit.
