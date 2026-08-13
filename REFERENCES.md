# References and Verification Queue

This file is a bootstrap bibliography and verification record. Primary papers must be obtained and checked before their methods or numerical values enter code. Reading a paper verifies what it reports; it does not independently validate the paper's inputs or make unreported implementation details known.

## Core multisource literature

### Yue and Humayun (2015) — primary paper read August 13, 2026

**Verified citation:** Yue, L., & Humayun, M. S. (2015). Monte Carlo analysis of the enhanced transcranial penetration using distributed near-infrared emitter array. *Journal of Biomedical Optics, 20*(8), 088001. DOI: `10.1117/1.JBO.20.8.088001`.

**Local primary source:** `references/papers/Yue_Humayun_2015_distributed_NIR_emitter_array.pdf` (SHA-256: `b75300275301a060a234288b3ca780a64242f29d05e5861776b707c5d49306fd`).

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

**Local primary source:** `references/papers/Dole_et_al_2024_multisource_tPBM_helmet.pdf` (SHA-256: `a10eb60bb676b44e33680bace3801e0f9609ca68d12e7d0ca7ba6299b0c36896`).

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

## Software and methods references to add

These are required but not yet selected in this bootstrap packet:

- [ ] canonical MCX paper(s) and official documentation for the exact installed MCX/MCX-CL releases;
- [ ] PMCXCL/PMCX documentation and examples used by the Python pipeline;
- [ ] source/validation paper for the selected head atlas and segmentation;
- [ ] paper(s) supporting the Monte Carlo output normalization and absorbed-energy derivation used here;
- [ ] primary literature for 1070-nm tissue optical properties or wavelength-dependent spectral models;
- [ ] primary literature for source radiometry/beam characterization methods;
- [ ] phantom or layered-tissue validation literature near 1064–1070 nm;
- [ ] an ROI atlas reference if anatomical summaries are reported.

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

Record database, full query, date, inclusion criteria, and screening disposition. The defensible provisional statement is:

> Dense multisource modeling already exists, notably a distributed array up to 277 emitters at approximately 850 nm. The candidate gap is a realistic dense approximately 1070-nm helmet with explicit cortical multisource-overlap attribution.

Change that statement if the refreshed primary-literature search finds a closer precedent.
