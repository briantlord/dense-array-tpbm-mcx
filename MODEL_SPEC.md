# Model Specification

## 1. Model identity and invariants

- **Target wavelength:** 1070 nm, monochromatic approximation for version 1.
- **Primary orchestration:** Python 3.13 with immutable JSON configurations, schemas, manifests, tests, and analysis code.
- **Simulation backends:** MCX-CL/PMCXCL on Apple Silicon and CUDA MCX/PMCX on NVIDIA systems. Backend identity and version are mandatory manifest fields. MATLAB/MCXLABCL may be used only as an independent verification path, not as a production dependency.
- **Transport regime:** linear, incoherent radiative transport. Per-emitter fluence/energy fields may be weighted and added. This is not coherent field interference.
- **Reference source normalization:** simulate each source independently at a declared unit launched energy (recommended for steady-state MCX output), then scale to measured optical power and exposure time in post-processing.
- **Primary anatomy:** one versioned adult head atlas at approximately 1-mm isotropic resolution. The exact atlas is `TBD` until licensing and benchmark compatibility are checked.
- **Primary analysis tissue:** cortical gray matter; whole-volume and other tissue outputs are secondary.

No production configuration is valid if a required field below is `TBD`.

## 2. Coordinate and unit conventions

Use SI-derived radiometric units in reports, while respecting MCX's documented input/output conventions internally.

| Quantity | Canonical stored unit | Notes |
|---|---|---|
| Position, voxel size, standoff | mm | Convert to MCX grid coordinates only at the engine boundary. |
| Wavelength | nm | Exact modeled wavelength recorded per scenario. |
| Absorption coefficient, `mua` | mm^-1 | Never mix with cm^-1 without explicit conversion. |
| Scattering coefficient, `mus` | mm^-1 | Distinguish from reduced scattering `musp`. |
| Reduced scattering, `musp` | mm^-1 | `musp = mus * (1 - g)`. |
| Anisotropy | dimensionless | `0 <= g < 1`. |
| Refractive index | dimensionless | `n >= 1` unless a documented model requires otherwise. |
| Optical power | W | Radiometric output, not electrical input power. |
| Irradiance / fluence rate | W mm^-2 internally or W cm^-2 for reports | Conversion must be tested. |
| Radiant exposure / fluence | J mm^-2 internally or J cm^-2 for reports | State whether the MCX output is normalized per launched joule. |
| Absorbed energy density | J mm^-3 internally or J cm^-3 for reports | Derived consistently from absorption and fluence. |

Coordinate frames must be named, right-handed unless documented otherwise, and expressed with 4x4 homogeneous transforms. Store transforms as `T_target_from_source`; do not use an ambiguous name such as `transform.json`.

## 3. Head anatomy

### Required tissues

At minimum:

1. background/air;
2. scalp/skin;
3. skull, with compact and spongy bone separated if the atlas and evidence support it;
4. CSF;
5. gray matter;
6. white matter.

Optional later labels include blood, eyes, muscle, dura, cerebellar tissues, and ventricular CSF. Added anatomical detail must not silently change the benchmark definition.

### Required anatomy metadata

- source dataset, version, URL/DOI, access date, and license;
- subject/template identity and age category;
- native voxel size, resampling method, and final voxel size;
- label definitions and any label merging;
- affine and orientation convention;
- preprocessing script/version;
- checksums for source and derived volumes;
- volume, slice, and surface renders used for visual QC;
- cortical mask construction and erosion/dilation operations, if any.

### Anatomy QC

- no unassigned internal holes or disconnected tissue islands without explanation;
- skull and scalp form anatomically plausible enclosing layers;
- CSF is not inadvertently collapsed by resampling;
- source rays begin outside or at the intended boundary and point inward;
- all intended cortical ROIs are mapped into gray-matter voxels;
- label counts and physical volumes are reported.

## 4. Optical-property provenance at 1070 nm

### Required table

Create a machine-readable table with one row per tissue and scenario:

| Field | Requirement |
|---|---|
| `scenario_id` | e.g. `nominal_1070_v1`, `low_absorption_v1` |
| `tissue_id`, `tissue_name` | Exact match to anatomy labels |
| `wavelength_nm` | 1070 for the primary model |
| `mua_mm-1` | Value or `TBD` |
| `mus_mm-1` | Value or `TBD`; if derived, retain the source `musp` too |
| `g` | Value or `TBD` |
| `n` | Value or `TBD` |
| `source_kind` | direct measurement, spectral model, interpolation, extrapolation, assumption |
| `citation` | DOI/URL/full citation |
| `source_wavelengths_nm` | Wavelengths actually supporting the value/model |
| `conversion` | Original units and exact equation/code used |
| `tissue_definition` | Species, state, temperature, ex vivo/in vivo, anatomical definition |
| `uncertainty` | reported interval or planned sensitivity range |
| `review_status` | unresolved, single-reviewed, double-checked, frozen |
| `notes` | Limitations and compatibility issues |

### Rules

