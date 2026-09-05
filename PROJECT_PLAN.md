# 1070-nm Dense-Array tPBM Monte Carlo Project Plan

**Current state (4 September 2026):** start with [CURRENT_STATE.md](CURRENT_STATE.md) for the corrected 1070/refined 810 comparisons, new uncertainty audit. Older milestones below retain their historical scope.

## Project status

Bootstrap specification. No optical-property value, helmet dimension, emitter output, or performance result in this repository should be treated as measured until it has a cited source and passes the gates below.

## Scientific objective

Build a reproducible Python-orchestrated MCX/MCX-CL workflow that estimates the three-dimensional optical field from a realistic dense transcranial photobiomodulation (tPBM) helmet operating near 1070 nm. The primary question is:

> In cortical gray matter, how much of the modeled fluence from a dense dense-array helmet is due to spatial overlap from emitters other than the locally dominant emitter?

Primary analyses will quantify total fluence, absorbed energy, multisource enhancement, neighbor contribution, and the effective number of contributing emitters. Results are model estimates conditional on the anatomy, optical properties, source characterization, registration, and Monte Carlo settings—not direct measurements of dose or biological effect.

## Novelty statement

Multisource transcranial photon-transport modeling is not new. Yue and Humayun modeled distributed arrays up to 277 emitters at approximately 850 nm and superimposed the per-source fields. Cassano et al. (2019) and Yuan et al. (2020) modeled frontal LED arrays at 1064 nm, and Dole et al. (2024) modeled a realistic multisource helmet at 670/810 nm. The proposed contribution is narrower:

> A realistic dense whole-head approximately 1070-nm helmet, registered to a human head model, with retained per-emitter fields and explicit voxelwise and regionwise attribution of cortical optical-field overlap.

The 2026-08-13 search identified no exact report combining those elements, but this remains a candidate gap rather than a priority claim. See `literature/novelty_search_2026-08-13.md`, and refresh it before publication.

## Scope

Version 1 will:

- use the maintained MCX family rather than implement photon transport from scratch: standalone MCX-CL under Python orchestration on Apple Silicon and CUDA MCX/PMCX on NVIDIA systems;
- use Python for validation, configuration generation, execution, provenance capture, aggregation, analysis, and reporting;
- begin with one documented, segmented adult head atlas at approximately 1-mm isotropic resolution;
- represent scalp/skin, skull, CSF, gray matter, and white matter at minimum;
- import a versioned emitter table for independently addressable sources;
- register helmet coordinates to head coordinates using explicit landmarks and transforms;
- characterize every tissue with provenance-tracked optical properties at 1070 nm;
- simulate each emitter independently at unit launched energy or power, retain per-source output, and form weighted sums afterward;
- produce whole-head, cortical-surface, and region-of-interest summaries;
- reproduce a Yue-and-Humayun-style 850-nm dense-array benchmark before interpreting the novel configuration;
- run photon-count convergence and optical-property, geometry, registration, and source-density sensitivity analyses.

## Non-goals for version 1

- Developing a new Monte Carlo engine.
- Claiming a biological efficacy threshold or clinical benefit.
- Treating modeled fluence as measured intracranial dose.
- Thermal or bioheat modeling.
- Modeling photochemistry, cytochrome-c-oxidase action spectra, or mitochondrial response.
- Subject-specific MRI analysis, population inference, or intersubject variability.
- Detailed hair-fiber geometry. Hair/coupling can enter as a documented attenuation scenario only after the no-hair/reference model is stable.
- Full wavelength-resolved LED spectra; version 1 uses a monochromatic 1070-nm approximation, with spectral integration reserved for later work.
- Automatic optimization of emitter placement or drive currents.
- Treating 1064-nm values as interchangeable with 1070-nm values.

## Scientific gates

1. **Anatomy gate:** segmentation source, license, voxel size, coordinate convention, labels, and checksums are recorded.
2. **Optical-property gate:** every value has a tissue definition, wavelength, quantity definition, units, source, and transformation history. Unresolved values remain `TBD` and block production runs.
3. **Hardware gate:** source positions, normals, emitting areas/profiles, radiometric outputs, and standoff/coupling assumptions are measured or traceable to controlled documents.
4. **Registration gate:** landmarks, coordinate frames, transform direction, fit error, and collision/standoff checks are saved.
5. **Benchmark gate:** software correctness is established by convergence, field integrity, aggregate equivalence, and regression tests; external numerical reproduction is evaluated separately against prespecified paper targets without treating unreported methods as recoverable inputs.
6. **Convergence gate:** cortical and ROI estimates are stable to increased photon count and repeated random seeds.
7. **Interpretation gate:** figures and prose label nominal versus sensitivity results and do not convert modeled optical quantities into biological claims.

