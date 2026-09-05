# Targeted penetration tallies

## Result

- **2.5811%** of normalized in-model launched energy first reaches the intracranial compartment.
- **21.460%** of energy that reaches skull or marrow subsequently reaches the intracranial compartment.
- **1.8597%** of launched energy first reaches gray or white matter.
- **0.1766%** of launched energy first reaches white matter.

| Stage | Launched energy (%) | Retained from preceding stage (%) | Replicate SD (percentage points) |
|---|---:|---:|---:|
| entered_head_tissue | 99.999996 | 99.999996 | 0.000000 |
| reached_skull_complex | 12.027815 | 12.027815 | 0.001302 |
| reached_intracranial_compartment | 2.581131 | 21.459684 | 0.000329 |
| reached_brain_parenchyma | 1.859730 | 72.050966 | 0.000487 |
| reached_white_matter | 0.176631 | 9.497685 | 0.000122 |


## Interpretation boundary

The denominator is energy launched by the 277 sources inside this computational surrogate. At their nominal voxel coordinates, 276 of 277 sources are already located in superficial tissue labels. Therefore this result does **not** include external emitter-to-scalp coupling or a measured Fresnel entry loss.

Each target tissue set was replaced by a nearly perfect absorber with the original tissue refractive index. Target deposition measures first-entry photon weight. Three independent 277,000,000-photon aggregate runs were used per stage.

The intracranial-with-skull-blocked audit measured only 0.00003741% of launched energy reaching intracranial labels before skull/marrow labels (0.00145% of intracranial-reaching energy), so the skull-conditional ratio is not materially driven by segmentation bypasses.

Changing absorber μa from 100 to 1000 mm⁻¹ changed the low-photon intracranial tally by 0.0444% relative.

Scientific status: provisional_yue_derived_spatial_surrogate_not_target_helmet_not_measured_dose_not_biological_efficacy.
