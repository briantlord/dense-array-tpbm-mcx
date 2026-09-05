# Refined 810-nm full-atlas basis result

Status: **complete**. All 277 Yue-derived spatial-surrogate emitters ran independently at 100,000,000 photons per emitter on the Windows RTX 3080 Ti basis (27.7 billion photons total). All 277 native JNIfTI fluence fields passed manifest and checksum preflight before streaming aggregation.

## Main result

For equal total launched energy distributed uniformly across all 277 emitters, the refined primary 810-nm model absorbs **1.13355% in brain tissue**:

- gray matter: **0.82698%**
- white matter: **0.30657%**
- gray + white matter: **1.13355%**

The corrected recommended 1070-nm model (effective adipose \(\mu_a=0.010\ \mathrm{mm^{-1}}\)) absorbed **1.21425%** in gray + white matter under the same equal-total normalization. The 810-nm value is therefore **0.9335 times** the corrected 1070-nm value, or **6.65% lower**. It lies within the completed 1070 fat-property bracket of **0.90636% to 1.32223%**.

The earlier **0.44582%** value is not the corrected 1070 comparator. It belongs to the superseded extreme-high-fat baseline with \(\mu_a=0.103\ \mathrm{mm^{-1}}\), which absorbed excessive energy superficially.

Despite slightly lower brain absorption, 810 nm produces **2.3226 times more integrated brain fluence** than the corrected 1070 model (0.32867 versus 0.14151 in the unit-total relative normalization). Absorption differs from fluence because it is fluence multiplied by the local absorption coefficient. In particular, gray-matter \(\mu_a\) is 0.028 mm^-1 at 810 nm versus 0.08892 mm^-1 in the 1070 model, so substantially more 810-nm light can be present in gray matter while a smaller fraction is absorbed there.

This is absorbed energy, not merely energy that crosses into brain. The targeted 810-nm tally found 1.8913% reaching brain parenchyma; absorption and entry are different quantities because energy can enter, scatter, leave, or be absorbed later.

## Absorption by atlas tissue

| Atlas tissue | Absorbed % of equal-total launched energy |
|---|---:|
| CSF | 0.07365% |
| Gray matter | 0.82698% |
| White matter | 0.30657% |
| Fat | 0.11741% |
| Muscle | 29.18267% |
| Skin-and-muscle composite | 30.28794% |
| Skull | 2.78161% |
| Fat 2 | 0.13778% |
| Dura | 0.09326% |
| Marrow | 0.33676% |
| Vessels | 0.19970% |
| **All modeled tissues** | **64.34433%** |

The remaining **35.65567%** was not absorbed in a labeled tissue before leaving the finite model/time window. It should not be interpreted as a clean specular-reflection measurement; it combines boundary escape after superficial scattering with other unabsorbed transport loss from the modeled domain.

## Multi-emitter summation

The summed 810-nm field is highly distributed across emitters:

| Brain-wide metric | 810 nm |
|---|---:|
| Integrated-field enhancement over dominant emitter (EF_dom) | 85.86 |
| Integrated non-dominant contribution | 98.84% |
| Integrated effective emitter count (N_eff) | 216.43 |
| Median voxel EF_dom | 3.73 |
| Median voxel non-dominant contribution | 73.15% |
| Median voxel N_eff | 6.69 |

Thus, at a typical brain voxel, the total 810-nm fluence is about **3.73 times** the largest single-emitter contribution, and roughly **73%** comes from all non-dominant emitters combined. These ratios describe spatial overlap; they do not create energy and remain linear with uniform source-power scaling.

The previously quoted 1070 overlap metrics were from the superseded high-fat baseline. They are not used here as the corrected-fat comparison; corrected-fat overlap maps require streaming the corrected 1070 basis separately.

## Marrow uncertainty carried forward

Only the refined-primary marrow case received the full 277-source atlas run. The previously completed targeted marrow endpoints changed brain-parenchyma entry by -9.68% (skull-like endpoint) and +10.82% (trabecular endpoint). Applying those relative changes to the full-basis brain-absorption result gives an **approximate propagated range of 1.0238% to 1.2562%**. The analogous white-matter range is **0.2774% to 0.3399%**.

This is an uncertainty annotation, not a substitute for two additional full 277-emitter endpoint runs. It assumes the targeted relative marrow sensitivity transfers approximately to the full-basis absorbed-energy metric.

## Scientific boundary

This remains a provisional Colin27/Yue-derived spatial surrogate. The source locations and normals are inherited geometry, not target helmet CAD; each source is a normalized pencil source, not measured beam radiometry or coupling. Results are modeled relative transport quantities, not patient-specific dose, thermal response, or evidence of biological efficacy.
