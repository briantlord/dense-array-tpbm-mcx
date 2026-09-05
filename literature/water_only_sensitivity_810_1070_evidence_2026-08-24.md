# Water-only 810/1070-nm counterfactual

Date: 2026-08-24

## Question

Can the larger pure-water absorption at 1070 nm materially explain the 1070-nm brain fluence and absorption result?

## Controlled intervention

The corrected-fat 1070-nm model is the baseline. For each selected tissue, only the water-derived part of `mua` is changed from its 1070-nm value to its 810-nm value:

`mua_counterfactual = mua_1070 - water_fraction * (mua_water_1070 - mua_water_810)`

Scattering, anisotropy, refractive index, geometry, source positions, launched energy, and every non-water contribution to absorption remain at their corrected 1070-nm values. This is therefore a component-isolation experiment, not an alternative physical 810-nm model.

## Pure-water spectrum

- Hale and Querry (1973), as transcribed by OMLC, gives `0.019858 cm^-1` at 810 nm, or `0.0019858 mm^-1`.
- The project 1070-nm value is the linear midpoint of the Hale-Querry rows at 1060 (`0.120 cm^-1`) and 1080 nm (`0.130 cm^-1`): `0.125 cm^-1`, or `0.0125 mm^-1`.
- The 100%-water decrement used here is therefore `0.0105142 mm^-1`.

Source: https://omlc.org/spectra/water/data/hale73.txt

## Tissue water fractions

The brain values are the strongest inputs: Oros-Peusquens et al. (2019) measured 21 healthy volunteers in vivo and reported white matter `69.1 +/- 1.7%` and gray matter `83.7 +/- 1.2%`, calibrated against CSF at approximately 100% water.

Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC6934004/

The systemic tissue proxies come from Wang et al. (1999): skin 0.6154, skeletal muscle 0.7857, blood 0.8000, bone 0.1700, and adipose 0.1533. The Colin27 composite, dura, and marrow entries are declared project assumptions because direct matched fractions are unavailable.

Source: https://journals.physiology.org/doi/full/10.1152/ajpendo.1999.276.6.E995

Jacques (2013) independently documents the component-mixing convention in which tissue absorption is constructed from water, blood, fat, and melanin volume fractions. It supports the decomposition method but does not supply matched fractions for all Colin27 labels.

Source: https://omlc.org/news/dec14/Jacques_PMB2013/index.html

The exact fraction transcription and confidence labels are in `literature/water_fraction_transcription_2026-08-24.csv`.

## Interpretation limits

This subtraction assumes that each baseline tissue coefficient can be decomposed into an additive water term plus a fixed non-water term. It does not account for wavelength-dependent hemoglobin, lipid, collagen, or other chromophores. It also deliberately freezes scattering, even though scattering changes with wavelength. A result from this test answers only how much the water spectral term contributes within the current 1070 model.
