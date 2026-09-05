# 1070-nm Optical-Property Audit

**Ledger:** `colin27_native12_1070_source_ledger_v1`  
**Target:** 1070.0 nm, coefficients in mm^-1  
**Anatomy:** `colin27_2008_native12_1mm_v3`  
**Status:** scientifically blocked; Priority 1 sources acquired and transcribed
**Machine-readable evidence:** `literature/optical_properties_1070_source_ledger.json`  
**Neighboring-wavelength implementation precedent:** `literature/cassano_2019_1064_table1_transcription.csv`

## Result

The search did not yield a complete, mutually consistent, primary-source tuple of `mua`, `mus` or `musp`, `g`, and `n` at 1070 nm for all 12 Colin27 labels. The production table therefore remains all `TBD` for optical quantities. That is the intended outcome of the gate, not a software failure.

Several components are already strong enough to preserve as numerical candidates:

- Shapey et al. Table S1 revised `mua` and model-fitted `musp` at exactly 1070 nm: gray matter `0.08892 / 2.0896383631 mm^-1`, white matter `0.04040 / 7.1437578099 mm^-1`, and dura `0.07021 / 2.2915790502 mm^-1`. The workbook contains means, not numerical SD columns.
- Human adipose reduced scattering from Bashkatov et al.'s spectral model: `musp(1070) = 0.9150744461 mm^-1`.
- Human skin reduced scattering from the same source: `musp(1070) = 1.6724764029 mm^-1`. The Colin27 class is `skin_and_muscles`, however, so the pure-skin value cannot be assigned directly.
- Human cortical cranial-bone reduced scattering from Bashkatov et al.'s 800-1100-nm model: `musp(1070) = 1.6460702479 mm^-1`.
- Reproducibly digitized 1070-nm central absorption estimates are `0.0157 mm^-1` for skin, `0.103 mm^-1` for adipose, and `0.0167 mm^-1` for cortical cranial bone. These are graph-derived sensitivity candidates, not table-exact values.
- Roggan et al. Figure 13 yields state-specific diluted-blood estimates at hct 5%, 20 C, and shear 500 s^-1: `mua=0.259 mm^-1` at 100% oxygen saturation, `mua=0.190 mm^-1` at 0% saturation, `mus=19.85 mm^-1`, and `g=0.9859`. The earlier curve-state transcription was reversed and has been corrected. These are not physiological-haematocrit whole-blood defaults.
- Friebel et al. (2006) Figure 6 supplies the primary hct-42.1%, oxygenated-blood candidate at 1070 nm: `mua=0.42667 mm^-1`, `g=0.97073`, and `musp=2.05487 mm^-1`. The `mus` trace stops near 1050 nm, so it is not represented as a direct 1070-nm value.
- Friebel et al. (2009) provides hct-33.2% oxygenation sensitivities at 1070 nm: oxygenated/deoxygenated `mua=0.22999/0.14091 mm^-1`, `mus=63.17/62.05 mm^-1`, and shared `g=0.97599`. The paper reports that oxygenation effects on `mus` are not significant above 750-800 nm.
- Cortese et al.'s 65-subject human SCM study ends at 1050 nm. Its all-subject long-separation scattering law gives `musp=0.652095 mm^-1` at 1070 after an explicit 20-nm extrapolation; the 1050-nm absorption value is retained only as neighboring-wavelength context.
- Kothuri et al.'s released human tibia data provide exact 1070-nm sensitivity candidates for cortical-bone powder (`mua = 0.003`, `musp = 4.2987 mm^-1`), trabecular bone (`mua = 0.00833`, `musp = 0.544 mm^-1`), and frozen bone marrow (`mua = 0.00667`, `musp = 0.9663 mm^-1`). These are direct three-iteration means, not cranial nominal values.
- A secondary transcription and linear interpolation of Yaroslavsky et al.'s native gray-matter spectra gives candidate values `mua = 0.053 mm^-1`, `mus = 5.705 mm^-1`, and `g = 0.90`, implying `musp = 0.5705 mm^-1`. These remain sensitivity candidates because the numerical endpoints came from a secondary graph tabulation, not a primary data table.

