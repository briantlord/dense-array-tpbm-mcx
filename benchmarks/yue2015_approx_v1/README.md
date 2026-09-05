# Yue 2015 approximation v1

This directory defines the executable 850-nm benchmark approximation. It is not an exact reconstruction of the unpublished MCXLAB configuration.

## Frozen reported inputs

- 850 nm;
- the five `mua` and reduced-scattering rows from Table 2, in `mm^-1`;
- 1-mm Colin27 anatomy;
- the Table-1 layer elevations and counts totaling 277 sources;
- inward source axes, unit initial source weight, and `10^9` photons per source for the eventual paper-scale comparison;
- density counts 13, 53, 105, 181, 229, and 277.

## Declared project approximations

- `colin27_2008_yue5_1mm_v1` is derived from the accepted native-label atlas, not the paper's unavailable SPM12 segmentation.
- Native vessels are assigned spatially to the nearest non-vessel tissue; they are not globally mapped to scalp or brain.
- Every elevation ring begins at zero azimuth because the paper omits per-ring phase.
- Lower-density tiers are deterministic nested farthest-point subsets seeded at the north pole because their coordinates are not reported.
- The executable comparison uses a zero-width pencil source. The paper's Gaussian width is not reported; Figure 4's enhancement ratio is explicitly the pencil comparison.
- The paper reports reduced scattering and an isotropic assumption. This implementation sets `g=0` and therefore `mus=musp`.
- The paper says approximate refractive indices were used but does not give them. Version 1 sets every `n=1.0` to remove an otherwise arbitrary boundary mismatch. Refractive-index sensitivity remains required.
- The output contract is MCX normalized fluence. This is deliberately distinguished from the paper's deposited photon weight, which it calls photon flux.

## Rebuild and validate

The official Colin27 source and accepted native derivative must already exist locally. Then run:

```bash
.venv/bin/python scripts/build_yue2015_approx_v1.py
.venv/bin/mcx-project preflight \
  benchmarks/yue2015_approx_v1/template_manifest.json \
  --project-root .
```

The ignored five-tissue NIfTI is reconstructed locally. Tracked outputs include its metadata, derivation transitions, compact QC, the 277-source geometry and visualization, nested density tiers, optical table, calibration convention, registration, base MCX configuration, and manifest.

`configs/yue2015_approx_v1_basis_plan.json` defines the original 277 independent, unit-source, one-billion-photon pencil plan. Do not launch that file unchanged: it predates the corrected convergence decision. The v2 result selects `10^8` photons per source as the minimum passing representative candidate for the first multisource benchmark comparison.

## Current validation boundary

The frozen protocol is `configs/yue2015_convergence_acceptance_v1.json`. Compact results are retained at three levels:

- `convergence_pilot_m4_v1/`: `10^5` through `10^7` photons;
- `convergence_representative_m4_v1/`: adds `10^8` photons;
- `convergence_paperscale_m4_v1/`: adds `10^9` photons and is the controlling representative result.

The v1 analyses are invalid because JData column-major fields were decoded as row-major; see `convergence_axis_order_invalidation_2026-08-14.md`. The corrected `convergence_paperscale_m4_v2/` sequence reran three independent seeds at every tier from `10^5` through `10^9`. Both final transitions pass all frozen thresholds. At `10^8`, the maximum tissue-integral CV is 0.098%, median profile CV is 1.28%, and the `10^7`-to-`10^8` median profile change is 2.23%. At `10^9`, those values are 0.023%, 0.67%, and 0.70% relative to `10^8`. The versioned decision records `10^8` photons per source as the minimum passing representative candidate. None of these representative runs alone reproduces the multisource Yue curves or passes the benchmark gate.

The prespecified figure targets are digitized in `literature/yue2015_figure_digitization_v1.csv`, with calibration/provenance in `digitization_manifest_v1.json`. The 39-point ledger covers the five regional Figure 2b profiles at 60 mm, Figure 4's 850-nm pencil gain curve, all six Figure 5a density gains at 60 mm, Figure 5b uniformity including the one-source reference, and Figure 6c's 690-nm gain curve. It is a single-operator two-pass extraction, not author-supplied numerical data.

The complete `yue2015_850_277_pencil_basis_v2` basis contains 277 checksum-locked fields at `10^8` photons per source. `multisource_1e8_v2/` records the five regional single-source curves, all density-tier total-field curves, the 277-source regional total curves, north-pole `EF_ref`, explicit-mask uniformity alternatives, plots, and the discrepancy report. A direct two-source `2 x 10^8`-photon MCX-CL run independently validates linear aggregation in `aggregate_equivalence_v1/result.json`: maximum tissue-integral error is 0.0275%, median 20-to-60-mm axis-profile error is 1.56%, and median valid-voxel error is 0.89%; all frozen components pass.

The multisource comparison passes the frozen Figure-4 profile-shape target (`Spearman r=0.964`) and increasing-density ordering, but fails the 25% quantitative headline gate. At 40 mm, modeled `EF_ref=23.1` versus the digitized Yue value 7.78; at 60 mm, modeled `EF_ref=22.4` versus 15.6. The paper's exact uniformity scalar cannot be reconstructed because its spatial mask is not reported; whole-head and intracranial raw-field alternatives decrease monotonically, while the declared shell and five-axis alternatives do not. The benchmark implementation and discrepancy report are complete, but the scientific benchmark gate is **not passed** for this approximation.

## Post hoc discrepancy diagnosis and milestone decision

The frozen v1 outcome above is not changed. A separately versioned north-pole sensitivity study in `single_source_segmentation_sensitivity_v1/` then held the source, Yue optical table, MCX build, photon count, and three seeds fixed while perturbing only tissue boundaries or the reported observable. It showed that MCX energy output agrees with `mua * fluence` after one global unit scale, and that modest local boundary changes alter the 60-mm single-source signal by roughly 1.5x to 2.0x. A deliberately aggressive global CSF perturbation changes it by 25.9x, demonstrating that segmentation can dominate deep single-source magnitude. A combined explanatory bound reaches 72.2% of the digitized Yue value in the absorbed-energy comparison, without claiming that Yue used those boundaries.

For the multisource result, the 181-source modeled total at 60 mm is within about 3% of the digitized Yue total while the reference-source denominator remains substantially smaller. The excess `EF_ref` is therefore primarily a denominator/observable/anatomy-identifiability problem, not evidence that linear superposition or the MCX implementation failed. Because the paper omits the exact SPM segmentation, plotted output definition/normalization, and several source details, exact numerical reproduction is not identifiable from the publication. The software-validation milestone is closed as complete; the original prespecified 25% external-reproduction criterion remains a recorded failure and is not retroactively redefined as a pass.
