# Novelty Search: Dense 1064/1070-nm Multisource tPBM Modeling

**Search date:** 2026-08-13  
**Literature cutoff:** 2026-08-13  
**Status:** completed screening search; refresh required before any priority claim or submission  
**Machine-readable ledger:** `literature/novelty_screening_2026-08-13.csv`

## Question and operational target

The target is not merely Monte Carlo modeling of transcranial photobiomodulation (tPBM), nor merely use of 1064/1070-nm light. The combined target is:

1. a realistic, dense, whole-head helmet or cap at approximately 1064/1070 nm;
2. an anatomically realistic human head model;
3. independently retained per-emitter transport fields or an equivalent decomposition;
4. voxelwise or regionwise attribution of cortical multisource overlap, such as dominant-emitter contribution, neighbor contribution, or effective contributor count; and
5. reproducible source geometry and optical normalization.

An **exact precedent** must satisfy all five elements. A **partial precedent** satisfies at least two central elements and materially constrains the novelty claim. An **adjacent method** informs wavelength, anatomy, dosimetry, or source modeling but does not implement the combined target.

## Sources searched

- the full local primary PDFs for Yue and Humayun (2015), Cassano et al. (2019), Yuan et al. (2020), and Dole et al. (2024), each read in full and checked page-by-page;
- PubMed and PubMed Central records/full text;
- publisher full text and metadata pages from SPIE/Neurophotonics, Optica, Wiley, Elsevier/PubMed, and World Scientific;
- the CaltechAUTHORS institutional repository;
- broad scholarly-web discovery with primary-source verification;
- backward and forward citation chaining from the Yue and Dole anchors and from the closest 1064-nm papers.

Twelve plausible records were retained in the screening ledger. Search hits that were plainly non-head, non-optical, clinical-only duplicates, reviews, or unrelated uses of “multisource” were not promoted to the ledger.

The attempted external deep-research run was not used because it would have uploaded the project PDFs and incurred paid usage. No project PDF was uploaded. The evidence below comes from local papers and primary-source web records.

## Query families

The search used the following exact or punctuation-normalized query families, with singular/plural and hyphen variants:

1. `"transcranial" "Monte Carlo" multisource photobiomodulation helmet human head`
2. `"1064 nm" transcranial photobiomodulation Monte Carlo simulation human head`
3. `"1070 nm" transcranial photobiomodulation Monte Carlo simulation human head`
4. `"distributed" near-infrared emitter array Monte Carlo transcranial`
5. `"1070 nm" helmet "Monte Carlo" photobiomodulation`
6. `"1064 nm" multisource helmet Monte Carlo photobiomodulation`
7. `"multisource transcranial photobiomodulation" simulation`
8. `"emitter array" 1064 Monte Carlo human head photobiomodulation`
9. `"transcranial photobiomodulation" MCX array simulation`
10. `"transcranial" LED array photon transport human head simulation`
11. `"light source array" human head Monte Carlo photobiomodulation`
12. `"multiple sources" MCX transcranial light propagation`
13. `"1070" "photobiomodulation helmet" simulation brain`
14. `"1070-nm" photobiomodulation helmet head model`
15. `"transcranial photobiomodulation" "dominant source" simulation`
16. `"transcranial photobiomodulation" emitter overlap Monte Carlo`
17. `tPBM "per-emitter" Monte Carlo`
18. `cortical photon overlap emitter array MCX photobiomodulation`
19. exact-title and DOI searches for each candidate and both anchor papers.

## Inclusion and exclusion rules

Included for direct screening:

- primary research, proceedings, preprints, or theses with spatial optical modeling of light entering a human head;
- transcranial PBM/NIR studies using Monte Carlo, finite-element diffusion, or a closely related photon-transport method;
- studies with multiple emitters, a helmet/cap, 1064/1070 nm, or explicit regional/voxel dosimetry.

Excluded from direct-precedent status:

