# Provisional 1070-nm representative pilot QC

Software and placement QC for 100,000-photon provisional runs. Values are not convergence-qualified, calibrated device dose, or efficacy.

| Emitter | Absorbed energy (%) | Positive voxels | GM sum | WM sum | Max distance from source (mm) | Checks |
|---|---:|---:|---:|---:|---:|---|
| P1070_SUPERIOR | 64.83802 | 592,879 | 0.0135054 | 0.00336791 | 0.974 | PASS |
| P1070_ANTERIOR | 68.71448 | 433,513 | 0.0778247 | 0.00300576 | 1.345 | PASS |
| P1070_POSTERIOR | 55.41327 | 417,769 | 0.126793 | 0.0121695 | 1.248 | PASS |
| P1070_LEFT_TEMPORAL | 48.97187 | 393,898 | 0.0299317 | 0.000539498 | 0.957 | PASS |
| P1070_RIGHT_TEMPORAL | 69.10593 | 492,383 | 0.133882 | 0.00172028 | 1.356 | PASS |

The v1 superior attempt is retained as a failed immutable run because the restricted process exposed no OpenCL device. The complete v2 set ran with direct M4 Pro OpenCL access.
