# Codex-Ready Task List

Work in order. Do not mark scientific gates complete merely because the software accepts an input.

## P0 — Repository and execution scaffold

- [x] Create `inputs/{anatomy,optical_properties,emitters,registration}`, `configs`, `src`, `runs`, `results`, and `tests` directories.
- [x] Add a concise `README.md` with environment setup and the exact smoke-test command.
- [x] Choose Python 3.13 as the primary orchestration path, using pinned standalone MCX-CL on Apple Silicon and PMCX/MCX on NVIDIA systems; retain MATLAB only for independent checks.
- [x] Record the verified Python, standalone MCX-CL, operating-system, GPU/runtime, package-lock, and license metadata; document why PMCXCL was rejected and mark PMCX/CUDA as unverified.
- [x] Add `.gitignore` rules for large MCX arrays, caches, and local machine paths while retaining manifests and summaries.
- [x] Define naming rules for scenario IDs, run IDs, coordinate frames, checksums, and immutable versions.
- [x] Implement a run-manifest schema containing every field required by `MODEL_SPEC.md`.
- [x] Add a Python command that validates all inputs before any MCX or MCX-CL launch.
- [x] Run a homogeneous synthetic MCX-CL example on the M4 Pro and archive only its small QC summary.

**Exit gate passed on the M4 Pro (2026-08-13):** a new checkout can execute and validate a smoke run from `./scripts/verify_scaffold.sh`.

## P0 — Schemas and synthetic tests

- [x] Implement the emitter table and JSON Schema from `MODEL_SPEC.md`.
- [x] Implement the optical-property table schema and an all-`TBD` production template.
- [x] Create a conspicuously named `synthetic_test_only` optical table and geometry for unit tests.
- [x] Reject duplicate emitter IDs, invalid normals, illegal duty cycles, missing provenance, and mixed units.
- [x] Test `musp = mus * (1-g)` conversions and cm^-1/mm^-1 conversions.
- [x] Implement unit tests for `EF_dom`, `EF_ref`, `NCF`, and `N_eff`, including zeros and near-zero masks.
- [x] Test field-first versus metric-first ROI calculations on a small hand-computable array.
- [x] Test on-disk/chunked aggregation against an in-memory high-precision sum.

**Exit gate passed (2026-08-13):** synthetic tests pass without using any production parameter as a placeholder.

## P0 — Literature and source verification

- [x] Obtain and read Yue & Humayun (2015), including all methods, figures, and references in the supplied paper. No separate supplement was identified in the supplied PDF.
- [ ] Verify its DOI, exact wavelengths, tissue table, head model/version, emitter counts/layout, source definition, photon count, normalization, and comparison locations.
- [x] Obtain and verify the full citation and reported methods for the recent realistic multisource helmet study listed in `REFERENCES.md`; its referenced additional tables remain to be obtained.
- [ ] Run a current literature search for dense 1064/1070-nm multisource helmet models before retaining the novelty statement.
- [ ] Build a claim ledger separating published facts, digitized estimates, inferences, and project hypotheses.
- [ ] Record all inaccessible data or irreproducible details as benchmark limitations.

**Exit gate:** benchmark inputs and novelty language are supported by verified primary sources.

## P0 — Anatomy acquisition and QC

- [ ] Select an atlas compatible with the benchmark and record license/version/checksum.
- [ ] Create the minimum tissue label map: scalp, skull, CSF, gray matter, white matter.
- [ ] Preserve the native affine and document every resampling or label merge.
- [ ] Generate label counts, physical volumes, orthogonal slices, and surface renders.
- [ ] Check layer continuity, CSF preservation, cortical mask, and internal holes.
- [ ] Add a compact anatomy QC report to the run artifacts.

**Exit gate:** anatomy gate in `PROJECT_PLAN.md` is signed off.

## P0 — 850-nm benchmark implementation

- [ ] Transcribe the verified benchmark optical table with original units and citations.
- [ ] Recreate or approximate the published distributed emitter layouts with deviations documented.
- [ ] Implement independent unit-source simulations and weighted aggregation.
- [ ] Reproduce single-source and total-field depth curves.
- [ ] Reproduce reference-source enhancement at prespecified depths and across density tiers.
- [ ] Quantify Monte Carlo and digitization uncertainty.
- [ ] Freeze acceptance tolerances before evaluating final benchmark runs.
- [ ] Write a discrepancy report and regression-test the accepted outputs.

**Exit gate:** benchmark behavior is reproduced within justified tolerances or remaining mismatch is traced and declared.

## P0 — 1070-nm optical-property ledger

- [ ] Search for wavelength-specific primary measurements or spectral models for every required tissue.
- [ ] Record species/state/temperature/tissue definition and whether values are direct, interpolated, extrapolated, or assumed.
- [ ] Preserve original `mua`, `mus`/`musp`, `g`, `n`, wavelength, and units before conversion.
- [ ] Define defensible uncertainty ranges or discrete literature scenarios.
- [ ] Resolve conflicting sources explicitly; do not average by default.
- [ ] Perform an independent quantity/unit/wavelength audit.
- [ ] Freeze `nominal_1070_v1` only after no required cell is `TBD`.

