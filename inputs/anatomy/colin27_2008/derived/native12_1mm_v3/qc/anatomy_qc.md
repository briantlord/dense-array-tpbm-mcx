# Colin27 native-label 1-mm anatomy QC

- Anatomy ID: `colin27_2008_native12_1mm_v3`
- Automated status: **passed**
- Visual review: **accepted**
- Output geometry: `[181, 217, 181]` at 1-mm isotropic, RAS
- Label output SHA-256: `f37076f548dcfcb3ac0728982a5f766b2632398cbae01659c0b715b8aa7b5d6f`
- Reference T1 SHA-256: `98568e9fbeaa2f065d7d48add0cbde0d71960626326baa1263527988f97c13e9`
- Tied block-mode voxels: `269754` (3.7945%)
- Enclosed background/air voxels: `5753`; these include anatomical air cavities and require visual interpretation, not automatic filling.
- Removed disconnected non-head voxels: `105`; transitions by original label are recorded in `anatomy_qc.json`.
- Removed outside the 15-mm cranial soft-tissue envelope: `141210` voxels; transitions by original label are recorded in `anatomy_qc.json`.

## Tissue volumes

| Label | Tissue | Native mm3 | Derived mm3 | Relative change |
|---:|---|---:|---:|---:|
| 0 | background_air | 3160882.0 | 3286799.0 | 3.984% |
| 1 | cerebrospinal_fluid | 314727.2 | 338002.0 | 7.395% |
| 2 | gray_matter | 993734.5 | 1001274.0 | 0.759% |
| 3 | white_matter | 660533.5 | 640621.0 | -3.015% |
| 4 | fat | 137909.5 | 140570.0 | 1.929% |
| 5 | muscles | 666694.6 | 668388.0 | 0.254% |
| 6 | skin_and_muscles | 450175.8 | 383231.0 | -14.871% |
| 7 | skull | 360600.2 | 355103.0 | -1.524% |
| 9 | fat_2 | 227608.8 | 170283.0 | -25.186% |
| 10 | dura | 10294.5 | 8868.0 | -13.857% |
| 11 | marrow | 81071.9 | 74917.0 | -7.592% |
| 12 | vessels | 44904.5 | 41081.0 | -8.515% |

## Interpretation boundary

Automated structural checks do not validate optical properties, source registration, cortical ROIs, or clinical dosimetry. The native labels were intentionally not merged. A five-tissue benchmark map, if required, must be a separate versioned derivative.