None of those partial tuples can yet populate a production row. The graph estimates need independent digitization review and do not resolve source-method conflicts; the reported `g=0.9` values in the Bashkatov inverse solutions and Shapey's `g=0.85`, `n=1.40` were fixed inputs rather than independent measurements; the blood data are hct 5%; and tissue-specific refractive indices remain largely assumed rather than measured at 1070 nm.

## Audit rules

1. **1070 nm is a hard target.** A value reported at 1064 nm is preserved as neighboring-wavelength evidence, not relabeled as 1070 nm.
2. **Quantity identity is preserved.** `mus` and `musp` are not interchangeable. The conversion `musp = mus(1-g)` is made only when `g` comes from the same model or is explicitly declared as an assumption.
3. **Original units are retained.** Every evaluated spectral model stores its original cm^-1 value before division by 10 to mm^-1.
4. **Assumptions are not measurements.** Fixed inverse-model values for `g` or `n` and simulation-wide values such as `n=1.37` remain labeled as assumptions.
5. **Conflicts become scenarios.** Competing sources are not averaged by default.
6. **Atlas identity is binding.** Dura and marrow are not silently mapped to skull; `fat` and `fat_2` are not assumed identical; pure-skin data are not copied into `skin_and_muscles`.

## Tissue coverage and remaining blockers

| ID | Colin27 tissue | Best evidence now | Primary blocker |
|---:|---|---|---|
| 0 | background_air | Ideal boundary tuple identified | Freeze only with full scenario |
| 1 | cerebrospinal_fluid | CSF-water transmission equivalence plus interpolated water `mua` and formula-derived water `n` | No physiological CSF `mus`/`musp` or `g`; water substitution must be explicit |
| 2 | gray_matter | Exact Shapey Table S1 `mua`/`musp`; secondary Yaroslavsky candidate | Single frozen cadaver; select scenario and audit fixed `g`/`n` assumptions |
| 3 | white_matter | Exact Shapey Table S1 `mua`/`musp` | Fixed `g`/`n`; secondary Yaroslavsky transcriptions disagree |
| 4 | fat | Human `musp` model plus digitized exact-wavelength `mua` | Material absorption-method conflict, fixed `g`, unresolved `n` and atlas mapping |
| 5 | muscles | Exact porcine-muscle and bulk human upper-arm data plus a 65-subject human SCM scattering model extrapolated 20 nm | No isolated-human complete tuple; `g`, `n`, and layered-to-isolated mapping remain unresolved |
| 6 | skin_and_muscles | Pure-skin candidates plus exact bulk in-vivo human forehead data | Composite atlas class has no source-supplied composition fraction |
| 7 | skull | Digitized intact-cranial `mua`, cortical model, exact tibial component data | Site, preparation, composition, fixed `g`, and unresolved `n` |
| 9 | fat_2 | Same adipose candidate as label 4 | Optical meaning of `fat` versus `fat_2` unresolved |
| 10 | dura | Exact Shapey Table S1 `mua`/`musp` | Single frozen cadaver; fixed `g`/`n`; older formula only secondarily verified |
| 11 | marrow | Exact frozen human tibial-marrow `mua` and `musp` | Single elderly donor, boundary effects, cranial applicability, `g`, and `n` unresolved |
| 12 | vessels | Primary Friebel hct-42.1 oxygenated and hct-33.2 oxygenation-state curves, plus Roggan and Bosschaart sensitivities | Independent graph audit, arterial/venous and lumen/wall mapping, and `n` remain unresolved |

## Source assessment

### Directly relevant human measurements and models

