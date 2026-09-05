# Yue-derived 1070-nm surrogate regional convergence

This is a five-region convergence study for a provisional spatial surrogate, not target-helmet validation.

- Candidate full-basis count: `10,000,000` photons per emitter.
- Candidate passes every frozen regional transition check: `False`.
- Estimated 277-source runtime at the candidate count: `30.9` minutes on this M4 Pro.

| Region | Integral CV max | Integral change max | Profile CV median | Profile change median | Pass |
|---|---:|---:|---:|---:|:---:|
| anterior | 0.866% | 0.086% | 5.720% | 6.683% | PASS |
| left_temporal | 0.891% | 2.570% | 8.216% | 5.311% | PASS |
| posterior | 0.527% | 0.565% | 13.927% | 18.890% | FAIL |
| right_temporal | 0.403% | 0.449% | 7.612% | 14.759% | FAIL |
| superior | 0.522% | 1.745% | 6.498% | 23.662% | FAIL |

Do not prepare or execute the full basis yet; extend the regional protocol to 10^8 photons without changing the current results.
