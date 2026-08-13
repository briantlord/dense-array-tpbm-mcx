# References and Verification Queue

This file is a bootstrap bibliography and verification record. Primary papers must be obtained and checked before their methods or numerical values enter code. Reading a paper verifies what it reports; it does not independently validate the paper's inputs or make unreported implementation details known.

## Core multisource literature

### Yue and Humayun (2015) — primary paper read August 13, 2026

**Verified citation:** Yue, L., & Humayun, M. S. (2015). Monte Carlo analysis of the enhanced transcranial penetration using distributed near-infrared emitter array. *Journal of Biomedical Optics, 20*(8), 088001. DOI: `10.1117/1.JBO.20.8.088001`.

**Verification source:** Publisher PDF read locally but intentionally excluded from GitHub; retrieve via DOI. Locally verified SHA-256: `b75300275301a060a234288b3ca780a64242f29d05e5861776b707c5d49306fd`.

**Why it matters:** foundational computational precedent for independent-source simulation and superposition in distributed scalp arrays, reportedly including up to 277 emitters and approximately 850-nm conditions.

**Verified from the paper:**

- [x] DOI, title, authors, year, journal, volume/issue, and article number
- [x] 850-nm primary simulation and 690-nm comparison
- [x] density cases of 13, 53, 105, 181, 229, and 277 point sources; approximately equal-solid-angle spherical placement
- [x] Colin27 at 1-mm isotropic resolution, segmented with SPM12 into scalp, skull, modified CSF, gray matter, and white matter
- [x] reported optical-property table and cited source papers
- [x] MCXLAB implementation, Gaussian source default, unit initial photon weights, and `10^9` photons launched per source
- [x] benchmark enhancement is multisource divided by the single north-pole reference source along that source's propagation axis; it is not `EF_dom`
- [x] source-axis depth profiles, source-density analysis, and relative-SD uniformity definition

**Unresolved or requiring care:** the exact MCXLAB release, random seeds/replicates, convergence evidence, detailed boundary configuration, source beam parameters, code, and numerical data are not reported. The paper calls the voxelwise sum of dropped photon weight “photon flux”; the implementation must determine which MCX output reproduces that deposited-weight quantity rather than silently substituting fluence. Optical-property source papers remain to be checked independently.

### Dole et al. (2024) — primary paper read August 13, 2026

**Verified citation:** Dole, M., Bleuet, P., Auboiroux, V., Billères, M., & Mitrofanis, J. (2024). Monte Carlo simulations of a multisource transcranial photobiomodulation helmet device: application to young and aged brains. *Advanced Technology in Neuroscience, 1*(2), 261–275. DOI: `10.4103/ATN.ATN-D-24-00022`.

**Verification source:** PDF read locally but intentionally excluded from GitHub; retrieve via DOI or another authorized source. Locally verified SHA-256: `a10eb60bb676b44e33680bace3801e0f9609ca68d12e7d0ca7ba6299b0c36896`.

**Why it matters:** possible precedent for registering a realistic multisource helmet to young and aged head anatomies at wavelengths reported as 670 and 810 nm.

**Verified from the paper:**

- [x] full bibliographic record and DOI
- [x] WellRed Coronet 6 Duo with 41 paired locations, comprising 41 670-nm LEDs at 345 mW each and 41 810-nm LEDs at 267 mW each
- [x] paired-source midpoint positions digitized with Polhemus and registered to MRI-derived head surfaces; Gaussian source with reported 0.76-mm beam radius
- [x] one 24-year-old and one 75-year-old female T1 MRI, 1-mm isotropic voxels, CAT12 segmentation, MNI normalization, and AAL3 parcellation
- [x] six media labels and the reported wavelength-specific optical table; refractive index fixed at 1.37 for brain tissues
- [x] modified `mcxyz`, `10^9` photons per source, multiple single-source runs concatenated/summed, followed by power and 12-minute exposure scaling
- [x] normalized voxel output reported as deposited power density per incident source watt, with regional totals and energy densities derived afterward

