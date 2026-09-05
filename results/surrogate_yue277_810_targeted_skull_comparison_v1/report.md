# Targeted 810-nm skull optical-property comparison

The in-vivo-first case is the primary estimate. Cassano is the higher-scattering sensitivity and Pitzschke is the lower-attenuation cadaver-fit sensitivity.

| Skull case | mua (mm^-1) | musp (mm^-1) | Reaches skull (% launched) | Reaches intracranial (% launched) | Intracranial / reaches-skull | Change vs primary |
|---|---:|---:|---:|---:|---:|---:|
| in_vivo_first | 0.021 | 0.92 | 8.6723% | 2.1052% | 24.27% | +0.0% |
| cassano_high_scatter | 0.011 | 1.92 | 8.6710% | 1.6600% | 19.14% | -21.1% |
| pitzschke_low_attenuation | 0.004 | 0.54 | 8.6723% | 3.6095% | 41.62% | +71.5% |

The complement of the conditional percentage is not skull absorption. It includes absorption anywhere before intracranial first entry plus scattering/backscatter that redirects energy away or out of the modeled head.

The nearly identical skull-entry control values show that the superficial path is matched. Differences in intracranial entry therefore arise from the label-7 skull coefficients, subject to the fixed skull-like marrow proxy.

These are normalized in-model energy fractions, not device irradiance, biological efficacy, or external scalp-coupling measurements.
