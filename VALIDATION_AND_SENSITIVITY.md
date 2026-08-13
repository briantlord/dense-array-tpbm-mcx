# Validation and Sensitivity Plan

## Purpose

Validation is staged. Passing a software or literature benchmark does not validate the physical helmet, a human intracranial dose, or a biological effect. Each result must state the highest validation level it has reached.

## Validation hierarchy

| Level | Question answered | Minimum evidence |
|---|---|---|
| V0 — schema/static | Are inputs complete, typed, unit-consistent, and traceable? | Automated schema, range, checksum, and provenance tests |
| V1 — numerical/software | Does orchestration preserve MCX normalization, geometry, and linear sums? | Analytic/synthetic cases, conservation diagnostics, unit tests, repeat runs |
| V2 — published computational benchmark | Does the implementation recover known dense-array behavior? | Yue-and-Humayun-style 850-nm reproduction with discrepancy report |
| V3 — phantom | Does the modeled source/tissue system predict measured optical fields in controlled media? | Calibrated 1070-nm phantom measurements with uncertainty |
| V4 — layered/ex vivo | Does it predict transmission through anatomically relevant layers? | Scalp/skull or validated layered-tissue comparison |
| V5 — in vivo optical | Does it predict measurements in living heads? | Appropriate human/animal optical measurement and preregistered comparison |
| V6 — thermal/biological | Does optical deposition predict temperature or biological response? | Separate coupled model and experiment; outside version-1 scope |

Version 1 targets V2. V3–V6 are future experimental work unless suitable data become available.

## 1. Yue-and-Humayun-style 850-nm benchmark

### Aim

Test the complete anatomy–source–MCX–superposition–analysis path against the foundational dense distributed-array study rather than assuming that MCX installation alone establishes correctness.

### Reproduction target

- use the same or closest documented head model, tissue classes, wavelength, source model, source locations/densities, power normalization, and sampled axes/ROIs;
- implement the reported emitter counts, including the maximum 277-source case, only after verifying exact values and layout from the paper/supplement;
- run each source independently and superimpose its normalized field;
- reproduce the paper's single-source and multisource definitions, including its reference-source denominator;
- digitize figures only when numerical tables/data are unavailable, recording software and digitization uncertainty.

### Prespecified benchmark outputs

- fluence/photon-density-versus-depth curve for the reference single source;
- total multisource curve along the same line/axis;
- reference-source enhancement versus depth;
- enhancement versus source density at prespecified depths;
- spatial uniformity or field maps when sufficiently specified.

### Acceptance criteria

Before reading the reproduced headline values, freeze tolerances for:

- relative error or confidence-interval overlap at selected depths;
- shape agreement across the complete depth profile;
- ordering and qualitative trend across source densities;
- spatial correspondence after accounting for resolution and coordinate definitions.

Initial engineering targets may be recorded as provisional, but final tolerances must reflect digitization error and irreducible method differences. A failed exact reproduction is still useful if discrepancies are traced to unavailable source geometry, optical tables, atlas version, normalization, or stochastic uncertainty. Do not tune 1070-nm inputs to force an 850-nm match.

## 2. Numerical and convergence testing

### Photon-count sequence

For representative sources and the aggregate field, run a log-spaced sequence such as `10^6, 10^7, 10^8`, and if needed `10^9` photon packets per source. These are candidates, not a predetermined sufficient count.

Include emitters over frontal, temporal, parietal, and occipital regions and at least one source with oblique incidence or unfavorable standoff.

### Replicates

- use multiple independent seeds at each selected count;
- compare voxelwise fields only after masking regions below the noise/analysis threshold;
- focus primary convergence judgments on cortical and ROI integrals, percentiles, `EF`, `NCF`, and `N_eff`;
- estimate Monte Carlo coefficient of variation or confidence intervals from repeats.

### Convergence decision

Freeze a production photon count when increasing the count produces changes smaller than prespecified tolerances for every primary cortical endpoint and no material spatial artifact remains. Example tolerances must be set in a versioned protocol before final runs; no universal percentage is assumed here.

### Additional numerical checks

- identical configuration and seed reproduces output within the engine's deterministic limits;
- independent seeds are not accidentally reused across sources;
- normalized per-source sums agree with an aggregate-source test within Monte Carlo uncertainty;
- scaling all source weights by a constant scales total fluence linearly;
- setting all but one weight to zero recovers that basis field;
- source permutation leaves aggregate and symmetric metrics unchanged;
- chunked aggregation agrees with a high-precision synthetic reference;
- `1 <= N_eff <= N_enabled`, `0 <= NCF < 1`, and `EF_dom >= 1` wherever defined.

## 3. Optical-property sensitivity

### Inputs

