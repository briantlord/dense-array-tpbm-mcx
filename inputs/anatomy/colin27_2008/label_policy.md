# Colin27 label policy

## Primary 1070-nm anatomy

The primary 1-mm anatomy retains every native discrete tissue identity from the official Colin27 2008 release:

| ID | Tissue | Primary disposition |
|---:|---|---|
| 0 | Background/air | Retain as non-scattering exterior/cavity medium; do not fill anatomical air cavities automatically. |
| 1 | Cerebrospinal fluid | Retain. |
| 2 | Gray matter | Retain; primary analysis tissue. |
| 3 | White matter | Retain. |
| 4 | Fat | Retain pending optical-property binding. |
| 5 | Muscles | Retain pending optical-property binding. |
| 6 | Skin and muscles | Retain as the source atlas defines it; do not relabel as pure skin. |
| 7 | Skull | Retain. |
| 9 | Fat 2 | Retain separately until its source definition and optical treatment are resolved. |
| 10 | Dura | Retain. |
| 11 | Marrow | Retain; do not silently merge with compact skull. |
| 12 | Vessels | Retain. |

No native tissue labels are merged in `colin27_2008_native12_1mm_v3`. Visual QC of earlier derivatives identified a connected soft-tissue wraparound/field-of-view artifact superior to the cranial tissues. Version 3 retains all protected cranial labels (CSF, GM, WM, skull, dura, marrow, and vessels), retains soft tissues within 15 mm of those protected tissues, and reassigns more distant soft tissue to background. Remaining nonzero components disconnected from the largest head component are also reassigned to background. Per-label transition counts are recorded. This removes field-of-view artifacts without claiming tissue equivalence and prevents the anatomy step from hiding unsupported optical equivalences.

## Five-tissue benchmark derivative

The Yue and Humayun benchmark used scalp, skull, CSF, gray matter, and white matter, but their 1-mm segmentation was generated with SPM12 and is not identical to the official 2008 discrete phantom. A five-tissue approximation may therefore be generated only as a separately versioned `benchmark` artifact after its spatial reassignment policy is frozen.

A global lookup-table merge is not accepted because vessels and soft tissues occur in both extracranial and intracranial locations. Any benchmark collapse must use an explicit spatial reassignment method, report voxel transitions, and never be substituted for the primary native-label anatomy.
