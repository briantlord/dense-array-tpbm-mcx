**Project workspace review — 4 September 2026**

**Public copy:** device-specific material has been omitted; the complete original remains local.

The project is a strong exploratory photon-transport research platform with substantial completed computation, careful scientific qualification, and useful sensitivity experiments. Its saved numerical results are internally consistent in the checks performed here. Reproducibility and documentation have fallen behind the newer work, and several validation boundaries need strengthening. The real helmet model remains incomplete.

The most useful next milestone is a reproducible, uncertainty-qualified comparison with an explicit path to the actual device. Further undirected full-array runs would add less value than closing the specific gaps below.

| Area | Assessment | Main reason |
|---|---|---|
| Research design and provenance | Strong for provisional research | Explicit source ledgers, scenario identities, failed-gate preservation, and clearly stated limitations |
| Numerical implementation | Strong within the exercised 1-mm pencil-source workflow | Tested aggregation and unit conversion; saved field integrity and energy accounting checked |
| Scientific validation | Partial | External quantitative benchmark failed; current wavelength comparison has unresolved optical and convergence uncertainty |
| Reproducibility | Mixed | Good run manifests, but historical analyzer drift, missing analysis entry points, and extensive untracked work |
| Maintainability | Moderate | A useful core package surrounded by increasingly specialized scripts and duplicated utilities |
| Actual device readiness | Incomplete | Device-specific evidence omitted; registered 3D geometry, spectral source weights, beam behavior, and scalp coupling are not yet modeled |
| Communication | Mixed | Detailed local reports are careful; the workspace entry points do not describe the current state |

**Scope and verification.** I inventoried all project directories, inspected Git history and local changes, mapped the Python modules, reviewed the core execution/validation/aggregation code and recent analyses, read the main plans and result reports, inspected anatomy/result figures, and reviewed all five files in the helmet folder. The inventory contains 17,819 files totaling approximately 96.2 GB, excluding Git internals, local engines, virtual environments, caches, and scratch files. There are 74 Python files and 15,059 lines across source, scripts, and tests.

This was a workspace-wide review with focused code and numerical checks, rather than a line-by-line certification of every generated file or a fresh systematic literature review. No GPU simulations were launched and no existing implementation, configuration, or scientific result was changed.

The [machine-readable review evidence](<C:/Users/brian/OneDrive/Projects/MCX Project/reviews/REVIEW_EVIDENCE_2026-09-04.json>) records the inventory, basis audits, numerical cross-checks, test result, and isolated validation probes.

| Check performed | Outcome |
|---|---|
| Full existing test suite, Windows Python environment | **108 passed, 1 failed**, 18.35 seconds |
| Original 1070 optical-ledger audit | Structurally valid; 59 evidence records, 12 labels covered, 60 unresolved production cells; production blocked |
| Provisional optical-table freshness and independent arithmetic audit | Passed; scientific tissue-mapping limitations remain |
| Basis-index inventory | 12 indices inspected; all referenced manifests present; seven complete 277-source bases, plus a completed five-source pilot |
| Corrected 1070, refined 810, and water-counterfactual integrity | **831/831 native fields matched recorded SHA-256**, with 11,634 input/output/volume reference checks; 277 unique seeds in each basis; observed binary hashes matched declared builds |
| Five top-level result manifests | 94 references checked; one historical analyzer checksum mismatch; other declared references matched |
| Independent aggregate absorption calculations | Reproduced saved headline values; arrays finite and nonnegative; tissue absorption agreed with mean engine logs within 0.00015 percentage points |
| Isolated validation probes | Reproduced engine-identity, source-validation, optical-override, and rotated-affine gaps described below |

The complete raw-field checksum audit covered those three current comparison bases, not every historical field in the 96.2-GB workspace. Recomputing tissue integrals from saved aggregates and comparing engine energy budgets provides a separate numerical cross-check; it is not independent experimental validation or a fresh re-sum of every raw field.

**What the completed work establishes.** The project progressed through a working standalone MCX-CL adapter, explicit anatomy derivation and QC, a 277-source Yue approximation, provisional 1070 optical scenarios, regional convergence, Windows backend checks, streaming overlap analysis, three fat-absorption variants, targeted first-entry tallies, refined 810 properties and a complete basis, and a water-only counterfactual. The progression is substantial and the later sensitivity studies materially improve the interpretation.

