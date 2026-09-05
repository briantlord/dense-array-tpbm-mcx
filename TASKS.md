# Codex-Ready Task List

**Current state (4 September 2026):** start with [CURRENT_STATE.md](CURRENT_STATE.md) for the corrected 1070/refined 810 comparisons, new uncertainty audit. Older milestones below retain their historical scope.

Work in order. Do not mark scientific gates complete merely because the software accepts an input.

## Review follow-through — 4 September 2026

- [x] Preserve reviewed code, configurations, evidence and compact records in Git; recover exact historical analyzer snapshots.
- [x] Add a current/superseded scenario inventory and checksum-based large-artifact restore tooling.
- [x] Enforce generic basis engine identity before launch and on completion; validate transformed source geometry, 1-mm grids, supported sources and effective optical scenarios.
- [x] Replace 810 analyzer global patching with explicit settings and capture actual entrypoint/shared-code provenance.
- [x] Recompute corrected-fat 1070 overlap from all 277 existing native fields; verify exact agreement with the saved aggregate.
- [x] Add locked Windows setup and portable CI checks; remote CI execution remains to be verified after push.
- [x] Complete the bounded two-wavelength Monte Carlo audit: 18/21 endpoint ratios pass the declared screen; suppress three >=50-mm ratios and publish the qualified comparison.
- [ ] Obtain measured assembled geometry, spectral powers, beam profile and coupling/registration for the actual device pilot.
- [ ] Add validated cortical-ribbon/named-region masks and an adequately specified independent quantitative benchmark.
- [ ] Quantify optical/anatomy/registration uncertainty with endpoint simulations; conditional Monte Carlo intervals do not complete this task.
- [ ] Establish and verify an independent artifact archive; the OneDrive workspace is the presently identified copy.

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
- [x] Verify its DOI, exact wavelengths, tissue table, head model/version, emitter counts/layout, source definition, photon count, normalization, and comparison locations; classify unreported fields in `benchmarks/yue_2015_parameter_ledger.csv`.
- [x] Obtain and verify the full citation and reported methods for the recent realistic multisource helmet study listed in `REFERENCES.md`; its referenced additional tables remain to be obtained.
- [x] Run a current literature search for dense 1064/1070-nm multisource helmet models before retaining the novelty statement; see `literature/novelty_search_2026-08-13.md`.
- [x] Build a claim ledger separating published facts, search findings, inferences, and project hypotheses.
- [x] Record all inaccessible data or irreproducible details as benchmark limitations.

**Exit-gate status (2026-08-13):** novelty language and the reported Yue benchmark fields are supported by verified primary sources. Exact numerical reproduction remains intentionally approximate because the paper does not report several required implementation fields.

## P0 — Anatomy acquisition and QC

- [x] Select the official MNI Colin27 high-resolution 2008 NIfTI atlas source and record its license, version, headers, label counts, and checksums in `inputs/anatomy/colin27_2008/`.
- [x] Create `colin27_2008_native12_1mm_v3`, retaining the minimum required tissues plus the source's additional native tissue identities without merging.
- [x] Preserve physical geometry and document the 0.5-to-1-mm resampling, tie rule, field-of-view cleanup, and every label transition.
- [x] Generate label counts, physical volumes, orthogonal/multislice overlays, and outer/cortical surface projections.
- [x] Check head connectivity, enclosing layers, CSF preservation, cortical gray matter, internal air cavities, and source field-of-view artifacts; automated checks passed and visual QC was accepted.
- [x] Add compact machine-readable and Markdown anatomy QC reports under the versioned derived artifact.

**Exit gate:** anatomy gate in `PROJECT_PLAN.md` is signed off.

**Exit-gate status (2026-08-13):** accepted for anatomical use as `colin27_2008_native12_1mm_v3`. This does not approve optical properties, source registration, ROI mapping, or a production photon-transport run.

## P0 — 850-nm benchmark implementation

- [x] Transcribe the verified benchmark optical table with original units and citations as `yue2015_850_approx_v1`; preserve `musp`, the isotropic `g=0` conversion, and the unreported-index limitation.
- [x] Recreate the 277-source Table-1 layout and deterministic nested density tiers, with unreported azimuth phases and lower-density coordinates declared as project approximations.
- [x] Extend independent unit-source preparation/execution to provenance-gated benchmark anatomy and retain float64 weighted aggregation; a real 100,000-photon north-pole implementation check passed on the M4 Pro.
- [x] Reproduce single-source and total-field depth curves.
- [x] Reproduce reference-source enhancement at prespecified depths and across density tiers.
- [x] Quantify representative Monte Carlo and figure-digitization uncertainty. Corrected three-seed uncertainty is recorded through `10^9`; Figures 2b, 4, 5a, 5b, and 6c have a reproducible single-operator two-pass pixel ledger with the frozen one-pixel uncertainty rule.
- [x] Freeze convergence, digitization, and benchmark acceptance tolerances before evaluating the paper-scale representative tier.
- [x] Write a discrepancy report and regression-test the evaluated outputs without converting a failed quantitative gate into acceptance.

