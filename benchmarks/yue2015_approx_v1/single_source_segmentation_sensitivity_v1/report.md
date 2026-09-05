# Yue north-pole single-source segmentation sensitivity

This controlled study holds the Yue Table-2 optical coefficients, source coordinate and direction, MCX-CL build, photon count, and three common random seeds fixed. The variants are causal sensitivity operations, not reconstructions of Yue's unavailable SPM12 segmentation.

## Observable and normalization check

| Observable at 60 mm | Model value | Model / digitized Yue |
|:---|---:|---:|
| fluence_normalized_depth0 | 7.5147e-08 | 0.062 |
| fluence_normalized_peak_0_20 | 4.1972e-08 | 0.035 |
| absorbed_proxy_normalized_depth0 | 2.2544e-07 | 0.186 |
| absorbed_proxy_normalized_peak_0_20 | 1.2591e-07 | 0.104 |

The absorbed-energy proxy is independently checked against MCX's energy output after one fitted global unit scale. This tests the identity `energy proportional to mua times fluence`; it does not identify Yue's unpublished plot normalization.

## Segmentation effects on raw normalized MCX fluence

| Variant | Raw fluence / baseline | Absorbed proxy / Yue | Replicate CV |
|:---|---:|---:|---:|
| baseline | 1.000 | 0.169 | 2.523% |
| inner_scalp_transparent_2mm | 1.661 | 0.285 | 4.210% |
| inner_skull_to_csf_2mm | 1.890 | 0.321 | 2.600% |
| csf_into_gm_2mm | 25.909 | 4.421 | 1.806% |
| superior_csf_into_gm_2mm_r20 | 1.548 | 0.264 | 5.266% |
| deep_axis_gm_to_wm_r20 | 1.994 | 0.132 | 0.602% |
| combined_explanatory_bound | 10.951 | 0.722 | 5.371% |

Interpret the combined scenario only as an explanatory sensitivity. It stacks localized scalp, skull, superior-CSF, and deep gray/white changes and is not evidence that Yue used those exact tissue boundaries. The global CSF dilation is a separate aggressive upper bound.