**Current gate status (2026-08-14):** the anatomy gate is accepted as `colin27_2008_native12_1mm_v3`. The Yue implementation passes convergence, field-integrity, direct aggregate-equivalence, profile-shape, and density-ordering checks. Its frozen 25% paper-reproduction target remains failed. Post hoc sensitivity shows that segmentation and the fluence-versus-absorbed-energy denominator can readily change deep single-source magnitude, while the paper omits the exact SPM segmentation and output normalization. The software benchmark milestone is therefore complete with a preserved negative external-reproduction result, not a failed transport implementation. The independent 1070-nm quantity/unit/wavelength audit passes mechanically, and a separately named 277-source Yue-derived 1070-nm surrogate is prepared at the regionally converged `10^8`-photon tier. Neither result passes the target-hardware or production optical-property gates.

## Architecture

```text
inputs/
  anatomy/                 segmented volume, label map, affine, license, checksum
  optical_properties/      source ledger and frozen scenario tables
  emitters/                raw geometry, calibrated geometry, output weights
  registration/            landmarks and helmet-to-head transforms
configs/                   immutable, backend-portable MCX JSON configurations
src/                       import, validation, simulation, aggregation, analysis
runs/                      manifests, logs, seeds, versions; large arrays ignored
results/                   numeric summaries and publication-ready figures
tests/                     schema, unit, synthetic, regression, and benchmark tests
```

The computational flow is:

```text
provenance-checked inputs
        -> registered source model
        -> one normalized MCX run per emitter
        -> per-emitter fluence basis volumes
        -> radiometric/duty-cycle weighting and linear superposition
        -> cortical and ROI attribution metrics
        -> sensitivity ensemble and uncertainty-qualified reporting
```

Each run manifest must record the code revision, MCX version/build, GPU, anatomy and table checksums, source ID, source normalization, photon count, random seed, output type, voxel size, time gates if any, and full configuration hash.

## Milestones

### M0 — Reproducible scaffold

- Create directory layout, environment notes, schemas, run manifests, and smoke tests.
- Run an MCX homogeneous/slab example and verify normalization and units.

### M1 — 850-nm benchmark

- Implement a documented Colin27-style head and distributed array.
- Reproduce the source-density and depth-dependent multisource behavior reported by Yue and Humayun to the extent permitted by available methods and inputs.
- Freeze benchmark outputs as regression tests.

### M2 — Nominal 1070-nm model

- Complete the 1070-nm optical-property ledger.
- Import and validate the planned source array.
- Complete helmet-to-head registration and render inspection views.
- Run a converged nominal per-emitter basis set.

### M3 — Cortical overlap analysis

- Compute total fluence, absorbed energy, dominant-emitter field, enhancement, neighbor fraction, effective source count, and contributor rank maps.
- Produce ROI summaries with uncertainty from Monte Carlo repeats.

### M4 — Sensitivity and density study

- Complete optical-property, source-geometry, registration, coupling/output, and density sweeps.
- Separate robust findings from assumptions that change the conclusion.

### M5 — Reproducible release packet

- Re-run from frozen manifests.
- Archive tables, code, validation outputs, and a limitations/claim ledger.
- Prepare a methods-ready report without claiming experimental validation.

## Success criteria

The project is successful when:

- a clean environment can reproduce the benchmark and nominal analysis from documented commands;
- no production run uses an unresolved or uncited optical-property placeholder;
- source and coordinate schemas reject invalid units, non-unit normals, duplicate IDs, and out-of-volume sources;
- per-emitter superposition agrees numerically with an independently computed aggregate case within a prespecified Monte Carlo tolerance;
- benchmark discrepancies are quantified and explained rather than hidden;
- nominal cortical/ROI metrics satisfy declared convergence tolerances;
- enhancement, neighbor fraction, and effective source count are computed from clearly defined denominators and include masks for unstable near-zero regions;
- sensitivity analyses identify which conclusions survive plausible property and geometry variation;
- every result is traceable to a run manifest and every plotted unit is explicit;
- conclusions remain optical and conditional, with experimental and biological validation boundaries stated.

## Immediate next action

The provisional 277-source surrogate basis, direct superposition check, and frozen overlap analysis are complete on the Windows RTX 3080 Ti. Do not extend those conditional results into target-device claims. The controlling next gate is to obtain the exact target helmet model/revision, emitter coordinates and normals, radiometry, beam profile, duty cycle, standoff/coupling evidence, and registration landmarks; those inputs require a new geometry, transport basis, and result identity.

In parallel, use the completed surrogate package only as a software/scientific-sensitivity baseline. Version the next protocols before execution, beginning with the declared high-impact optical-property cases and nested source-density subsets under both constant-per-emitter and constant-total relative weighting. Preserve the current central fields and analysis as immutable controls, and keep thermal, measured-dose, and biological-efficacy interpretations out of scope.