Construct low/nominal/high or probabilistic scenarios only from the provenance ledger. Sensitivity bounds should reflect source disagreement, reported uncertainty, spectral-interpolation uncertainty, and tissue-definition mismatch—not an automatic percentage chosen for convenience.

At minimum vary:

- `mua` by tissue;
- `musp` or `mus` with `g` handled consistently;
- `g` where independently uncertain;
- refractive index and boundary mismatch in a secondary analysis;
- skull representation (single versus compact/spongy layers) if supported;
- CSF optical values and segmentation thickness;
- correlated property sets as well as one-at-a-time changes.

### Design

Use three layers:

1. one-at-a-time perturbations for interpretability;
2. grouped plausible literature scenarios to preserve correlated assumptions;
3. global sampling (for example Latin hypercube or Sobol design) if parameter ranges and compute permit.

Report sensitivity of absolute cortical fields separately from overlap metrics. Ratios can appear stable while absolute dose changes substantially.

## 4. Geometry and registration sensitivity

Vary parameters that could plausibly differ between CAD, bench, and worn configurations:

- global helmet translation and rotation based on landmark residuals;
- head-size fit or a documented helmet adjustment mechanism;
- source-to-scalp standoff;
- optical-axis angular error;
- emitter position error;
- emitting aperture and angular profile;
- missing, low-output, or failed sources;
- heterogeneous source output/calibration error;
- ideal contact versus documented coupling attenuation;
- optional hair attenuation scenarios only when a defensible model exists.

Perturbations should be tied to measurement uncertainty or realistic donning variability. Include a worst-plausible registration case and display source/scalp QC for all extremes.

Primary geometry outcomes:

- change in cortical mean/median and coverage;
- spatial displacement of high-fluence regions;
- change in ROI ranking;
- change in `EF_dom`, `NCF`, and `N_eff`;
- fraction of sources whose rays miss or graze the scalp.

## 5. Source-density sweep

### Candidate counts

Use the verified benchmark counts for the 850-nm reproduction. For the approximately 288-source helmet, candidate nested counts are:

`18, 36, 72, 144, 288`.

The exact sequence may change to preserve the physical wiring/layout and final verified source count.

### Subset construction

- use spatially balanced, nested subsets so every lower-density set is contained in the next;
- predefine the selection algorithm (for example farthest-point sampling on the helmet surface) and seed;
- include multiple balanced subsets at a given count when selection variability may matter;
- compare at least two power constraints:
  - **constant per-emitter output**, where total launched power grows with count;
  - **constant total output**, where power is redistributed across enabled emitters.

These answer different engineering questions and must not be mixed.

### Density outcomes

- total and ROI fluence/absorbed energy;
- cortical coverage above declared absolute or relative thresholds;
- spatial uniformity;
- `EF_dom`, `NCF`, and `N_eff` distributions;
- marginal gain from adding a density tier;
- diminishing returns under both power constraints.

Avoid interpreting diminished marginal gain as an intrinsic optimum without considering scalp irradiance, thermal constraints, power budget, and helmet geometry.

## 6. Wavelength comparison

The benchmark is at approximately 850 nm and the target is 1070 nm. A direct wavelength comparison is permitted only when geometry, source normalization, property provenance, and output definitions are harmonized. It should show both:

- absolute modeled optical quantities under clearly stated source power assumptions; and
- overlap metrics that reduce but do not eliminate dependence on absolute output.

Do not describe any difference as a biological advantage without a separate action-spectrum and dose-response model.

## 7. Analysis robustness

- define cortical and ROI masks before final results;
- report both field-first and metric-first ROI aggregation;
- test alternative near-zero thresholds for ratio maps;
- compare nearest-by-distance source, source-axis intersection, and dominant-by-contribution labels without conflating them;
- quantify rank stability of top contributors across sensitivities;
- retain unthresholded numeric outputs even when visualizations are masked;
- correct for no multiplicity only if analyses are descriptive; any inferential claims need a separate statistical plan.

## 8. Reporting matrix

Every headline result should be labeled with:

- validation level (V0–V6);
- nominal versus sensitivity scenario;
- anatomy and helmet version;
- wavelength and source-power constraint;
- metric definition/denominator;
- Monte Carlo uncertainty;
- parameter uncertainty or scenario range;
- whether it is a modeled quantity, measured quantity, or derived comparison.

## 9. Stop conditions

Stop and repair before interpreting results if:

- any production optical parameter lacks provenance or has ambiguous `mus`/`musp` units;
- registration produces source collisions, outward-pointing normals, or undocumented standoffs;
- benchmark disagreement is large and unexplained;
- deep/cortical fields do not converge at feasible photon counts;
- aggregate and independent-source superposition disagree beyond stochastic tolerance;
- headline ratio maps are dominated by near-zero denominators;
- sensitivity scenarios reverse the main conclusion without that uncertainty being centered in the report.