**Shapey et al. (2022).** This is the most directly relevant primary dataset for gray matter, white matter, and dura. It reports human cadaveric healthy-tissue `mua` and model-fitted `musp` every 10 nm from 400 to 1800 nm, including 1070 nm. Healthy tissue came from one cadaver; samples were frozen, thawed at room temperature, and processed by a two-stage inverse adding-doubling workflow. The inversion fixed `g=0.85` and `n=1.40`, so those two values are model inputs, not direct measurements. Table S1 was acquired, its 24 sheets were structurally inspected, and the GM, WM, and Dura row-69 cells were transcribed into `literature/shapey_2022_1070_transcription.csv`. The production candidates use `mua_revised_mean` and `model_fitted_mus`; the article establishes that the latter is reduced scattering despite the abbreviated workbook header. The workbook contains mean columns but no numerical SD columns, so uncertainty is not invented from figure bands. [DOI](https://doi.org/10.1002/jbio.202100072)

**Yaroslavsky et al. (2002).** This source measured native human gray and white matter from seven nondiseased brains over 360-1100 nm using integrating-sphere measurements and inverse Monte Carlo. It is an important independent human dataset, but the values used in the current candidate interpolation were transcribed from a secondary tabulation of the plotted spectra. Gray-matter endpoints were internally consistent; white-matter scattering transcriptions were not, so no white-matter interpolation is accepted. [DOI](https://doi.org/10.1088/0031-9155/47/12/305)

**Bashkatov et al. (2005).** Human skin and adipose measurements support explicit reduced-scattering formulas. With wavelength in nm and output in cm^-1:

```text
skin: musp(lambda) = 73.7 lambda^-0.22 + 1.1e12 lambda^-4
fat:  musp(lambda) = 1050.6 lambda^-0.68
```

The 1070-nm evaluations and cm^-1-to-mm^-1 conversions are stored in the ledger and regression-tested. The IAD analysis fixed `g=0.9`. Figure 2a and Figure 6 were digitized with saved pixel-axis calibrations, yielding central 1070-nm `mua` estimates of `0.0157 mm^-1` for skin and `0.103 mm^-1` for adipose. The paper explicitly discusses a large adipose-absorption discrepancy plausibly related to lateral light loss. The digitized number preserves that conflict rather than resolving or averaging it away. [DOI](https://doi.org/10.1088/0022-3727/38/15/004)

**Bashkatov et al. (2006).** Ten postmortem human cortical cranial-bone samples support the model `musp(lambda) = 1533.02 lambda^-0.65 cm^-1` for 800-1100 nm. The model evaluates to `1.6460702479 mm^-1` at 1070 nm. Figure 3 was digitized to a central `mua` estimate of `0.0167 mm^-1`; Table 2 values through 1000 nm provide a local plausibility check but not an exact 1070 table cell. Again, `g=0.9` was fixed in the inversion. [DOI](https://doi.org/10.1117/12.697305)

**Roggan et al. (1999).** Figure 13 was digitized at 1070 nm into separate records: oxygenated `mua=0.259 mm^-1`, deoxygenated `mua=0.190 mm^-1`, `mus=19.85 mm^-1`, and `g=0.9859`. The oxygenated curve is the upper absorption curve at 1070 nm; this corrects the earlier reversed state labels. The measurements are means of three diluted-blood samples at hct 5%, 300 mosmol/L, 500 s^-1 shear, and 20 C. They are valuable state-specific evidence but cannot be scaled to physiological haematocrit by simple relabeling, and blood is not equivalent to a vessel wall or an undefined arterial/venous mixture. [DOI](https://doi.org/10.1117/1.429919)

**Mosca et al. (2020).** The open supplementary tables contain exact 1070-nm ex-vivo porcine-muscle means and three-position SDs: `mua=0.0150583 +/- 0.000715684 mm^-1` and `musp=0.2488027 +/- 0.0161099 mm^-1`. These values are retained as an animal sensitivity and not promoted to a human nominal row. [DOI](https://doi.org/10.1364/BOE.386349)

**Damagatla et al. (2026).** The open Zenodo results contain exact 1070-nm in-vivo human spectra for ten subjects at five locations. Averaging the six measurements within subject and then across subjects gives upper-arm `mua=0.0298683 mm^-1`, `musp=0.731867 mm^-1` and forehead `mua=0.017675 mm^-1`, `musp=0.868717 mm^-1`. These are realistic bulk layered-tissue measurements, not isolated muscle or pure skin coefficients. [DOI](https://doi.org/10.1038/s41597-026-06586-9)

**Cortese et al. (2023).** This 65-subject in-vivo human study measured the sternocleidomastoid region with time-domain NIRS at eight wavelengths from 637 to 1050 nm and fit `musp(lambda)=A(lambda/785)^(-b)`. The all-subject long-separation fit (`A=8.0 cm^-1`, `b=0.66`) evaluates to `0.6520947 mm^-1` at 1070 nm, only 20 nm past the measured endpoint. Table A5 reports long-separation `mua=0.37 +/- 0.01 cm^-1` at 1050 nm, but no absorption law supports extending it to 1070. Tissue `n=1.4` was fixed, not measured. Variable skin/adipose/fascia depth means this is a muscle-rich layered-region sensitivity rather than isolated muscle. [DOI](https://doi.org/10.1088/1361-6579/ad133a)

**Water and CSF evidence.** Human CSF transmission from 400 to 1800 nm closely matched water in Wasserzug et al., which supports—but does not force—an explicit water proxy. The Hale and Querry primary paper verifies a 25 C compiled/smoothed optical-constant spectrum; its printed Table I is coarse near 1070 nm, while the public fine-grid transcription supplies 1060/1080-nm values whose midpoint gives `mua=0.0125 mm^-1`. That numerical transcription remains independently auditable. Daimon and Masumura's primary Table 2 directly verifies the 21.5 C four-term Sellmeier coefficients; the formula gives `n=1.32431985643` at 1070, with expanded measurement uncertainty `8e-6` (`k=2`) and formula residual SD `1.3e-6`. No physiological CSF scattering or anisotropy measurement was found. [CSF DOI](https://doi.org/10.1117/1.JBO.28.9.094803), [water absorption DOI](https://doi.org/10.1364/AO.12.000555), [water refractive-index DOI](https://doi.org/10.1364/AO.46.003811)

**Physiological-haematocrit blood.** Friebel et al. (2006) directly measured human RBC suspensions at hct 42.1%, oxygen saturation above 99%, 20 C, and shear 600 s^-1. Figure 6 digitization gives `mua=0.42667 mm^-1`, `g=0.97073`, and `musp=2.05487 mm^-1` at 1070. Because Figure 6b's `mus` curve stops near 1050 nm, the ledger does not mislabel an extrapolation as direct measurement. Friebel et al. (2009) measured hct 33.2% RBCs at 100% and 0% oxygen saturation through 2000 nm. At 1070 the graph-derived pairs are `mua=0.22999/0.14091 mm^-1`, `mus=63.17/62.05 mm^-1`, and shared `g=0.97599`; the authors report that oxygenation-induced `mus` differences are not significant above 750-800 nm. The saved axis calibrations make every graph value reproducible, but they still require independent digitization review. [2006 DOI](https://doi.org/10.1117/1.2203659), [2009 DOI](https://doi.org/10.1117/1.3127200)

**Secondary blood context.** Bosschaart et al.'s compiled hct-45 appendix row at 1070 nm gives oxygenated/deoxygenated `mua=0.42/0.19 mm^-1`, oxygenated `mus=59.04 mm^-1`, and `g=0.9799`. It remains a sensitivity and cross-check rather than the central primary source. [DOI](https://doi.org/10.1007/s10103-013-1446-7)

### Important conflicts and implementation precedents

**Human bone heterogeneity.** Kothuri et al. (2025) released exact 10-nm data for one 89-year-old female donor's tibia. At 1070 nm, three-iteration means are `mua=0.003` and `musp=4.2987 mm^-1` for cortical-bone powder, `mua=0.00833` and `musp=0.544 mm^-1` for trabecular bone, and `mua=0.00667` and `musp=0.9663 mm^-1` for frozen bone marrow. The source separately reports spectral-fit values, all retained in `literature/kothuri_2025_human_bone_1070_transcription.csv`. The authors warn that cortical powder/flakes add scattering and that limited marrow volume introduced boundary effects. These data demonstrate component and preparation sensitivity; they are not an intact-cranium replacement for Bashkatov's cortical-skull model. [Article and open-data link](https://doi.org/10.1038/s41598-025-06138-y)

**Cassano et al. (2019).** The supplied paper's Table 1 is a valuable 1064-nm transcranial simulation precedent and has been transcribed verbatim into a separate CSV. It combines measurements, extrapolations, assumptions, and prior simulation choices, maps dura and marrow to skull, assumes `n=1.37` throughout, and does not establish that the full tuple is measured at 1070 nm. It is therefore context, not a production parameter source. [DOI](https://doi.org/10.1117/1.NPh.6.1.015004)

**Recent 1070-nm simulations.** Dong et al. model 1070 nm, but the accessible article does not publish the numerical tissue table needed to reproduce its wavelength-specific property map. It establishes implementation precedent, not a recoverable primary measurement set. [DOI](https://doi.org/10.1117/1.NPh.12.1.015010)

## Prespecified scenario structure

The eventual uncertainty analysis should use discrete, provenance-preserving cases rather than a single synthetic average:

- **Brain dataset:** Shapey exact-1070 versus Yaroslavsky-interpolated human data, after independent transcription review.
- **Bone compartment and preparation:** intact cortical cranium, trabecular tibia, cortical powder, and frozen marrow remain separate candidates; do not rank them on one low-to-high axis without matching the atlas class.
- **Blood state:** at minimum an oxygenated/arterial-like and deoxygenated/venous-like case with declared haematocrit and temperature.
- **Refractive index:** tissue-specific evidence if found; otherwise a declared uniform-`n` assumption sensitivity such as 1.37 versus 1.40, never mislabeled as measurement.
- **Composite tissue:** anatomy relabeling is preferred for `skin_and_muscles`; if impracticable, define and test a documented effective-medium rule.
- **CSF:** measured or best-available physiological scattering plus an explicitly labeled water-absorption substitute, with temperature matching.

These are scenario slots, not frozen numeric configurations.

## Provisional implementation status

The selected central bindings and 14 one-at-a-time cases are implemented under `inputs/optical_properties/provisional_1070_v1/`. The generator recomputes every `mus` derived from `musp` and `g`, preserves the neighboring-1064 fat and CSF precedents as assumptions, and emits a field-level provenance manifest. All tables are complete enough for research simulation but carry `scientific_status: provisional` and are ineligible for a production-labeled preflight. `inputs/optical_properties/production_1070_tbd.json` remains authoritative for the unresolved production gate.

## Work remaining before `nominal_1070_v1` can freeze

1. Independently review the Shapey spreadsheet cells and the saved pixel calibrations for the four graph sources; obtain numerical source tables if any authors can provide them.
2. Independently audit the saved Friebel graph calibrations and prespecify arterial/venous oxygenation states; do not naively scale between haematocrits.
3. Independently audit the Hale fine-grid public transcription and find a defensible physiological CSF-scattering source; the Daimon coefficients are now primary-paper verified.
4. Determine whether animal muscle, bulk in-vivo upper-arm data, and exact tibial-marrow data are acceptable only as surrogate sensitivity models.
5. Apply `inputs/anatomy/colin27_2008/optical_binding_policy_1070.md`; do not invent missing label semantics or composition fractions.
6. Establish tissue-specific refractive-index evidence or formally declare and test an assumption set; keep Shapey's 1.40 and Cassano's 1.37 labeled as assumptions.
7. The independent implementation audit of wavelength, quantity, unit, formula, and saved provenance links is complete in `optical_properties_1070_independent_audit_2026-08-14.md` and passes. It does not replace second-operator graph redigitization or acceptance of surrogate tissue mappings; those remain open above.
8. Freeze one nominal choice and discrete sensitivity cases only when all production cells are numeric and provenance-complete.

Run the current audit with:

```bash
.venv/bin/mcx-project audit-optical-ledger --project-root .
```

The command validates the ledger schema, checks all evidence references, requires exact agreement with the accepted anatomy labels, rejects a numeric 1070 target from a neighboring-wavelength-only record, and confirms that a non-frozen ledger cannot silently become a complete production table.