- clinical or physiological tPBM studies without spatial optical modeling;
- single-source studies that do not add a distinct multisource or attribution method;
- animal-only, non-head, photodynamic, fNIRS-only, sinus-imaging, or optogenetic studies;
- reviews, vendor pages, marketing simulations, social posts, and patents. These may identify terminology or devices but cannot establish an academic-method precedent.

## Main result

No exact precedent was identified under this search for the **combined** target of a realistic dense whole-head 1064/1070-nm helmet plus retained per-emitter fields and explicit voxelwise/ROI cortical overlap attribution.

That result is not evidence that no such work exists. It means no report was identified within the documented sources and queries through the cutoff date.

The broader novelty claim does **not** survive. Multisource 1064-nm tPBM simulation was already reported:

- Cassano et al. (2019) modeled a 4 x 7 LED array, including two arrays used simultaneously at F3 and F4, at 670, 810, 850, 980, and 1064 nm on Colin27 using MCX. It reported regional deposition/fluence but not emitter-resolved cortical overlap attribution.
- Yuan et al. (2020) used the same commercial-array family at F3, F4, and Fpz across 18 age-dependent MRI atlases, again including 1064 nm. Its methods report 15 simulations per atlas (three source positions by five wavelengths), followed by bilateral F3/F4 treatment analysis; it quantified age-dependent regional deposition, not dense whole-head helmet overlap.

The closest whole-head helmet precedent is Dole et al. (2024): a realistic 41-location dual-wavelength helmet, registered to two MRI-derived heads, with independent-source `mcxyz` simulations summed and scaled. Its wavelengths are 670 and 810 nm, and it does not report per-source dominance, neighbor fraction, or effective contributor count.

## Closest precedents

