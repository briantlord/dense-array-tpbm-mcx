# Yue and Humayun (2015) Benchmark Ledger

**Primary source:** Yue, L., & Humayun, M. S. (2015). *Monte Carlo analysis of the enhanced transcranial penetration using distributed near-infrared emitter array*. Journal of Biomedical Optics, 20(8), 088001. DOI `10.1117/1.JBO.20.8.088001`.  
**Local source:** `references/papers/Yue_Humayun_2015_distributed_NIR_emitter_array.pdf`  
**Audit date:** 2026-08-13  
**Machine-readable ledger:** `benchmarks/yue_2015_parameter_ledger.csv`

## Outcome

The paper is sufficient for a **Yue-style qualitative and semi-quantitative benchmark**, but not for a bitwise or uniquely specified numerical reproduction. The source-density series, tissue table, photon count, source-axis comparison, and headline trends are reported. The exact MCXLAB release, random seeds, convergence, boundary settings, Gaussian beam parameters, precise low-density coordinates, and numerical figure data are not.

The implementation must be named as an approximation, for example `yue2015_approx_v1`, and every project-selected value must be separated from a value reported by the paper.

## Status vocabulary

- **reported:** explicitly present in the paper;
- **inferred:** a strong interpretation, not directly specified;
- **missing:** needed for reproduction but not reported;
- **inconsistent:** two parts of the paper cannot both be applied literally;
- **project decision:** a value or rule that must be frozen by this project before running.

## Reproduction target

### Anatomy and coordinate handling

- Colin27, 1 x 1 x 1 mm voxels, segmented with SPM12 into scalp, skull, modified CSF, gray matter, and white matter.
- The paper gives the original head center as `(111.5, 91, 30)` in its Cartesian coordinates.
- The head is translated to the origin and rotated 0.09 rad counterclockwise about the y-axis so the approximate hemispherical brain equator lies in the x-y plane.
- Source directions point inward along the spherical normal toward the head center.

The Colin27 release/checksum, the actual segmentation volume, the filtering command, and the SPM12 release are not supplied. A benchmark anatomy cannot be frozen until those choices are recorded.

### Source layout

The maximum-density table resolves to 277 sources across 11 elevation layers:

| Elevation theta (rad) | Sources | Actual delta-phi (rad) | Actual delta-omega |
|---:|---:|---:|---:|
| 0.000 | 40 | 0.157 | 0.025 |
| 0.157 | 40 | 0.157 | 0.024 |
| 0.314 | 36 | 0.175 | 0.026 |
| 0.471 | 36 | 0.175 | 0.024 |
| 0.628 | 32 | 0.196 | 0.025 |
| 0.785 | 28 | 0.224 | 0.025 |
| 0.942 | 24 | 0.262 | 0.024 |
| 1.100 | 20 | 0.314 | 0.022 |
| 1.257 | 12 | 0.524 | 0.025 |
| 1.414 | 8 | 0.785 | 0.019 |
| 1.571 | 1 | n/a | n/a |

The table implies an elevation step of approximately 0.157 rad, while the prose says “a 0.05 radian elevation grid.” These cannot both be literal. Use the tabulated elevations for `yue2015_approx_v1`, label the prose value as an internal inconsistency, and test any alternative only as a sensitivity.

For reduced densities, the paper reports counts and aggregate spacing statistics but not complete coordinate lists:

| Source count | Weighted average delta-omega | SD | SD / average |
|---:|---:|---:|---:|
| 277 | 2.45e-2 | 1.23e-3 | 5.03% |
| 229 | 2.99e-2 | 1.67e-3 | 5.57% |
| 181 | 3.82e-2 | 2.61e-3 | 6.82% |
| 105 | 6.80e-2 | 4.80e-3 | 7.06% |
| 53 | 1.43e-1 | 1.17e-2 | 8.16% |
| 13 | 7.02e-1 | 1.20e-1 | 17.16% |

The project must define and retain the deterministic coordinate-generation/rounding rule for every lower-density tier. Matching count and mean solid angle alone does not prove the same layout.

### Optical table reported by the paper

All coefficients are in `mm^-1`. The scattering column is reduced scattering, `musp`, not `mus`.

| Tissue | mua 850 | musp 850 | mua 690 | musp 690 |
|---|---:|---:|---:|---:|
| scalp | 0.012 | 1.8 | 0.021 | 2.37 |
| skull | 0.025 | 1.6 | 0.026 | 2.35 |
| modified CSF | 0.003 | 0.01 | 0.0004 | 0.01 |
| gray matter | 0.036 | 0.9 | 0.036 | 1.4 |
| white matter | 0.014 | 1.1 | 0.014 | 1.5 |

