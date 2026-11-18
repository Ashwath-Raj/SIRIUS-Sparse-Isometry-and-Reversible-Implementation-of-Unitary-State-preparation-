# SIRIUS Ubuntu RTX 3050 benchmark campaign — public evidence

**Run:** `20261117T193151Z`
**Machine:** Ubuntu laptop, AMD Ryzen 5 6600H, NVIDIA RTX 3050 Laptop GPU (6 GiB)
**Python:** 3.12.14
**Source snapshot SHA-256:** `3319fe11187e252a55acc0efd0dfc648ceef63b11d13728a876f6a0e973c831b`

## Paper reproduction track

| Status | Attempts |
|---|---:|
| Completed | 316 |
| Failed | 51 |
| Timed out | 14 |
| Resource-capped / skipped | 88 |
| **Total** | **469** |

### Authors' Figure 10 coverage

| Support size | Unrestricted | Restricted |
|---:|---:|---:|
| 10² | 19/19 selected widths | 19/19 selected widths |
| 10³ | 19/19 | 19/19 |
| 10⁴ | 19/19 | 19/19 |
| 10⁵ | 19/19 | 19/19 |
| 10⁶ | 15/19 | 15/19 |
| 10⁷ | No completed measurements | No completed measurements |

The locally measured authors' Rust counter series is reported separately from the published `out.txt` values and from SIRIUS measurements. Medians and IQRs below are across completed register widths, not independent-seed uncertainty estimates.

| Support size | Unrestricted Toffoli median (IQR) | Restricted Toffoli median (IQR) |
|---:|---:|---:|
| 100 | 108 (30) | 126 (51.5) |
| 1,000 | 1,060 (464.5) | 1,251 (1,459) |
| 10,000 | 11,538 (8,391) | 15,000 (24,348) |
| 100,000 | 125,939 (125,060) | 168,750 (314,862) |
| 1,000,000 | 1,798,203 (1,553,986), 15 widths | 2,875,338 (3,596,984.5), 15 widths |
| 10,000,000 | Not run | Not run |

## Matched SIRIUS–Malvetti comparison

At n=9, s=100, five independent seeds were used with a warm-up and three timing repetitions per method. SIRIUS median runtime was **289.889 ms**; Malvetti median runtime was **100.483 ms**. SIRIUS median paper-accounted Toffoli count was **134** (IQR 1; bootstrap interval 131–135). SIRIUS coherent/emitted Toffoli count was **267** (IQR 1). Malvetti did not expose a directly comparable paper-accounted Toffoli count. Timing scopes differ from the authors' Rust Figure 10 measurement interval; do not compare them as if they were the same metric.

## Symmetry-structured support extension

| Status | Raw attempts |
|---|---:|
| Completed | 204 |
| Timed out | 12 |
| **Total** | **216** |

The raw records contain 60 duplicate logical-job groups (54 completed and 6 timed-out groups). They represent 156 logical jobs. Raw attempts are retained unchanged; deduplicated analytics use one representative per logical job. The random-versus-fixed-weight analysis contains 36 matched contrast records, grouped into 24 unique n/s/seed/algorithm tuples. There are only three independent seeds per stratum; no confidence or significance claim is warranted. Random and fixed-weight supports intentionally differ, so these are matched geometry comparisons, not identical mathematical states.

The ordering experiment contains 36 lexicographic-versus-shuffled comparisons across 18 instances; the canonical mathematical states and basis-attached coefficients/signs match while ordered-input hashes differ.

## GPU basis-row lane

The final campaign includes one 8-row CuPy basis-row parity attempt: kernel 3.661 ms, host-to-device 0.084 ms, device-to-host 0.033 ms, total lane wall time 3.804 ms. An earlier bounded RTX 3050 pilot recorded 60/60 eligible GPU basis-row parity stages passing. This is `uint64` reversible basis-row simulation, **not** complex-amplitude statevector simulation and not quantum-hardware execution.

## Validation and archives

- Python 3.12 regression suite: 186 tests passed.
- Raw attempt SHA-256 (paper): `e186bf63e2c4d1cc0d2389a973cc82c8c03a8f8c973d305ca7a84bd391fa0601`
- Raw attempt SHA-256 (symmetry): `bab329ddafbbd05c39e9e77732abf6fac279f1e1f4c671343110457632936c12`
- Original campaign ZIP SHA-256: `35c88c1412e125a50a793b8eac7dcaf47caac0577f7e1e9d16e2d2c0c59f8344`
- Data-quality closure ZIP SHA-256: `5dee36420feec0fba0dcc64097cf062ddb19aa63343784701e8a90f8a3c0daeb`

The [campaign release](https://github.com/Ashwath-Raj/SIRIUS-Sparse-Isometry-and-Reversible-Implementation-of-Unitary-State-preparation-/releases/tag/sirius-ubuntu-rtx3050-campaign-20261117) contains both campaign archives and their checksum sidecars. The closure archive includes the audit tables, pair validation, plots, logs, source snapshot and original archive.

## Scope and limitations

This is a **partial Figure 10 reproduction**, not a complete reproduction of the paper. No support-size 10⁷ measurements completed; the 10⁶ points are incomplete. The matched SIRIUS–Malvetti scaling study is small. The symmetry extension is exploratory. The GPU lane does not simulate complex amplitudes. No QPU execution is included. The Equation (3) wording/resource discrepancy remains unresolved, and authors' mapping/counter checks do not establish primitive gate-by-gate equivalence.
