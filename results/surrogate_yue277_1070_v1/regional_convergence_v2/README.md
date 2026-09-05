# Yue-derived 1070-nm surrogate regional convergence

This is a five-region convergence study for a provisional spatial surrogate, not target-helmet validation.

- Candidate full-basis count: `100,000,000` photons per emitter.
- Candidate passes every frozen regional transition check: `True`.
- Estimated 277-source runtime at the candidate count: `242.1` minutes on this M4 Pro.

| Region | Integral CV max | Integral change max | Profile CV median | Profile change median | Pass |
|---|---:|---:|---:|---:|:---:|
| anterior | 0.208% | 0.320% | 1.570% | 2.220% | PASS |
| left_temporal | 0.299% | 0.837% | 3.057% | 4.246% | PASS |
| posterior | 0.164% | 0.076% | 5.384% | 7.685% | PASS |
| right_temporal | 0.115% | 0.049% | 1.919% | 3.896% | PASS |
| superior | 0.193% | 0.091% | 2.786% | 1.151% | PASS |

The candidate plan may now be prepared, but executing all 277 fields remains a separate explicit compute step.