- Do not invent numerical 1070-nm parameters.
- Prefer direct wavelength-specific human data when defensible, but do not merge incompatible tissue definitions merely because they are human.
- A 1064-nm value is not a measured 1070-nm value. If used through a spectral model or interpolation, preserve the original data and label the transformation.
- Never derive `mus` from `musp` without recording `g`: `mus = musp / (1 - g)`.
- Refractive-index choices need provenance even when their sensitivity is expected to be smaller.
- Tissue-water absorption near this wavelength and spectral slopes require explicit review; intuition about a generic optical window is not a parameter source.
- The nominal table is frozen only after a second-person or independent-source check of quantity definition, wavelength, units, and tissue match.

Use an all-`TBD` production template initially. A separate `synthetic_test_only` table may contain arbitrary plausible numbers solely to test code paths; its filename and manifests must prevent confusion with scientific runs.

## 5. Emitter geometry schema

Use CSV or Parquet for the table and JSON Schema for validation. One row represents one independently weighted emitting element.

| Field | Type/unit | Required | Meaning |
|---|---|---:|---|
| `helmet_model` | string | yes | Hardware/version identifier |
| `geometry_version` | string | yes | Immutable geometry revision |
| `emitter_id` | string | yes | Stable unique ID |
| `group_id` | string | yes | Hardware zone/string/module |
| `enabled` | boolean | yes | Included in this configuration |
| `wavelength_peak_nm` | float | yes | Measured or documented peak |
| `spectral_fwhm_nm` | float | recommended | Required for later spectral model |
| `x_mm,y_mm,z_mm` | float | yes | Emitter center in helmet frame |
| `nx,ny,nz` | float | yes | Unit optical-axis vector in helmet frame |
| `source_type` | enum | yes | MCX source model, e.g. disk, Gaussian, pattern |
| `emitting_area_mm2` | float | yes | Radiating aperture/footprint |
| `beam_parameter_kind` | enum | yes | FWHM angle, half-power angle, fitted profile, etc. |
| `beam_parameter_value` | float/path | yes | Value or calibrated angular-profile file |
| `optical_power_cw_W` | float | yes | Measured radiometric CW-equivalent output |
| `power_uncertainty_W` | float | recommended | Calibration uncertainty |
| `duty_cycle` | 0–1 | yes | For the simulated program |
| `pulse_frequency_Hz` | float | conditional | Descriptive unless time-resolved transport is needed |
| `phase_group` | string | recommended | Simultaneously active group for temporal programs |
| `standoff_mm` | float | yes | Aperture-to-scalp distance after registration |
| `coupling_factor` | 0–1 | yes | Scenario-specific pre-tissue transmission; 1 for ideal reference |
| `calibration_id` | string | yes | Link to spectrum/power/beam record |
| `provenance` | string/path | yes | CAD, measurement, or controlled document |

Validation must enforce approximately 288 expected rows for the target geometry (exact count set in configuration), unique IDs, finite coordinates, unit normals within tolerance, nonnegative power, legal duty cycles, and no duplicate positions unless physically justified.

Do not substitute electrical wattage for optical power. If the hardware count, source construction, or radiometry is not yet known, leave it unresolved and use a versioned synthetic geometry only for development.

## 6. Helmet-to-head registration

### Inputs

- helmet geometry in `helmet_mm`;
- head volume/surface in `head_world_mm`;
- helmet and head landmarks: nasion, inion, left/right preauricular points, and vertex where available;
- physical standoff or contact constraints;
- optional helmet interior surface or CAD mesh.

### Procedure

1. Establish an initial rigid transform from corresponding landmarks.
2. Refine using a constrained surface fit if an interior helmet mesh exists; preserve the initial and refined transforms.
3. Do not allow unconstrained scaling unless modeling explicit head-size adaptation. Any scale factor defines a separate geometry scenario.
4. Transform source positions and normals into head space.
5. Ray-cast each source toward the scalp to compute contact point, incidence angle, and standoff.
6. Render anterior, lateral, superior, and sectional QC views.

### Registration outputs and acceptance checks

- `T_head_from_helmet.json` with units, frame names, method, and checksum;
- transformed source table;
- landmark residuals and, if used, surface-fit residuals;
- fraction of rays intersecting scalp, distribution of incidence angles/standoffs, and collision report;
- visual QC images with source IDs;
- a signed/dated acceptance record before production simulation.

Registration uncertainty is a sensitivity variable, not merely a preprocessing nuisance.

## 7. MCX/MCX-CL simulation strategy

### Primary strategy: per-emitter basis fields

For each emitter `i`:

1. load the same labeled anatomy and optical table;
2. set the registered position, direction, emitting profile, and aperture;
3. launch a declared photon count with a stored seed;
4. save a normalized fluence volume `F_i(r)` and the complete run manifest;
5. repeat selected sources/seeds for convergence estimation.

Form a scenario after simulation:

`Phi_i(r) = w_i * F_i(r)`

where `w_i` is derived from measured optical power, duty cycle, coupling factor, and the normalization documented for `F_i`. Then:

`Phi_total(r) = sum_i Phi_i(r)`.

This enables arbitrary activation patterns without rerunning photon transport, provided wavelength, anatomy, optical properties, source profile, and registration are unchanged.

