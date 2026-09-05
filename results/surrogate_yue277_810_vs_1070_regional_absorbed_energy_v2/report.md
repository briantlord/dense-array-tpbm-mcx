# Regional absorbed-energy-density comparison

This analysis uses the saved equal-total 277-emitter fields. Values scale linearly with total launched optical energy or power; the project calibration is numerical and is not a measured device output.

Ratios failing the independent aggregate Monte Carlo or minimum-signal gates are suppressed. Passing ratios remain conditional on these optical/anatomical scenarios. No voxelwise ratio map is generated because no voxelwise convergence evidence has been established.

## Whole tissue classes

| Tissue | 810 absorbed per 100 J | 1070 absorbed per 100 J | 810/1070 |
|---|---:|---:|---:|
| Gray Matter | 0.826975 J | 1.177580 J | 0.702x |
| White Matter | 0.306573 J | 0.036668 J | 8.36x |
| **Total brain** | **1.133548 J** | **1.214248 J** | **0.934x** |

## Depth-resolved absorption

Depth is the shortest Euclidean distance from each voxel to exterior-connected background through the filled head envelope. It is a geometric depth measure, not a named anatomical parcellation or an optical path length.

### Gray and white matter combined

| Depth | 810 J/100 J | 1070 J/100 J | 810/1070 |
|---:|---:|---:|---:|
| <10 mm | 1.1598e-02 | 1.0201e-02 | 1.14x |
| 10-20 mm | 5.0667e-01 | 8.3225e-01 | 0.609x |
| 20-30 mm | 5.7559e-01 | 3.6408e-01 | 1.58x |
| 30-40 mm | 3.7725e-02 | 7.6002e-03 | 4.96x |
| 40-50 mm | 1.8297e-03 | 1.1594e-04 | 15.8x |
| >=50 mm | 1.3954e-04 | 2.9302e-06 | not qualified |

### Tissue-specific detail

| Tissue | Depth | 810 J/100 J | 1070 J/100 J | 810/1070 |
|---|---:|---:|---:|---:|
| Gray Matter | <10 mm | 1.0193e-02 | 1.0122e-02 | 1.01x |
| Gray Matter | 10-20 mm | 4.4453e-01 | 8.2047e-01 | 0.542x |
| Gray Matter | 20-30 mm | 3.5155e-01 | 3.4023e-01 | 1.03x |
| Gray Matter | 30-40 mm | 1.9522e-02 | 6.6625e-03 | 2.93x |
| Gray Matter | 40-50 mm | 1.0683e-03 | 9.4778e-05 | 11.3x |
| Gray Matter | >=50 mm | 1.1610e-04 | 2.9079e-06 | not qualified |
| White Matter | <10 mm | 1.4053e-03 | 7.8368e-05 | 17.9x |
| White Matter | 10-20 mm | 6.2139e-02 | 1.1777e-02 | 5.28x |
| White Matter | 20-30 mm | 2.2404e-01 | 2.3854e-02 | 9.39x |
| White Matter | 30-40 mm | 1.8203e-02 | 9.3775e-04 | 19.4x |
| White Matter | 40-50 mm | 7.6136e-04 | 2.1157e-05 | 36x |
| White Matter | >=50 mm | 2.3437e-05 | 2.2231e-08 | not qualified |

## Scaling

For a real total launched energy `E` joules, multiply every `J per 100 J` value by `E/100`. For continuous total optical power `P` watts, each reported mean `mJ/cm³ per 100 J` becomes `mW/cm³` after multiplying by `P/100`. This assumes the real emitter weighting matches the equal-total uniform model.

Absorbed-energy density is an optical deposition metric. It does not by itself predict temperature, photochemistry, or biological efficacy.

## Verification

- 810 stored absorbed field consistency: maximum absolute error `2.711e-20`.
- 810 whole-brain absorbed fraction: `0.011335479848`.
- 1070 whole-brain absorbed fraction: `0.012142482485`.
- All declared input and output files are SHA-256 recorded in `manifest.json`.
