# 1070-nm water-only counterfactual

## Result

Replacing only the water-derived absorption term in the corrected-fat 1070-nm model with the Hale-Querry 810-nm water value increased equal-total integrated brain fluence from `0.1415077317` to `0.2494324814`, a `76.2677%` increase.

Brain absorption increased from `1.214248%` to `1.912809%` of launched energy, a `0.698560` percentage-point or `57.5303%` relative increase. Total modeled tissue absorption decreased from `56.819788%` to `49.897141%`; correspondingly, escaped or unabsorbed energy increased from `43.180212%` to `50.102859%`.

This answers a narrow counterfactual question: the 1070-nm water absorption spectrum can materially reduce brain fluence in this model. It does not show that the complete 810-nm model should equal this counterfactual, because scattering and every non-water chromophore were deliberately frozen at 1070 nm.

For context, the independent full 810-nm model has brain integrated fluence `0.3286713815`. The water-only counterfactual closes `57.6633%` of the fluence gap between corrected 1070 and independent 810, but remains `24.1089%` below the independent 810 fluence. Its brain absorption (`1.912809%`) is also much higher than the independent 810 value (`1.133548%`) because the counterfactual retains the larger non-water 1070 tissue absorption terms. Water is therefore a major contributor to the fluence difference, not a complete explanation of the wavelength comparison.

## Strong versus assumption-sensitive evidence

The targeted first-entry experiment separates two effects:

| Scenario | Brain-parenchyma entry | Change from corrected 1070 | White-matter entry | Change from corrected 1070 |
|---|---:|---:|---:|---:|
| Corrected 1070 baseline | 1.859730% | — | 0.176631% | — |
| Brain/CSF water term at 810 | 1.946566% | +4.669% | 0.216633% | +22.647% |
| Whole-head water term at 810 | 2.773648% | +49.143% | 0.311211% | +76.192% |

The brain/CSF-only values use in-vivo MRI water fractions for gray and white matter and are the higher-confidence result. The much larger whole-head values depend strongly on systemic proxies for superficial tissues, including an assumed 0.700 water fraction for the Colin27 skin-and-muscle composite. They should be treated as a sensitivity scenario, not a best estimate.

## Tissue response in the full whole-head run

| Tissue | Fluence change | Absorbed energy, baseline | Absorbed energy, counterfactual | Absorption change |
|---|---:|---:|---:|---:|
| CSF | +66.96% | 0.27579% | 0.07315% | -73.48% |
| Gray matter | +74.59% | 1.17758% | 1.85242% | +57.31% |
| White matter | +100.81% | 0.03667% | 0.06039% | +64.70% |
| Fat | +24.24% | 2.39181% | 2.49270% | +4.22% |
| Muscle | +19.49% | 32.96942% | 28.49860% | -13.56% |
| Skin and muscle | +17.02% | 13.20017% | 9.01488% | -31.71% |
| Skull | +39.87% | 3.12001% | 3.89688% | +24.90% |
| Fat 2 | +24.10% | 2.94478% | 3.06534% | +4.09% |
| Dura | +53.61% | 0.13230% | 0.18192% | +37.51% |
| Marrow | +42.17% | 0.27246% | 0.29372% | +7.80% |
| Vessels | +59.50% | 0.29878% | 0.46715% | +56.35% |

## Interpretation boundary

The counterfactual uses `mua_new = mua_1070 - water_fraction * (0.0125 - 0.0019858) mm^-1`. The brain fractions are in-vivo tissue-class measurements. Several non-brain fractions are systemic mass-fraction proxies, while the optical mixing equation is most naturally a volume-fraction model; tissue density and atlas composition are not resolved. This is another reason the whole-head value is a sensitivity bound.

The correct conclusion is therefore not “water explains 76%.” It is: water absorption is demonstrably a factor; its high-confidence local brain/CSF effect measurably improves deep entry, while a potentially much larger superficial-path effect exists but is currently limited by tissue-composition uncertainty.