**Unresolved or requiring care:** this is a realistic-helmet precedent, not an MCX/MCXLAB benchmark. The modified `mcxyz` code/patch, exact software version, random seeds, convergence study, boundary settings, full registration residuals, and source-orientation table are not supplied. Only two individual anatomies were modeled. The PDF refers to two additional tables that are not embedded in the supplied file; obtain them separately if their full regional values are needed. Optical-property source papers remain to be checked independently.

### Cassano et al. (2019) — primary paper read August 13, 2026

**Verified citation:** Cassano, P., Tran, A. P., Katnani, H., Bleier, B. S., Hamblin, M. R., Yuan, Y., & Fang, Q. (2019). Selective photobiomodulation for emotion regulation: model-based dosimetry study. *Neurophotonics, 6*(1), 015004. DOI: `10.1117/1.NPh.6.1.015004`.

**Verification source:** Publisher PDF read locally but intentionally excluded from GitHub; retrieve via DOI. Locally verified SHA-256: `45466fdaf398fea6fbf926a1340784e71f5319c1606de9adcb74f8330626683d`.

**Why it changes the novelty claim:** the study modeled a 4 x 7 Omnilux New-U LED array and included a condition with two arrays used simultaneously at F3 and F4. It used MCX on Colin27, simulated `10^8` photons per condition, and included 1064 nm among five wavelengths. It therefore rules out a “first multisource 1064/1070-nm tPBM simulation” claim. It did not model a dense whole-head helmet or report emitter-resolved dominance, neighbor contribution, or effective-source maps.

**Verified from the paper:** 0.5-mm Colin27 with eight consolidated tissue classes; 670/810/850/980/1064-nm optical tables; a 4 x 7 Omnilux New-U array with 11-mm spacing on the long edge and 8-mm spacing on the short edge; tangent source planes and pencil-beam LED elements; simultaneous bilateral F3/F4, unilateral F3, unilateral F4, and single Fpz protocols; `10^8` photons per test scenario; total emitted energy normalized to 1 J per single source array and 2 J for the combined F3/F4 condition; average and 99th-percentile regional deposited-energy estimates, fluence, and illustrative treatment scaling.

**Unresolved or requiring care:** exact MCX release and configuration, per-element field retention, random seeds/replicates, convergence evidence, detailed boundary settings, full array orientation coordinates, and code/data are not reported. The source elements are described as pencil beams, so the paper is a multisource array precedent but not a validated radiometric model of a dense helmet. Its conclusion that 810 nm ranked highest is conditional on the selected literature optical properties, which the authors themselves flag as uncertain.

### Yuan et al. (2020) — primary paper read August 13, 2026

**Verified citation:** Yuan, Y., Cassano, P., Pias, M., & Fang, Q. (2020). Transcranial photobiomodulation with near-infrared light from childhood to elderliness: simulation of dosimetry. *Neurophotonics, 7*(1), 015009. DOI: `10.1117/1.NPh.7.1.015009`.

**Verification source:** Publisher PDF read locally but intentionally excluded from GitHub; retrieve via DOI. Locally verified SHA-256: `9c7ed0ec96c605afa84e069ce8f5358351ec985655d106198dddfb4aeeb6d95b`.

**Why it changes the novelty claim:** the study modeled Omnilux New-U arrays at F3, F4, and Fpz across 18 age-dependent MRI atlases, launched `10^9` photons per source-position/wavelength condition with MCX, and included 1064 nm. It then analyzed F3/F4 treatment of dlPFC and Fpz treatment of vmPFC. Its endpoint was regional deposition/fluence and age dependence, not dense whole-head helmet overlap or per-emitter cortical attribution.

**Verified from the paper:** 18 average MRI atlases spanning ages 5 through 89; 1-mm isotropic WM, GM, CSF, and composite extracerebral-tissue segmentations plus air cavities; DKT/FreeSurfer cortical parcellations; three source positions by five wavelengths for 15 simulations per atlas; F3/F4 arrays rotated about 90 degrees relative to Cassano et al.; `10^9` launched photons per simulation; normalized average energy deposition with adaptive nonlocal-means denoising; 99th-percentile target fluence for exposure-time estimates; age-invariant optical properties; and a reported decline in energy delivery with increasing extracerebral-tissue thickness.