**Exit gate:** benchmark behavior is reproduced within justified tolerances or remaining mismatch is traced and declared.

**Current status (2026-08-14):** the corrected convergence sequence selected `10^8` photons per source, and all 277 basis fields completed without failure. Direct two-source aggregate equivalence passes every frozen component. The single/total curves, density tiers, `EF_ref`, explicit-mask uniformity alternatives, plots, and discrepancy report are complete and regression-tested. Profile shape (`Spearman r=0.964`) and density ordering pass, but the 25% quantitative headline gate fails (`EF_ref` 23.1 versus 7.78 at 40 mm; 22.4 versus 15.6 at 60 mm). A separately versioned segmentation/output study traced the deep single-source discrepancy to the non-identifiable anatomy/observable denominator: local tissue-boundary changes produce roughly 1.5x to 2.0x effects, an aggressive CSF bound produces 25.9x, and `mua * fluence` agrees with MCX energy output after one global scale. The 850-nm software-validation milestone is complete; the original quantitative external-reproduction criterion remains a recorded failure and is not rewritten as a pass.

## P0 — 1070-nm optical-property ledger

- [x] Search for wavelength-specific primary measurements or spectral models for every required tissue; retain negative findings as explicit gap records.
- [x] Record species/state/temperature/tissue definition and whether values are direct, interpolated, extrapolated, or assumed.
- [x] Preserve original `mua`, `mus`/`musp`, `g`, `n`, wavelength, and units before conversion.
- [x] Define discrete literature-scenario slots for brain dataset, skull scattering, blood state, refractive index, composite tissue, and CSF.
- [x] Classify conflicting sources explicitly and retain them as separate candidates; no default averaging was performed.
- [x] Generate an assumption-explicit `provisional_1070_v1` central table and 14 one-at-a-time variants with field-level provenance and a production-status preflight guard.
- [x] Perform an independent quantity/unit/wavelength audit of the saved provisional implementation; retain second-operator graph redigitization and surrogate-tissue acceptance as separate scientific blockers.
- [ ] Freeze `nominal_1070_v1` only after no required cell is `TBD`.

**Exit gate:** optical-property gate passes; until then, production 1070-nm simulation is blocked.

**Current status (2026-08-14):** first-pass search, primary-paper acquisition, provenance transcription, formula evaluation, tissue coverage, conflict classification, and the runnable provisional scenario set are complete. An independent implementation reconstructed all 12 rows from the saved source tables and passed quantity identity, unit conversion, wavelength labeling, spectral-formula arithmetic, and provenance-link checks. It does not constitute a second-operator graph redigitization or scientific acceptance of the surrogate tissue bindings. The all-`TBD` production table therefore remains authoritative, and `nominal_1070_v1` is not frozen.

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

- [x] Generate one immutable synthetic MCX configuration per emitter from validated inputs; production-status generation remains gated.
- [x] Prepare a five-source, 100,000-photon Colin27 pilot plan for `provisional_1070_v1`, using a separately identified software-only spatial scaffold and no target-hardware claims.
- [x] Execute the five-source provisional pilot on the M4 Pro and archive automated placement/field QC; retain the restricted-process v1 failure and complete replacement v2 runs separately.
- [x] Implement deterministic run IDs and independent seed allocation.
- [x] Implement resumable single-run execution without overwriting checksum-valid complete runs; batch scheduling remains pending.
- [x] Save normalized output, manifest, execution record, and failure state atomically.
- [x] Build a separately identified 277-source Yue-derived 1070-nm surrogate with unit-source calibration and constant-per-emitter versus constant-total weighting policies.
- [x] Run a five-region, three-seed surrogate convergence sequence; retain the failed `10^7` result and freeze `10^8` only after the versioned extension passes every region.
- [x] Prepare 277 checksum-valid surrogate run manifests with unique deterministic seeds; do not claim that preparation is execution.
- [x] Execute all 277 separately versioned Windows RTX 3080 Ti/OpenCL manifests at `10^8` photons; inventory 277 complete native fields, zero failures, and all output checksums.
- [x] Verify a representative source in each head region visually.
- [x] Implement radiometric weighting without modifying raw basis fields.
- [x] Implement a streaming aggregator to avoid loading all source volumes at once.
- [x] Cross-check a small multisource sum against an independently executed aggregate run; the two-source Windows check passes every pre-specified tolerance.

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

The following items are complete for `surrogate_yue277_1070_v1`; they must be repeated under a new identity after target-device inputs cross their gates.

- [x] Compute total field and absorbed-energy field with explicit units.
- [x] Compute dominant source ID/contribution and top-k contributors.
- [x] Compute `EF_dom`; compute `EF_ref` only for the documented superior-reference protocol.
- [x] Compute `NCF` and `N_eff` with the pre-specified near-zero mask.
- [x] Compute both field-first and metric-first cortical/ROI summaries.
- [x] Produce cortical maps, volume slices, distributions, and source-contribution examples.
- [x] Verify metric bounds and manually inspect representative fields/ROIs.
- [x] Create a result manifest linking every figure/table to its data and code revision.

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
