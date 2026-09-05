# Current research state — 4 September 2026

Use this page to select a scenario. The original plan and older reports remain historical records. The current research is a **277-source Yue-derived surrogate**, with conditional optical properties and 1-mm anatomy. It is not a simulation of the actual target device.

## Controlling comparisons

| Role | Artifact | Interpretation |
|---|---|---|
| Current provisional 1070 comparator | `inputs/fat_absorption_bracket_v1/fat_abs_010.json`; `runs/surrogate_yue277_1070_windows_rtx3080ti_fat_abs_010_basis_v1/index.json` | Effective-adipose absorption 0.010 mm^-1; one realization per source in the original basis |
| Current provisional 810 comparator | `inputs/optical_properties/provisional_810_v2/central_refined_primary.json`; `runs/surrogate_yue277_810_windows_rtx3080ti_opencl_basis_v3/index.json` | Refined provisional optical table; same 277-source spatial layout |
| Fat sensitivity alternatives | `results/surrogate_yue277_1070_fat_absorption_bracket_v1/` | 0.005065 and 0.030 mm^-1 bracket the selected 0.010 comparator; scenario variation is not a confidence interval |
| Water counterfactual | `results/surrogate_yue277_1070_water_counterfactual_v1/` | Substitutes the 810 water term while retaining other 1070 assumptions; not a physical full-810 model |
| Historical high-fat 1070 | `results/surrogate_yue277_1070_windows_rtx3080ti_opencl_analysis_v1/` | Original 0.103 mm^-1 fat scenario, retained for history and sensitivity; do not use as the corrected comparator |
| Corrected 1070 overlap | `results/corrected_1070_overlap_20260904_v1/` | Recomputed from existing corrected-fat native fields; whole GM/WM masks, not a cortical ribbon |
| Endpoint Monte Carlo audit | `results/two_wavelength_mc_audit_20260904_v1/` | Three independent seeds at two aggregate photon counts and two time windows; see `results/surrogate_yue277_810_vs_1070_regional_absorbed_energy_v2/report.md` for pass/fail by endpoint |

`provenance/scenario_inventory_20260904_v1.json` inventories all discovered basis indices and their statuses. Failed, planned and historical records remain available.

The saved equal-total-launch bases give brain absorption of **1.21425% at corrected 1070** and **1.13355% at refined 810**. Integrated brain fluence is about **2.32 times higher at 810**, while total brain absorption is about **6.65% lower**. These are different observables. Neither establishes a robust wavelength winner, device dose, safety, heating, or efficacy.

The completed 18-run audit qualifies **18 of 21 endpoint ratios**. All three ratios at depths >=50 mm fail the declared screening criteria and are suppressed. The high-count mean brain absorption is **1.13394% at 810** and **1.21453% at 1070**; this supports the saved comparison under the fixed assumptions. Read [the qualified comparison](results/review_comparison_public_20260905_v1/report.md) and [the revised regional report](results/surrogate_yue277_810_vs_1070_regional_absorbed_energy_v2/report.md).

## Qualification and unresolved science

- The new audit tests conditional Monte Carlo variation and selected numerical stability. Its three-replicate Student-t intervals do not include uncertain optical properties, segmentation, source placement or device coupling. Photon counts in the direct audit are total across all emitters, unlike the per-emitter basis count.
- The old regional report's 1,054-fold deepest-WM ratio is a historical unqualified point estimate. Use the new audit's endpoint gates and absolute deposition; a suppressed ratio must not be presented as a reliable effect. No voxelwise confidence map has been established.
- Whole GM, whole WM, their union and geometric head-depth shells are implemented. Validated cortical-ribbon and named target-region masks remain absent. Depth shells are not anatomical parcellations.
- The Yue 40/60-mm quantitative reproduction still fails its declared tolerance. Shape agreement and internal aggregate equivalence do not convert that external benchmark to a pass.
- The production optical ledger still has unresolved cells. Current tables are provisional scenarios. Additional parameter ensembles should be tied to endpoint outcomes before declaring parameter-robust conclusions.

## Device information

Device-specific information is omitted from this publication copy.

## Reproducibility and execution

The reviewed workspace was preserved in commit `e183ac4f` on `codex/review-hardening-20260904`. `.gitattributes` retains exact bytes across platforms, because historical checksums cover line endings too. Historical analyzer snapshots retain the hashes actually recorded; historical result hashes were not replaced.

The shared analyzer now takes explicit settings and records entrypoint, settings, shared modules, source snapshots, package versions and lock hash. The original 810 wrapper and omitted-code historical analyses have recovery supplements in `provenance/`; recovered workspace code is distinguished from contemporaneous generation proof.

New generic basis execution requires the declared executable SHA-256, release identity and selected GPU to agree before launch and after execution. Existing completed records can still be verified. Old plans without a binary hash require a newly versioned binding before new execution. Sources are transformed into the voxel frame consistently; current adapters require 1-mm orthogonal grids and pencil sources. Unsupported beam types fail explicitly.

For setup use Python 3.13 and `uv sync --frozen --group dev`. On Windows set `UV_PROJECT_ENVIRONMENT=.venv-win`. The Windows preflight now enforces this lock. CI runs portable software checks; the full local suite also validates saved research artifacts. The GitHub Actions workflow checks this portable suite on pushes and pull requests.

See `provenance/RESTORE.md` for recovering code and large artifacts. No independent off-machine archive location has been supplied or verified.