**Unresolved or requiring care:** the paper inherits exact LED dimensions and most optical properties from Cassano et al.; it reports three source-position simulations rather than explicitly documenting one combined 56-element MCX run; exact MCX release/configuration, source normalization across the bilateral analysis, per-emitter outputs, seeds/replicates, convergence, boundaries, code, and numerical fields are not supplied. The four-layer composite extracerebral model and age-invariant optical properties limit direct use as a production optical ledger. Results for young children are explicitly described as qualitative because the extracerebral segmentation pipeline had limited pediatric validation.

### Current novelty audit — completed August 13, 2026

The auditable search report is `literature/novelty_search_2026-08-13.md`; the screened-record table is `literature/novelty_screening_2026-08-13.csv`.

No exact report was identified that combines a realistic dense whole-head 1064/1070-nm helmet, independently retained per-emitter fields, and explicit voxelwise or regionwise cortical source-overlap attribution. This is a documented search result, not proof of absence. The provisional contribution must therefore be stated narrowly and refreshed before submission.

## Software and methods references to add

These are required but not yet selected in this bootstrap packet:

- [ ] canonical MCX paper(s) and official documentation for the exact installed MCX/MCX-CL releases;
- [ ] PMCXCL/PMCX documentation and examples used by the Python pipeline;
- [x] official MNI Colin27 high-resolution 2008 dataset release and citation metadata selected and recorded in `inputs/anatomy/colin27_2008/`; full methodological appraisal of the two cited papers remains pending;
- [ ] paper(s) supporting the Monte Carlo output normalization and absorbed-energy derivation used here;
- [ ] primary literature for 1070-nm tissue optical properties or wavelength-dependent spectral models;
- [ ] primary literature for source radiometry/beam characterization methods;
- [ ] phantom or layered-tissue validation literature near 1064–1070 nm;
- [ ] an ROI atlas reference if anatomical summaries are reported.

### Selected anatomy source — acquired August 13, 2026

The project uses the official MNI/BIC Colin27 high-resolution 2008 NIfTI release as its preserved source anatomy. The release provides 0.5-mm isotropic T1, T2, and PD images and a 12-class discrete tissue phantom in Talairach space. The official page, local license copy, archive/extracted-file hashes, NIfTI affine, and verified label counts are recorded under `inputs/anatomy/colin27_2008/`.

The release cites Holmes et al. (1998), DOI `10.1097/00004728-199803000-00032`, and Aubert-Broche et al. (2006), DOI `10.1016/j.neuroimage.2006.03.052`. Citation identity and the latter DOI were checked against PubMed; neither full paper has yet been appraised for this anatomy gate.

The production approximately 1-mm volume remains a derived artifact. Its resampling, tissue consolidation, topology, coordinate transforms, and optical-property binding must pass the remaining anatomy tasks before simulation.

## Optical-property source ledger requirements

A paper belongs in the production ledger only after checking:

- tissue identity and anatomical definition;
- human versus animal and species;
- in vivo, ex vivo, fixed, fresh, or homogenized state;
- measurement method and temperature;
- measured wavelength range and spectral resolution;
- whether it reports `mua`, `mus`, `musp`, `g`, or `n`;
- units and any transformations;
- sample size/variability;
- compatibility with the MCX tissue class.

The final optical table should cite the source at the individual cell or row level. A general review is useful for discovery but should not replace the primary measurement where available.

## Novelty-search protocol

Before describing the project as filling a literature gap, search at minimum for combinations of:

- photobiomodulation / transcranial photobiomodulation;
- Monte Carlo / photon transport / dosimetry;
- multisource / multi-source / distributed emitter / LED array / helmet;
- 1064 nm / 1070 nm / near-infrared;
- fluence overlap / superposition / enhancement / cortical dose.

Record database, full query, date, inclusion criteria, and screening disposition. The defensible provisional statement after the 2026-08-13 search is:

> Multisource tPBM modeling and 1064-nm frontal LED-array dosimetry already exist, and a realistic multisource helmet has been modeled at 670/810 nm. No prior academic report was identified in the documented search that combines a realistic dense whole-head 1064/1070-nm helmet with retained per-emitter fields and explicit voxelwise or regionwise cortical source-overlap attribution.

Change that statement if the refreshed primary-literature search finds a closer precedent.