**Exit gate:** optical-property gate passes; until then, production 1070-nm simulation is blocked.

## P0 — Helmet geometry and radiometry

- [ ] Obtain the exact hardware model/revision and verified emitter count.
- [ ] Import CAD coordinates/normals or define a documented digitization protocol.
- [ ] Assign stable emitter and group IDs.
- [ ] Measure or obtain radiometric optical power, spectrum/peak/FWHM, emitting area, angular profile, and uncertainty.
- [ ] Record duty cycle/program behavior separately from CW-equivalent calibration.
- [ ] Measure standoff/contact and define ideal versus realistic coupling scenarios.
- [ ] Render the helmet and inspect all source normals and duplicate/colliding positions.
- [ ] Validate the final table against the schema and archive calibration provenance.

**Exit gate:** hardware gate passes; electrical power ratings alone do not pass it.

## P1 — Helmet-to-head registration

- [ ] Define helmet and head coordinate frames and landmark conventions.
- [ ] Fit and save `T_head_from_helmet` using documented landmarks.
- [ ] If applicable, refine against helmet/head surfaces without undocumented scaling.
- [ ] Transform positions/normals and ray-cast to the scalp.
- [ ] Report landmark residuals, incidence angle, standoff, scalp hits/misses, and collisions.
- [ ] Produce labeled anterior/lateral/superior and slice QC renders.
- [ ] Obtain visual acceptance and freeze registration version.

**Exit gate:** registration gate passes with saved residuals and QC images.

## P1 — MCX basis-field runner

- [x] Generate one immutable synthetic MCX configuration per emitter from validated inputs; production/anatomical generation remains gated.
- [x] Implement deterministic run IDs and independent seed allocation.
- [x] Implement resumable single-run execution without overwriting checksum-valid complete runs; batch scheduling remains pending.
- [x] Save normalized output, manifest, execution record, and failure state atomically.
- [ ] Verify a representative source in each head region visually.
- [ ] Implement radiometric weighting without modifying raw basis fields.
- [ ] Implement a streaming aggregator to avoid loading all approximately 288 volumes at once.
- [ ] Cross-check a small multisource sum against an aggregate/pattern-source run.

**Exit gate:** per-emitter and aggregate paths agree within stochastic tolerance.

## P1 — Convergence and nominal production run

- [ ] Execute the photon-count/seed convergence protocol on representative sources.
- [ ] Define cortical/ROI and ratio-map tolerances before selecting production count.
- [ ] Freeze production photon count and seed strategy.
- [ ] Estimate storage/runtime and document the compute environment.
- [ ] Run all enabled emitters for `nominal_1070_v1`.
- [ ] Validate output completeness, checksums, normalization, nonnegativity, and masks.
- [ ] Rerun failed sources only from identical frozen configs with new run IDs as appropriate.

**Exit gate:** nominal fields are complete, traceable, and converged for primary endpoints.

## P1 — Multisource analysis

- [ ] Compute total field and absorbed-energy field with explicit units.
- [ ] Compute dominant source ID/contribution and top-k contributors.
- [ ] Compute `EF_dom`; compute `EF_ref` only for a documented reference protocol.
- [ ] Compute `NCF` and `N_eff` with prespecified near-zero masks.
- [ ] Compute both field-first and metric-first cortical/ROI summaries.
- [ ] Produce cortical maps, volume slices, distributions, and source-contribution examples.
- [ ] Verify metric bounds and manually inspect representative voxels/ROIs.
- [ ] Create a result manifest linking every figure/table to its data and code revision.

**Exit gate:** every headline number can be regenerated from one frozen result manifest.

## P1 — Sensitivity and density analyses

- [ ] Run one-at-a-time and grouped optical-property scenarios.
- [ ] Run registration, standoff, angular, position, output, and failed-emitter scenarios.
- [ ] Add hair/coupling scenarios only when the attenuation model is defensible.
- [ ] Construct nested spatially balanced source-density subsets.
- [ ] Compare constant-per-emitter and constant-total-power density sweeps.
- [ ] Quantify marginal gains, coverage, uniformity, and overlap metrics.
- [ ] Identify parameter choices that reverse or materially weaken conclusions.

**Exit gate:** final conclusions distinguish robust findings from assumption-sensitive ones.

## P2 — Reporting and future validation

- [ ] State the achieved validation level on every report.
- [ ] Prepare methods, limitations, provenance, and claim-ledger documents.
- [ ] Archive exact environment, configurations, checksums, and small reproducibility fixtures.
- [ ] Design a 1070-nm phantom validation experiment with calibrated detectors and uncertainty budget.
- [ ] Scope subject/anatomy variability, hair, spectral integration, and thermal modeling as separate follow-on work.
- [ ] Refresh the novelty search immediately before manuscript submission.

## Definition of done

- [ ] All success criteria in `PROJECT_PLAN.md` pass.
- [ ] No unresolved production placeholder appears in a run manifest.
- [ ] Benchmark, nominal, and sensitivity results are reproducible.
- [ ] Claims remain limited to modeled optical fields at the achieved validation level.
