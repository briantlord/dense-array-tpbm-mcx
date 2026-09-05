# Targeted 1070-nm evidence search: muscle, CSF/water, blood, and refractive index

## Outcome

The search materially narrows the uncertainty but does not justify a production freeze.

- **Muscle:** no isolated human skeletal-muscle dataset with a complete `mua`, `mus`/`musp`, `g`, and `n` tuple at 1070 nm was found. Mosca et al. provide exact open 1070-nm porcine muscle data (`mua=0.0150583`, `musp=0.2488027 mm^-1`). Damagatla et al. provide exact in-vivo human bulk upper-arm data (`mua=0.0298683`, `musp=0.731867 mm^-1`). Cortese et al. measured 65 human sternocleidomastoid regions through 1050 nm; their all-subject long-separation scattering law extrapolates 20 nm to `musp=0.652095 mm^-1` at 1070. Cortese's 1050-nm absorption (`0.37 cm^-1`) was not extrapolated because no absorption model was supplied. Both human measurements sample layered tissue rather than isolated muscle.
- **CSF/water:** Wasserzug et al. measured human CSF transmission from 400 to 1800 nm and found it closely matched water. Hale and Querry's primary paper confirms the 25 C compiled/smoothed optical-constant basis; the public fine-grid transcription gives 0.120 and 0.130 cm^-1 at 1060 and 1080 nm, yielding water `mua=0.0125 mm^-1` at 1070 by midpoint interpolation. The primary paper's own printed Table I is coarser near this band, so the fine-grid transcription still needs an independent numerical audit. Daimon and Masumura's primary Table 2 confirms the four-term 21.5 C Sellmeier coefficients and gives `n=1.32431985643` at 1070. Neither source supplies physiological CSF scattering or anisotropy.
- **Blood:** Friebel et al. (2006) now provides the primary physiological-haematocrit oxygenated candidate at hct 42.1%: graph-digitized `mua=0.42667 mm^-1`, `g=0.97073`, and `musp=2.05487 mm^-1` at 1070 nm. Its `mus` trace stops near 1050 nm, so no direct 1070 `mus` was invented. Friebel et al. (2009), hct 33.2%, gives oxygenated/deoxygenated `mua=0.22999/0.14091 mm^-1`, `mus=63.17/62.05 mm^-1`, and a shared `g=0.97599` at 1070; the paper states oxygenation-induced scattering differences are not significant above 750-800 nm. These primary graph values supersede Bosschaart as the central blood evidence while preserving Bosschaart and Roggan as discrete sensitivities.
- **Refractive index:** direct 1070-nm tissue-specific indices remain sparse. The water value is a defensible CSF-proxy sensitivity. Shapey's `n=1.40` and Cassano's `n=1.37` remain fixed model assumptions. Gienger et al. measured red-cell refractive-index increments through 1100 nm, not bulk whole-blood `n`, so it does not close the vessel row.

## Acquisition status

All five specifically requested primary papers were supplied, read in full, visually checked page by page, archived locally, and entered into the ledger on August 13, 2026:

1. Friebel et al. (2006), DOI `10.1117/1.2203659` — acquired and digitized.
2. Friebel et al. (2009), DOI `10.1117/1.3127200` — acquired and digitized.
3. Cortese et al. (2023), published DOI `10.1088/1361-6579/ad133a` — acquired; the spectrum ends at 1050 nm, so only the reported scattering model was extended by 20 nm.
4. Daimon and Masumura (2007), DOI `10.1364/AO.46.003811` — acquired; coefficients and uncertainty verified.
5. Hale and Querry (1973), DOI `10.1364/AO.12.000555` — acquired; paper provenance verified, with the public fine-grid transcription still flagged for independent numeric review.

There is no remaining paper on that acquisition list. The remaining evidence gaps are substantive: physiological CSF scattering/anisotropy, isolated-human muscle `g` and `n`, tissue-specific refractive indices, and an explicit atlas vessel-state/lumen-wall model.

Already acquired from open repositories and therefore not requested from the user: Mosca et al. porcine tissue tables, Damagatla et al. processed human in-vivo results, Wasserzug et al. open full text, Bosschaart et al. open appendix table, and Gienger et al. open full text.

## Search boundary

Exact-wavelength numeric values are entered only when a table, open dataset, or reproducible formula supports them. A curve endpoint, review compilation, animal tissue, bulk layered measurement, or fixed inversion parameter stays labeled as such. No 1064-nm value is renamed 1070 nm.
