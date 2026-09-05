# 810-nm skull optical-property decision record

## Decision

The primary skull row for the independent 810-nm model is an **in-vivo-first estimate**:

| Quantity | Primary value | Basis |
|---|---:|---|
| `mua` | 0.021 mm^-1 | Rounded from Bevilacqua et al.'s exposed living-human skull value of 0.0215 mm^-1 at 849 nm. |
| `musp` | 0.92 mm^-1 | Matcher et al.'s intact living-head fit gives 0.94 +/- 0.07 mm^-1 at 800 nm and `musp(lambda)=1.45-6.5e-4 lambda`, or 0.9235 mm^-1 at 810 nm; Bevilacqua reports 0.91 mm^-1 at 849 nm. |
| `g` | 0.89 | Project/Cassano phase-function assumption; neither in-vivo result directly establishes a skull-specific Henyey-Greenstein `g`. |
| `mus` | 8.363636 mm^-1 | `musp/(1-g)`. |
| `n` | 1.37 | Project/Cassano refractive-index assumption, not a direct 810-nm living-skull measurement. |

This is a synthesis, not a claim that one paper measured the complete MCX row at exactly 810 nm.

## Primary and sensitivity evidence

1. **Bevilacqua F, Piguet D, Marquet P, Gross JD, Tromberg BJ, Depeursinge C.** “In vivo local determination of tissue optical properties: applications to human brain.” *Applied Optics* 38 (1999), 4939–4950. DOI: `10.1364/AO.38.004939`.
   - Direct intraoperative measurements on exposed living human skull.
   - Skull at 849 nm: `mua=0.0215 mm^-1`, `musp=0.91 mm^-1`.
   - Strongest evidence here for skull-specific in-vivo absorption, but it is 39 nm above the target and does not resolve cortical/diploic layers.

2. **Matcher SJ, Cope M, Delpy DT.** “In vivo measurements of the wavelength dependence of tissue-scattering coefficients between 760 and 900 nm measured with time-resolved spectroscopy.” *Applied Optics* 36 (1997), 386–396. DOI: `10.1364/AO.36.000386`.
   - Intact-head in-vivo measurement in 10 adults, ages 23–35, with 4-cm source-detector separation.
   - Head at 800 nm: `mua=0.016 +/- 0.001 mm^-1`, `musp=0.94 +/- 0.07 mm^-1`.
   - Reported head scattering fit evaluates to `musp=0.9235 mm^-1` at 810 nm.
   - This is a layered-head homogeneous inversion. The paper's modeling indicates absorption mixes deeper and superficial tissues while scattering is weighted more toward outer tissues; it supports the skull scattering scale but is not an isolated-skull measurement.
   - Local source: `references/papers/matcher1997.pdf`.

3. **Cassano P et al.** 2019 selective transcranial PBM dosimetry study, Table 1.
   - Compiled 810-nm skull case: `mua=0.011 mm^-1`, `musp=1.92 mm^-1`, `g=0.89`, `n=1.37` (`mus=17.454545 mm^-1`).
   - Retained as the higher-scattering sensitivity and as the source for the rest of the initial 810-nm tissue table.
   - Local source: `references/papers/Cassano_et_al_2019_selective_tPBM_dosimetry.pdf`.

4. **Pitzschke A et al.** “Red and NIR light dosimetry in the human deep brain.” *Physics in Medicine & Biology* 60 (2015), 2921–2937. DOI: `10.1088/0031-9155/60/7/2921`.
   - Coefficients fitted with Monte Carlo to 808-nm cadaver-head fluence measurements.
   - Skull sensitivity: `mua=0.004 mm^-1`, `musp=0.54 mm^-1` (`mus=4.909091 mm^-1` at project `g=0.89`).
   - Retained as the lower-attenuation endpoint. It is not living tissue and its fitted parameters are model-dependent.

5. **Tedford CE et al.** “Quantitative analysis of transcranial and intraparenchymal light penetration in human cadaver brain tissue.” *Lasers in Surgery and Medicine* 47 (2015), 312–322. DOI: `10.1002/lsm.22343`.
   - Eight unfixed refrigerated cadaver heads, 20 sites, 808-nm transcranial measurements.
   - Whole-head effective attenuation was 2.22 cm^-1; normalizing at the inner skull reduced variability, showing that scalp/skull largely changes the transmission intercept.
   - External validation for whole-path attenuation, not a source of skull `mua` or `musp`.
   - Local source: `references/papers/tedford2015.pdf`.

6. **Eggert HR, Blazek V.** 1987 human brain/meningeal optical study.
   - Autopsy tissue, including one dura sample, with relative reflection/absorption/scattering and Beer-law penetration depth.
   - Qualitatively indicates dura is comparatively transmissive near 810 nm but does not provide a complete MCX-ready coefficient row.
   - Therefore the current dura=skull mapping remains an explicit likely-overattenuating proxy rather than evidence-backed equivalence.
   - Local source: `references/papers/eggert1987.pdf`.

## Interpretation limits

- Living skull varies with cortical thickness, diploic porosity, marrow/blood content, site, age, and hydration. A single homogeneous label cannot reproduce that microstructure.
- The primary row favors living-human evidence, while the Cassano and Pitzschke rows bracket materially different absorption/scattering partitions.
- The current comparison changes atlas label 7 only. Label 11 (marrow) stays fixed at the Cassano skull-like proxy, so the result is a cortical-skull-coefficient sensitivity, not the full uncertainty of the skull complex.
- Non-skull tissue values are an initial Cassano-based 810-nm implementation and need their own sensitivity audit before any production-nominal claim.
