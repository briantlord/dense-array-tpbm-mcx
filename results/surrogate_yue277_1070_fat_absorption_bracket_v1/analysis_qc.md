# 1070 nm fat-absorption sensitivity result

Status: **provisional**. The anatomy and 277-emitter layout are the existing Yue-derived
spatial surrogate, not a target-helmet geometry or a measured dose model.

## Outcome

The existing fat absorption coefficient (`mua = 0.103 mm^-1`) materially suppresses
modeled brain delivery. With constant total launched energy and all other optical
properties held fixed, the recommended effective-adipose case (`mua = 0.010 mm^-1`)
raises gray-plus-white-matter absorption from **0.4458%** to **1.2142%** of launched
energy, a **2.72x** result. The exact lipid-data case (`0.005065 mm^-1`) gives
**1.3222%**, while the conservative high case (`0.030 mm^-1`) gives **0.9064%**.

| Fat `mua` (mm^-1) | Interpretation | Fat absorbed | Brain absorbed | Brain vs. 0.103 |
|---:|---|---:|---:|---:|
| 0.103 | Existing extreme-high baseline | 23.9334% | 0.4458% | 1.00x |
| 0.005065 | Exact Van Veen lipid value at 1070 nm | 2.9140% | 1.3222% | 2.97x |
| 0.010 | Recommended effective adipose | 5.3366% | 1.2142% | 2.72x |
| 0.030 | Conservative high effective adipose | 12.4350% | 0.9064% | 2.03x |

## Recommended-case tissue budget

These percentages are fractions of total launched energy. Labels 4 and 9 are the two
fat compartments; “brain” is gray matter plus white matter.

| Tissue | Absorbed energy |
|---|---:|
| CSF | 0.2758% |
| Gray matter | 1.1776% |
| White matter | 0.0367% |
| Fat (label 4) | 2.3918% |
| Muscle | 32.9694% |
| Skin and muscle | 13.2002% |
| Skull | 3.1200% |
| Fat (label 9) | 2.9448% |
| Dura | 0.1323% |
| Marrow | 0.2725% |
| Vessels | 0.2988% |
| **All modeled tissue** | **56.8198%** |
| **Escaped or unabsorbed** | **43.1802%** |

## Verification and limits

- Three independent 277-emitter bases were run at 100 million photons per emitter
  (27.7 billion histories per scenario) on the NVIDIA GeForce RTX 3080 Ti.
- All 831 manifests are complete, and every native JNIfTI field checksum was verified
  while streaming the constant-total aggregate.
- Only fat `mua` changed in labels 4 and 9; fat scattering and every other tissue
  property were held fixed. This isolates absorption-coefficient sensitivity but does
  not establish that the unchanged scattering is physiologically correct.
- One replicate was used per emitter, so no formal Monte Carlo confidence interval is
  reported. The observed two- to three-fold brain change is much larger than expected
  photon noise at this count, but biological/anatomical parameter uncertainty remains
  the dominant limitation.
- The muscle coefficients remain provisional. The increased muscle absorption in the
  low-fat cases is physically consistent with more light surviving the fat layers and
  reaching muscle; it is not evidence that the muscle coefficient itself is validated.

Primary numerical artifacts are `comparison.csv`, `tissue_absorption_by_case.csv`, and
`result.json` in this directory. Aggregate arrays are retained locally but excluded from
Git by the project artifact policy.