### Cross-check strategy

Run at least one equivalent aggregate/pattern-source configuration, if supported without losing interpretability, and compare its total field with the sum of independent basis fields. Differences must be compatible with Monte Carlo noise and normalization. Before moving a frozen basis set between OpenCL and CUDA, run a prespecified backend-equivalence test on identical configurations; do not mix backends within a nominal basis set without passing that gate.

### Computation stages

- smoke: homogeneous/slab geometry, small photon count;
- pilot: representative frontal, parietal, temporal, and occipital emitters;
- benchmark: 850-nm distributed arrays;
- nominal: all sources at 1070 nm;
- sensitivities: reuse basis fields only when the changed parameter does not alter transport; otherwise rerun.

Photon count is not fixed in advance. Select it from convergence testing in `VALIDATION_AND_SENSITIVITY.md`. Use deterministic seed management without reusing identical random streams across nominally independent replicates.

## 8. Output volumes and summaries

### Required per-emitter outputs

- normalized fluence or fluence-rate basis volume;
- absorbed-energy volume where supported or unambiguously derived;
- run manifest, log, seed, and engine configuration;
- optional detected-photon/path data for diagnostics, not as the primary deliverable.

### Required aggregate outputs

- `total_fluence` or `total_fluence_rate` with explicit normalization;
- `absorbed_energy_density` or `absorbed_power_density`;
- `dominant_source_id` and `dominant_source_contribution`;
- `enhancement_factor`;
- `neighbor_contribution_fraction`;
- `effective_number_of_sources`;
- top-k contributor IDs/fractions or cumulative-contributor count;
- gray-matter and tissue masks;
- threshold/missing-value masks used for ratio metrics.

Report whole cortical gray matter and atlas-defined ROIs using mean, median, interquartile range, 5th/95th percentiles, and robust spatial coverage statistics. Maxima may be reported for QC but are not primary endpoints.

## 9. Multisource metrics

At a voxel or ROI element `r`, let nonnegative source contributions be `Phi_i(r)` and:

`Phi_total(r) = sum_i Phi_i(r)`.

Define the dominant contributor:

`Phi_dom(r) = max_i Phi_i(r)`.

### Dominant-source enhancement factor

`EF_dom(r) = Phi_total(r) / Phi_dom(r)`.

This is defined only where `Phi_dom` exceeds a prespecified absolute and/or signal-to-noise threshold. It ranges from 1 to the number of enabled sources. It answers how much the total exceeds the strongest single contribution at that location.

For direct Yue-and-Humayun-style comparisons, also compute a **benchmark reference-source enhancement**:

`EF_ref(r) = Phi_total(r) / Phi_ref(r)`,

where `ref` is selected by the benchmark protocol (for example, the source whose axis defines a sampled depth line). `EF_ref` and `EF_dom` are not interchangeable and must have distinct names in code and figures.

### Neighbor contribution fraction

`NCF(r) = [Phi_total(r) - Phi_dom(r)] / Phi_total(r) = 1 - Phi_dom(r)/Phi_total(r)`.

Define only where `Phi_total` passes the analysis threshold. Under this operational definition, every non-dominant source is a neighbor, regardless of physical distance. An optional distance-limited metric may separately sum sources outside or inside a declared geodesic/Euclidean radius; do not call it `NCF` without a suffix.

### Effective number of sources

Let `p_i(r) = Phi_i(r) / Phi_total(r)`. Define the inverse-Simpson participation number:

`N_eff(r) = 1 / sum_i p_i(r)^2 = Phi_total(r)^2 / sum_i Phi_i(r)^2`.

`N_eff = 1` when one source dominates and approaches `N` when `N` sources contribute equally. This measures contribution evenness, not a literal count of photons or emitters above a threshold.

### ROI aggregation rule

Compute metrics in two explicitly named ways:

1. **Field-first:** integrate each `Phi_i` over the ROI, then compute `EF_dom_ROI`, `NCF_ROI`, and `N_eff_ROI` from the integrated source contributions.
2. **Metric-first:** compute voxelwise metrics and summarize their distributions over the ROI.

These answer different questions and must not be conflated. Fluence-volume integration must account for voxel volume when calculating total energy-like quantities.

## 10. Analysis masks and numerical safeguards

- Define thresholds from convergence/noise behavior before inspecting headline results.
- Never display enhancement ratios in near-zero regions without a mask.
- Track zeros caused by geometry, truncation, numeric precision, or file corruption separately.
- Perform sums in adequate precision and test chunked/on-disk aggregation against an in-memory synthetic case.
- Verify nonnegativity and energy normalization on every basis volume.
- Keep raw normalized basis fields separate from device-weighted fields.

## 11. Provenance manifest

Each result must resolve to:

- anatomy ID/checksum;
- optical-table ID/checksum;
- emitter-geometry and calibration IDs/checksums;
- registration transform ID/checksum;
- wavelength and source model;
- MCX version, build, GPU, configuration, photon count, and seed;
- code revision and analysis configuration;
- output unit/normalization and derivation chain;
- creation timestamp and completion/error status.
