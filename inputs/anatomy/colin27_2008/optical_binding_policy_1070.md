# Colin27 native-label optical binding policy at 1070 nm

This policy governs how optical-property evidence may bind to `colin27_2008_native12_1mm_v3`. It does not alter the segmentation. The official release supplies names, not histological definitions, for the ambiguous labels, so unsupported identity claims remain forbidden.

## Source-defined labels and operational decisions

| ID | Official source name | What the source establishes | Permitted optical treatment |
|---:|---|---|---|
| 4 | Fat | A distinct native class named `Fat` | Preserve separately. A shared adipose proxy with ID 9 is allowed only as a declared sensitivity assumption; it does not establish equivalence. |
| 5 | Muscles | A distinct native class named `Muscles` | Bind skeletal-muscle evidence. Animal or bulk human measurements must retain their species and tissue-mixture qualifications. |
| 6 | Skin and Muscles | A composite class; no mixing fraction is supplied | Preserve as one label. Use discrete pure-skin, pure-muscle, and bulk-forehead proxy cases. Do not construct a weighted effective medium unless a composition map or prespecified fraction is supplied. |
| 9 | Fat 2 | A second native class named `Fat 2`; its distinction from ID 4 is not defined | Preserve separately. Test the same-adipose binding only as an explicit shared-proxy case. |
| 11 | Marrow | A separate native class named `Marrow` | Retain separately from skull. Human tibial marrow is a site/state sensitivity, not a cranial nominal value. A skull-like surrogate is a separate sensitivity, never a relabeling. |
| 12 | Vessels | A generic vessel class; lumen, wall, arterial, and venous identities are not supplied | Operationally test effective intravascular whole-blood cases because no separate wall label exists. Declare haematocrit and oxygenation. This is a model binding, not a claim that every vessel voxel is pure lumen. |

The source definitions were checked in `source/README.txt` and `source/label_definitions.itksnap`; neither file supplies additional semantics for IDs 4, 6, 9, 11, or 12.

## Scenario rules

1. Do not split, merge, or relabel the accepted native anatomy to resolve an optical-data gap.
2. Bind a measurement only to the tissue identity it actually measured. Species, anatomical site, in-vivo/ex-vivo state, temperature, and mixture depth remain part of the binding.
3. For ID 6, prefer discrete proxy scenarios over an invented mixture. A mixture model requires a documented equation and a defensible composition fraction.
4. For IDs 4 and 9, a shared numerical row is permitted only when both bindings point to the same evidence record and the scenario says `shared_adipose_proxy_assumption`.
5. For ID 12, physiological-haematocrit and oxygenation cases take precedence over diluted-blood curves for realistic sensitivity analysis, but secondary compilations do not become primary measurements.
6. Boundary air may use `(mua=0, mus=0, g=0, n=1)` only when the complete scenario is frozen.
7. The benchmark-only Yue five-tissue collapse in `label_policy.md` remains separate and may not be substituted for this policy.

## Provisional implementation

`inputs/optical_properties/provisional_1070_v1/` implements these rules as one assumption-explicit central table and one-at-a-time sensitivity variants. The implementation is runnable for research screening but is marked `scientific_status: provisional` and `production_eligible: false`. It does not resolve or overwrite the production `TBD` gate.