| Study | What it establishes | What it does not establish |
|---|---|---|
| [Yue et al. (2015), Proc. SPIE](https://doi.org/10.1117/12.2077019) | Whole-scalp multisource 850-nm LED-array concept using finite-element diffusion and a simplified adult head | Monte Carlo, 1064/1070 nm, realistic device registration, emitter attribution |
| [Yue & Humayun (2015)](https://doi.org/10.1117/1.JBO.20.8.088001) | Dense 13-277 source whole-scalp Monte Carlo model, independent source fields, superposition, depth gain, uniformity | 1064/1070 nm, physical helmet geometry, per-emitter cortical attribution, reproducible beam/version details |
| [Cassano et al. (2019)](https://doi.org/10.1117/1.NPh.6.1.015004) | Two simultaneous 4 x 7 frontal LED arrays at F3/F4; MCX; 1064 nm included; cortical ROI dosimetry | Dense whole-head helmet, retained emitter contribution maps, whole-cortex overlap metrics |
| [Yuan et al. (2020)](https://doi.org/10.1117/1.NPh.7.1.015009) | F3, F4, and Fpz LED-array positions at 1064 nm over 18 age-dependent atlases; MCX; bilateral F3/F4 treatment analysis | Whole-head helmet, source-resolved overlap attribution |
| [Dole et al. (2024)](https://doi.org/10.4103/ATN.ATN-D-24-00022) | Realistic multisource helmet, digitized positions, two MRI heads, per-source runs summed, regional dosimetry | 1064/1070 nm, dense approximately 256-288 element model, emitter-resolved overlap metrics |
| [Van Lankveld et al. (2025)](https://doi.org/10.1364/BOE.567345) | 1064-nm human-head MCX dosimetry and skin-tone sensitivity | Multiple sources or helmet |
| [Chang et al. (2025)](https://doi.org/10.1364/BOE.570066) | 810/1064-nm participant-specific MCX fields and ROI prediction across 154 heads | Multiple therapeutic emitters, helmet, overlap attribution |
| [Yang et al. (2026)](https://doi.org/10.1002/brx2.70048) | 660/810/1064-nm human and mouse head modeling with detailed anatomy | Multisource helmet; multi-source arrays are proposed future work |

## Feature matrix

| Feature | Yue 2015 JBO | Cassano 2019 | Yuan 2020 | Dole 2024 | Target project |
|---|---:|---:|---:|---:|---:|
| Human anatomical head | yes | yes | yes, 18 atlases | yes, 2 MRIs | planned |
| Multiple emitters | 13-277 | 28 or 56 frontal LEDs | 28 per simulated position; bilateral F3/F4 analysis | 41 paired locations | approximately 288, unverified |
| Whole-head helmet/cap | conceptual whole scalp | no | no | yes | planned |
| 1064 or 1070 nm | no | 1064 | 1064 | no | 1070 planned |
| Independent-source transport/sum | yes | not reported emitter-by-emitter | not reported emitter-by-emitter | yes | planned |
| Voxel/ROI total dosimetry | yes | yes | yes | yes | planned |
| Dominant/neighbor/effective-source attribution | no | no | no | no | planned |
| Public reproducible geometry/code | no | partial source dimensions; MCX public | partial; MCX public | no modified-code/source table | planned |

## Claim ledger

| Candidate claim | Classification | Evidence and disposition |
|---|---|---|
| Multisource transcranial photon-transport modeling exists. | Published fact | Yue 2015 and Dole 2024 directly establish it. |
| Dense whole-scalp arrays up to 277 emitters were modeled before this project. | Published fact | Yue & Humayun 2015. |
| 1064-nm multisource tPBM modeling exists. | Published fact | Cassano 2019 directly models two simultaneous frontal LED arrays at 1064 nm; Yuan 2020 extends the array-position dosimetry across 18 age atlases. Do not claim first multisource 1064/1070 simulation. |
| A realistic physical multisource helmet has been modeled. | Published fact | Dole 2024 at 670/810 nm. |
| Clinical/experimental 1070-nm helmets exist. | Published fact, outside direct precedent | Bowen et al. 2023 and Hu et al. 2025 use 1070-nm helmets but do not report the target optical simulation. |
| A dense whole-head 1070-nm helmet simulation has not been published. | Search result, not fact of absence | No identified academic report under this protocol. Requires refresh and subscription-database check before publication. |
| Explicit cortical emitter-overlap attribution is absent from prior work. | Search result, not fact of absence | None of the screened exact/partial precedents reports `dominant_source`, `NCF`, `N_eff`, or an equivalent emitter-resolved cortical map. |
| The project is the first multisource 1064/1070 tPBM simulation. | Rejected | Contradicted by Cassano 2019 and Yuan 2020. |
| The project may contribute the first combined realistic dense 1070-nm whole-head helmet plus emitter-resolved cortical overlap analysis. | Defensible candidate gap | Retain only with “to our knowledge” or “we identified no prior report” language and refresh immediately before submission. |

## Recommended novelty language

Use:

> Multisource tPBM modeling and 1064-nm frontal LED-array dosimetry have already been reported, and a realistic multisource helmet has been modeled at 670/810 nm. In the literature search documented here, we identified no prior academic report combining a realistic dense whole-head 1064/1070-nm helmet with retained per-emitter fields and explicit voxelwise or regionwise attribution of cortical source overlap.

Do not use:

- “first multisource 1064/1070-nm simulation”;
- “first dense tPBM helmet model”;
- “no previous study has modeled 1070-nm tPBM”; or
- a patent-style novelty statement based only on this academic search.

## Remaining search risk

- The search did not include authenticated Scopus, Web of Science, Embase, ProQuest Dissertations, or IEEE Xplore interfaces. Run those before manuscript submission if institutional access is available.
- Patent novelty is a separate task and was deliberately excluded.
- 1064 nm and 1070 nm must remain separate wavelengths in parameter and priority claims.
- Hardware claims remain blocked until the exact target helmet model, revision, element count, geometry, and radiometry are verified.
- Refresh this ledger immediately before any preprint or submission because this field is active and 2025-2026 work is still appearing.
