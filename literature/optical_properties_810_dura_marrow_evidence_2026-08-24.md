# 810-nm dura and cranial-marrow decision record

## Dura

The refined provisional dura row uses the exact 810-nm numerical spectrum released by Shapey et al. (2022):

| Quantity | Value | Source |
|---|---:|---|
| revised `mua` | 0.05682 mm^-1 | Table S1, sheet `Dura`, cell `D43` |
| model-fitted `musp` | 3.5592848441 mm^-1 | Table S1, sheet `Dura`, cell `E43` |
| `g` | 0.85 | Fixed IAD input in the paper, not measured |
| `mus` | 23.7285656270 mm^-1 | `musp/(1-g)` |
| `n` | 1.40 | Fixed IAD input in the paper, not measured |

The source is direct ex vivo human dura but not an in-vivo population estimate. Healthy tissues came from one post-mortem subject; the paper reports that death occurred six days before examination. Specimens were hand-cut to approximately 2 mm. The fixed `g` and `n` values are inversion assumptions. The prior Cassano skull-like dura row is retained as a one-at-a-time sensitivity, not as the primary row.

Eggert and Blazek (1987) provides qualitative support that dura is distinct from skull and comparatively transmissive near 810 nm, but its relative reflection/absorption/scattering presentation does not supply a complete MCX-ready coefficient row.

## Marrow

The refined provisional marrow row uses exact 810-nm data from Kothuri et al. (2025), Zenodo record 14170681. The archive SHA-256 is `72660c70a8e9b957521a3b92adc69dfe45212d029a88d69f58e87c867f456f1a`, matching the archive identity previously recorded in the 1070-nm ledger.

| Endpoint | `mua` (mm^-1) | `musp` (mm^-1) | Role |
|---|---:|---:|---|
| frozen bone marrow | 0.010 | 1.1843333333 | refined provisional primary |
| trabecular bone | 0.006 | 0.742 | porous/diploic lower-scattering sensitivity |
| Cassano skull-like proxy | 0.011 | 1.92 | previous higher-scattering sensitivity |

The Kothuri coefficients are arithmetic means of three released technical iterations in cm^-1, divided by 10. The primary row retains the project's `g=0.89` and `n=1.37` assumptions because Kothuri reports `musp` rather than a separate phase-function anisotropy or refractive index.

This is the best direct human-marrow dataset currently available in the workspace, but the mapping remains weak-to-moderate confidence: it is frozen tibial marrow from one 89-year-old female donor, kept on ice packs during transmission measurements, with notable boundary effects acknowledged by the authors. It is not living cranial diploic marrow.

## Simulation policy

- The refined primary scenario changes both dura and marrow relative to the v1 810-nm table.
- Marrow sensitivities change label 11 only after applying the refined primary overlay.
- The dura sensitivity changes label 10 only after applying the refined primary overlay.
- Intracranial first-entry tallies cannot test dura optics because dura itself is part of that tally surface. Dura is therefore evaluated with brain-parenchyma and white-matter first-entry tallies.
- All scenarios remain provisional and retain the Yue-derived 277-emitter spatial surrogate.