The paper states that approximate refractive indices were assigned, but does not report their values. It also says the reduced scattering coefficient accounts for anisotropy in an isotropic assumption. A likely implementation is `mus = musp` with `g = 0`, but that is an inference and must not be presented as reported. The cited optical-property papers remain an independent provenance task.

### Monte Carlo source and normalization

- MCXLAB under MATLAB; exact release and configuration absent.
- 850 nm is the default; 690 nm is the shorter-wavelength comparison.
- `10^9` photons per source, initially unit weight.
- Sources are called point sources, directed inward; Gaussian beam is the default and pencil beam is a comparison.
- No Gaussian width, waist, focus, divergence, or MCXLAB source-parameter vector is reported.
- The algorithm description accumulates photon weight lost to absorption in each voxel and calls the result “photon flux.” That wording is not a standard unit definition and does not uniquely identify an MCX output field.
- Multisource fields are formed by superimposing single-source fields.
- The Monte Carlo boundary behavior, time gate/stopping threshold, roulette settings, seeds, repeats, and convergence evidence are absent.

The benchmark must save both an explicitly named MCX fluence output and any absorbed/deposited-weight field used to mimic the paper. It must not label either “photon flux” without a unit/normalization definition.

## Comparison definitions and targets

### Single-source location check

The paper compares five single sources: frontal, occipital, temporal, parietal, and north pole. Four are described as randomly placed; no coordinates are given. The north-pole source is the only uniquely reconstructable comparison location.

### Reference-source enhancement

The reported gain is:

`EF_ref(depth) = total multisource field on the north-pole source axis / north-pole single-source field on the same axis`.

It is not `EF_dom`. Figure 4's plotted gain is specifically described as the pencil-beam multisource/single-source ratio even though Gaussian is the paper's default elsewhere. The project must reproduce and label the paper's denominator before comparing `EF_dom`.

Headline 277-source trends reported in prose:

- robust enhancement begins around 20 mm depth;
- approximately 5x at 40 mm, 10x at 60 mm, and greater than 40x at 100 mm for 850 nm;
- a later wavelength comparison describes the 850-nm gain at 40 mm as approximately 6x, showing that these are approximate readouts rather than exact tabulated targets;
- exponential fit parameter `tau = 34.7 +/- 2.9 mm^-1`, `R^2 = 0.995` for 850 nm;
- `tau = 20.0 +/- 1.4 mm^-1`, `R^2 = 0.993` for 690 nm.

The reported `tau` unit is dimensionally questionable for a length-scale parameter in an exponential function. Preserve the paper's label in the ledger, inspect the fitted equation during digitization, and do not hard-code the unit as physically correct.

### Density and uniformity targets

- At 60 mm, increasing from 105 to 181 sources raises gain from about 5x to 10x; further increases show diminishing returns.
- The paper recommends 181 idealized point sources as a balance of field and system complexity, while warning that finite emitters may require lower density.
- Uniformity is `SD(photon flux) / mean(photon flux)` and decreases with source count.

The spatial sampling domain/mask for the uniformity curve is not specified sufficiently for exact reproduction. Treat its direction and source-count ordering as the primary target unless figure digitization and code inspection resolve the domain.

## Benchmark acceptance strategy

Before final runs:

1. obtain and checksum a Colin27 volume and document the segmentation approximation;
2. freeze the Table-1-based 277-source generator and deterministic lower-density subset rule;
3. freeze two source-model scenarios: a declared Gaussian approximation and a pencil-beam comparison;
4. freeze the MCX output quantity and conversion used for each comparison;
5. run independent-seed photon-count convergence rather than assuming `10^9` is sufficient;
6. digitize Figures 2b, 4, 5a, 5b, and 6c with stored calibration points and digitization uncertainty;
7. freeze numerical tolerances before examining the final reproduced curves; and
8. write a discrepancy report that separates anatomy, source, output-definition, digitization, and stochastic effects.

Minimum acceptable reproduction is:

- correct qualitative depth attenuation for the five source regions;
- monotonic enhancement with depth for the 277-source/reference-source comparison;
- correct source-density ordering and diminishing returns near/above 181 sources;
- decreasing relative-SD trend with source count; and
- explicitly quantified mismatch at digitized depths, without tuning 1070-nm production inputs to force agreement.

## Known blockers to exact reproduction

- MCXLAB version/configuration and executable behavior;
- Colin27 file/release, filtering details, and exact SPM12 segmentation;
- complete source coordinates, especially reduced-density tiers and the four regional comparison sources;
- the prose/table elevation-grid inconsistency;
- Gaussian beam parameters and the point-source/Gaussian terminology conflict;
- refractive indices and exact `g` handling;
- boundary and termination settings;
- random seeds, replicates, convergence, and uncertainty;
- unambiguous output quantity and physical normalization;
- numeric data underlying figures and precise uniformity mask;
- code and any supplementary data, none identified in the supplied PDF.

