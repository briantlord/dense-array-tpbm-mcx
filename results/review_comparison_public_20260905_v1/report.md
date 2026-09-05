# Qualified wavelength comparison — 4 September 2026

This audit independently samples the same 277-source equal-total-launch surrogate at refined 810 nm and corrected-fat 1070 nm. It checks numerical variation under fixed model assumptions; it does not validate target-device hardware or establish clinical effects.

## Whole-tissue absorption

Values are percentages of total launched energy. Brackets are marginal 95% Student-t intervals for the mean of three independent high-count simulations.

| Tissue | 810 mean [interval] | 1070 mean [interval] | Qualified 810/1070 |
|---|---:|---:|---:|
| gray_matter | 0.82725% [0.82617, 0.82834] | 1.17787% [1.17767, 1.17806] | 0.7023x |
| white_matter | 0.30669% [0.30652, 0.30685] | 0.03666% [0.03663, 0.03670] | 8.365x |
| brain | 1.13394% [1.13281, 1.13506] | 1.21453% [1.21437, 1.21469] | 0.9336x |

## Depth endpoints and signal qualification

Absolute values below are joules absorbed per 100 J total launched. A missing ratio is a failed reporting gate, not zero absorption or equal wavelengths. These depth shells are geometric distances to exterior-connected background, not named target regions.

| Endpoint | 810 J/100 J | 1070 J/100 J | 810/1070 | Failed gates |
|---|---:|---:|---:|---|
| brain__depth_0_10_mm | 1.1600e-02 | 1.0200e-02 | 1.14x | none |
| brain__depth_10_20_mm | 5.0680e-01 | 8.3245e-01 | 0.609x | none |
| brain__depth_20_30_mm | 5.7586e-01 | 3.6418e-01 | 1.58x | none |
| brain__depth_30_40_mm | 3.7710e-02 | 7.5843e-03 | 4.97x | none |
| brain__depth_40_50_mm | 1.8296e-03 | 1.1723e-04 | 15.6x | none |
| brain__depth_50_inf_mm | 1.4095e-04 | 2.9206e-06 | not qualified | 1070: replicate_cv |
| gray_matter__depth_0_10_mm | 1.0194e-02 | 1.0123e-02 | 1.01x | none |
| gray_matter__depth_10_20_mm | 4.4465e-01 | 8.2067e-01 | 0.542x | none |
| gray_matter__depth_20_30_mm | 3.5171e-01 | 3.4032e-01 | 1.03x | none |
| gray_matter__depth_30_40_mm | 1.9516e-02 | 6.6473e-03 | 2.94x | none |
| gray_matter__depth_40_50_mm | 1.0703e-03 | 9.5496e-05 | 11.2x | none |
| gray_matter__depth_50_inf_mm | 1.1709e-04 | 2.8995e-06 | not qualified | 1070: replicate_cv |
| white_matter__depth_0_10_mm | 1.4060e-03 | 7.7345e-05 | 18.2x | none |
| white_matter__depth_10_20_mm | 6.2150e-02 | 1.1774e-02 | 5.28x | none |
| white_matter__depth_20_30_mm | 2.2415e-01 | 2.3854e-02 | 9.4x | none |
| white_matter__depth_30_40_mm | 1.8194e-02 | 9.3700e-04 | 19.4x | none |
| white_matter__depth_40_50_mm | 7.5928e-04 | 2.1730e-05 | 34.9x | none |
| white_matter__depth_50_inf_mm | 2.3864e-05 | 2.1131e-08 | not qualified | 1070: minimum_signal; 1070: photon_count_stability; 1070: replicate_cv |

## Audit design and limits

- Eighteen direct aggregate runs: two wavelengths, three independent seeds, 27.7 million versus 277 million total photons, then 277 million at a 10-ns rather than 5-ns window. Counts are total across 277 emitters, not per emitter.
- Frozen screening criteria: absorbed fraction at least 1e-8; replicate CV at most 5%; mean interval excluding zero; at most 10% mean change with photon count, time window, and relative to the saved basis. The engineering signal threshold is not a biological threshold.
- Criteria were frozen before these runs, after seeing the earlier review. They are a bounded numerical screen, not an independently preregistered hypothesis test. Three replicates provide limited interval precision and normality evidence.
- Ratios use independently sampled wavelength means. Ranges saved in JSON are constructed from separate marginal mean intervals, not joint 95% ratio confidence intervals. No multiple-endpoint coverage guarantee is asserted.
- Optical, segmentation, source and coupling uncertainty is excluded. The established fat sensitivity and water counterfactual remain controlling evidence that parameter assumptions matter. Formal parameter-uncertainty intervals are still absent.
- ROI qualification does not qualify individual voxels. The revised regional report suppresses voxel ratio maps. The old 1,054-fold deepest-white-matter value remains an unqualified historical point estimate.

## Corrected overlap comparison

These are field-first summaries from the existing per-emitter bases. They describe source contribution overlap within whole tissue masks; they are not cortical coverage or uncertainty-qualified spatial targeting metrics.

| Tissue | 1070 EF_dom | 810 EF_dom | 1070 N_eff | 810 N_eff |
|---|---:|---:|---:|---:|
| gray_matter | 115.383 | 84.015 | 239.452 | 213.821 |
| white_matter | 46.990 | 86.157 | 151.104 | 217.383 |
| brain_total | 115.997 | 85.858 | 239.966 | 216.426 |

The corrected-1070 analysis reverified all 277 native fields and reproduces the saved corrected-fat aggregate exactly. Historical high-fat overlap maps are not used in this matched table.

## Device and remaining evidence

Device-specific details are omitted. A device pilot needs measured source geometry, spectral weights, beam profile, and coupling evidence. The quantitative external benchmark and production optical gates remain unresolved.