Several decisions deserve retaining: the rejected in-process output path and corrected JNIfTI array-order handling are documented; native tissue labels and transformations are preserved; failed experiments remain distinguishable from replacements; field-first and voxelwise overlap statistics are separated; and first entry, fluence, absorption, and biological effect are not treated as interchangeable quantities. The numerical normalization is consistent with the [official MCX-CL output documentation](https://mcx.space/wiki/index.cgi/index.cgi?action=browse&id=MCXCL%2FREADME&revision=2.0), and the independent energy-budget check supports the implementation used here.

The current equal-total-launch results are:

| Scenario | Gray-matter absorption | White-matter absorption | Total brain absorption |
|---|---:|---:|---:|
| Original 1070, extreme-high fat absorption | — | — | 0.4458% |
| Corrected provisional 1070, fat absorption 0.010 mm^-1 | 1.17758% | 0.03667% | **1.21425%** |
| Refined provisional 810 | 0.82698% | 0.30657% | **1.13355%** |
| 1070 whole-head water-only counterfactual | 1.85242% | 0.06039% | **1.91281%** |

The first row is an old sensitivity baseline. The counterfactual substitutes the 810 water-absorption term while retaining other 1070 properties; it does not represent a physical full-810 scenario. The current 810 model has about 2.32 times the integrated brain fluence of corrected 1070, while its total brain absorption is about 6.65% lower. These differences describe the selected optical scenarios and launch geometry. They do not establish a robust overall wavelength winner.

The [fat study](<C:/Users/brian/OneDrive/Projects/MCX Project/results/surrogate_yue277_1070_fat_absorption_bracket_v1/analysis_qc.md>) is particularly valuable: changing one uncertain tissue coefficient changes brain absorption by factors of roughly two to three relative to the original model. The [water counterfactual](<C:/Users/brian/OneDrive/Projects/MCX Project/results/surrogate_yue277_1070_water_counterfactual_v1/report.md>) usefully separates brain/CSF effects from much more assumption-sensitive superficial-tissue effects. Together they show why uncertainty in tissue representation is a central research question.

**Priority 1 — Preserve a reproducible current state.** At review start, Git had three modified tracked files and **3,598 untracked files**, including eight analysis/preparation scripts, newer configurations, run records, results, and helmet evidence. The last commit is `00f714df`, dated 17 August; newer work extends through the end of August. A checkout of the current commit cannot reconstruct this workspace's latest analyses.

The failing test is [test_surrogate_analysis_result.py:46](<C:/Users/brian/OneDrive/Projects/MCX Project/tests/test_surrogate_analysis_result.py:46>). The original 1070 result records analyzer SHA-256 `646e5c5b...`; the working script now hashes to `efa6c64c...` because it was adapted for subsequent work. I verified that the committed original script still matches the recorded historical hash. This is a repairable provenance mismatch, with no demonstrated corruption of the original numerical outputs. Preserve the historical implementation under its original identity and introduce the reusable/new analyzer separately, or pin the historical result to recoverable code at a specific revision. Merely replacing the old hash with the new hash would misrepresent how that result was generated.

The [810 wrapper](<C:/Users/brian/OneDrive/Projects/MCX Project/scripts/analyze_surrogate_810_windows_basis.py:9>) changes module globals and calls the shared analyzer. Its result manifest records only the shared **1070** script via [its `__file__` handling](<C:/Users/brian/OneDrive/Projects/MCX Project/scripts/analyze_surrogate_1070_windows_basis.py:689>). Following the recorded script alone invokes the 1070 defaults. Record the actual entry point, arguments, shared code, environment/lock identity, and recoverable source snapshot. The fat, water, and regional comparison manifests also lack a code record; some separately written reports are outside the output list. Apply one result-manifest contract across all analyses.

Commit the reviewed source and compact records, retain failed/superseded versions, and create an explicit inventory of current, superseded, planned, and failed scenarios. Large fields can stay outside Git, but need a documented restore location or regeneration procedure and a tested checksum-based restore. OneDrive has already caused documented execution and manifest-lock failures; a local compute directory with controlled archive synchronization would simplify future runs.

**Priority 1 — Close gaps in execution and scientific-input validation.** These are reproduced code issues. They warrant fixes before new model extensions; the audited current fields had matching inputs and binary records.

| Issue | Evidence and consequence | Recommended correction |
|---|---|---|
| Engine identity is recorded but not enforced by generic execution | [basis.py:345](<C:/Users/brian/OneDrive/Projects/MCX Project/src/mcx_project/basis.py:345>) accepts an executor result reporting `WRONG_ENGINE` and a zero hash, marks it complete, and passes preflight in an isolated synthetic fixture. Generic CLI/index runners resolve the binary independently of the declared environment. | Compare actual binary hash/version and selected device against the frozen binding before launch; reject mismatched recorded engine metadata afterward. |
| Engine source position/direction is not cross-checked against geometry and registration | [preflight.py:144](<C:/Users/brian/OneDrive/Projects/MCX Project/src/mcx_project/preflight.py:144>) checks IDs and model types but not the transformed position/normal. A synthetic configuration with position `[-10000,-10000,-10000]` and zero direction passed after its checksum references were updated. | Recompute the expected source transform; require finite unit direction and a valid launch/scalp-intersection policy. External sources should be supported deliberately, rather than categorically rejected. |
| Targeted optical overrides bypass coefficient validation | [run_targeted_penetration_tallies.py:110](<C:/Users/brian/OneDrive/Projects/MCX Project/scripts/run_targeted_penetration_tallies.py:110>) checks Python numeric types. Both negative absorption and NaN were accepted in direct probes. The path also permits incomplete replacement tables. | Validate the effective scenario after all overlays: finite coefficients, physical ranges, required tissue coverage, consistent `mus`, `musp`, and `g`, and the reserved background row. Distinguish a full scenario from an explicitly partial overlay. |

The project already has useful validation functions; consolidating these paths would improve reliability more than adding more one-off checks. Add negative tests that exercise the actual launch and analysis boundaries, alongside existing arithmetic and artifact regression tests.

**Priority 1 — Qualify the wavelength comparison and deep ratios with endpoint-specific uncertainty.** The [810 convergence record](<C:/Users/brian/OneDrive/Projects/MCX Project/configs/surrogate_yue277_810_v2_regional_convergence_inheritance.json:32>) explicitly inherits 100 million photons from the 1070 setup. This is a transparent provisional choice, but changed absorption/scattering and new depth-resolved endpoints require their own convergence evidence. The fat study also has one realization per emitter and no formal Monte Carlo interval.

The regional analyzer uses only a positive-denominator condition for [depth-bin ratios](<C:/Users/brian/OneDrive/Projects/MCX Project/scripts/analyze_regional_absorbed_energy_density.py:567>) and [voxel ratio maps](<C:/Users/brian/OneDrive/Projects/MCX Project/scripts/analyze_regional_absorbed_energy_density.py:278>). Its report prints **1,054.264 times** for white matter at depth at least 50 mm. The underlying numbers are approximately `2.344e-5` versus `2.223e-8` joules absorbed per 100 joules launched. The arithmetic is correct; the precision and robustness of that ratio are not established. A vivid saturated ratio map can emphasize very small absolute deposition.

Prespecify uncertainty and minimum-signal criteria for those endpoints, repeat representative sources or aggregate experiments at both wavelengths, check photon-count and time-window stability, and suppress/flag ratios that do not meet the criteria. Report the absolute numerator and denominator alongside ratios, using scientific notation for tiny values. Distinguish Monte Carlo variation from optical-property, anatomy, and registration uncertainty.

The approximate marrow absorption range in the [810 report](<C:/Users/brian/OneDrive/Projects/MCX Project/results/surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_v2/report.md>) transfers a relative **first-entry** sensitivity to **absorbed energy**. The report correctly labels that assumption. It should remain an illustrative propagated scenario range, not a measured confidence interval or a replacement for endpoint simulations.

**Priority 2 — Make the anatomy and source adapter's supported scope explicit.** Current runs use an axis-aligned, 1-mm atlas and pencil sources. The implementation is narrower than the schemas suggest:

- [basis.py:102](<C:/Users/brian/OneDrive/Projects/MCX Project/src/mcx_project/basis.py:102>) transforms positions into voxel coordinates but leaves directions in the head/world frame. A 90-degree rotated-affine fixture returned voxel position `[0,-1,0]` and direction `[1,0,0]`; the direction should rotate into the voxel frame as well. The accepted atlas has an identity spatial basis, so this probe does not invalidate its existing runs.
- [standalone.py:90](<C:/Users/brian/OneDrive/Projects/MCX Project/src/mcx_project/standalone.py:90>) hardcodes `LengthUnit = 1.0`; the volume preparation does not enforce that the NIfTI voxel spacing is actually 1 mm. This must be enforced or generalized before changing resolution.
- The emitter/engine schemas admit disk, Gaussian, and pattern sources, but [the renderer](<C:/Users/brian/OneDrive/Projects/MCX Project/src/mcx_project/standalone.py:116>) emits only type, position, and direction. The preparation path drops beam parameters. The [official pinned MCX-CL specification](https://github.com/fangq/mcxcl/blob/v2025.10/README.md) separately defines grid length and source parameters. Reject unsupported models now, then implement and test the measured aperture/angular profile when extending to the helmet.

**Priority 2 — Bring conclusions and task status up to date.** The root README, plan, and task list largely describe the earlier 1070 milestone. The runnable central optical generator still intentionally reconstructs the historical high-fat scenario, while newer reports recommend the effective-adipose comparator. A newcomer can follow valid commands and end up using an outdated scientific default.

Add a short current-state record linking the intended provisional 1070 comparator, refined 810 basis, sensitivity alternatives, controlling reports, and unresolved gates. Make historical defaults visibly historical without rewriting frozen artifacts. The current 1070 overlap maps also belong to the original high-fat run; the 810 report correctly avoids treating them as corrected-fat overlap results. Recompute corrected-fat overlap statistics from the existing basis before presenting a matched overlap comparison.

Current ROI summaries are whole gray matter, whole white matter, and their union. The [analysis masks](<C:/Users/brian/OneDrive/Projects/MCX Project/scripts/analyze_surrogate_1070_windows_basis.py:377>) are tissue-label masks; they do not implement the cortical ribbon or named target ROIs specified in the model plan. Add explicit cortical/region masks and validation before making region-specific targeting or cortical-coverage claims. The regional depth shells are useful geometric summaries, not anatomical parcellations.

The failed [Yue quantitative reproduction](<C:/Users/brian/OneDrive/Projects/MCX Project/benchmarks/yue2015_approx_v1/multisource_1e8_v2/discrepancy_report.md>) must remain a failed external benchmark. Profile shape, ordering, aggregate equivalence, and sensitivity investigations are useful evidence, but do not turn the 40/60-mm quantitative mismatch into external validation. Choose an additional experiment/benchmark with sufficiently specified inputs and observables for the next validation step.

**Device information omitted from this publication copy.**

**Maintainability and presentation improvements.** Replace module-global patching with an explicit analysis configuration object. Move repeated hashing, atomic writing, source loading, scenario overlay, and manifest generation into shared functions. Add a consistent refuse-overwrite policy: [the regional analyzer](<C:/Users/brian/OneDrive/Projects/MCX Project/scripts/analyze_regional_absorbed_energy_density.py:474>) currently allows an existing output directory and replaces files, unlike most other versioned analyses.

Add automated software checks for the newer 810/water/regional paths and a compact synthetic integration fixture. No CI workflow was present in the reviewed inventory. The main installed Python packages match `uv.lock`, but the Windows setup uses unrestricted `pip install -e .` within broad dependency ranges, so a future setup is not guaranteed to reproduce that environment. Enforce the lock consistently and separate fast software tests from optional artifact/GPU checks. Some current tests copy the entire `inputs` tree, including large local anatomy data, where a small purpose-built fixture would suffice.

The figures are useful internal QC. The inspected depth-profile chart lacks numerical y-axis ticks, uses very small type, and has unsupported glyphs in several labels. Other maps lack a calibrated colorbar, and the ratio maps need a low-signal mask. For shared figures, use readable typography, labeled axes/colorbars, units, physical coordinates, clear normalization, and uncertainty. Generate reports and tables from the same frozen data so that manually added narrative does not drift outside manifests.

**Recommended order of work.** Each step has a concrete completion condition:

1. **Freeze the current research state.** Preserve the recoverable historical analyzer; commit reviewed new code and compact artifacts; add the current/superseded scenario inventory and restore instructions. Completion: a fresh checkout identifies the correct current comparisons and resolves every recorded analysis entry point.
2. **Harden the shared boundaries.** Enforce engine identity, source transforms, optical validation, supported grids/source models, and immutable outputs. Completion: the reproduced negative cases fail clearly and the full software suite is green without falsifying historical provenance.
3. **Qualify the comparison.** Run a focused two-wavelength convergence audit for whole-tissue, depth-shell, and ratio endpoints. Prioritize paired superficial-tissue/brain optical scenarios and the uncertainties already shown to matter. Completion: every headline comparison has explicit Monte Carlo and parameter-uncertainty qualifications.
4. **Resolve the device model.** Obtain the necessary source-model inputs, register assembled source geometry, obtain spectral source weights and beam/coupling evidence, and prepare a separately versioned device pilot. Completion: positions, normals, powers, and launch boundary are reviewable and tied to a specific unit/revision.
5. **Complete the useful endpoints and reporting.** Generate corrected-1070 overlap results, validated cortical/target ROI summaries, and consistent comparative figures. Completion: each conclusion links to a reproducible result and distinguishes transport prediction from device validation.

The strongest asset is the substantial, traceable simulation work already completed. The main opportunity is to make its present conclusions easier to reproduce and harder to overinterpret, then connect that workflow to the actual helmet with validated inputs.
