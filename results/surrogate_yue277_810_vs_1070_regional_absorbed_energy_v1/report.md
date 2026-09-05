# Regional absorbed-energy-density comparison

This analysis uses the saved equal-total 277-emitter fields. Values scale linearly with total launched optical energy or power; the project calibration is numerical and is not a measured device output.

## Whole tissue classes

| Tissue | 810 absorbed per 100 J | 1070 absorbed per 100 J | 810/1070 |
|---|---:|---:|---:|
| Gray Matter | 0.826975 J | 1.177580 J | 0.702× |
| White Matter | 0.306573 J | 0.036668 J | 8.361× |
| **Total brain** | **1.133548 J** | **1.214248 J** | **0.934×** |

## Depth-resolved absorption

Depth is the shortest Euclidean distance from each voxel to exterior-connected background through the filled head envelope. It is a geometric depth measure, not a named anatomical parcellation or an optical path length.

### Gray and white matter combined

| Depth | 810 J/100 J | 1070 J/100 J | 810/1070 |
|---:|---:|---:|---:|
| <10 mm | 0.011598 | 0.010201 | 1.137× |
| 10-20 mm | 0.506668 | 0.832245 | 0.609× |
| 20-30 mm | 0.575587 | 0.364083 | 1.581× |
| 30-40 mm | 0.037725 | 0.007600 | 4.964× |
| 40-50 mm | 0.001830 | 0.000116 | 15.782× |
| >=50 mm | 0.000140 | 0.000003 | 47.621× |

### Tissue-specific detail

| Tissue | Depth | 810 J/100 J | 1070 J/100 J | 810/1070 |
|---|---:|---:|---:|---:|
| Gray Matter | <10 mm | 0.010193 | 0.010122 | 1.007× |
| Gray Matter | 10-20 mm | 0.444529 | 0.820468 | 0.542× |
| Gray Matter | 20-30 mm | 0.351547 | 0.340229 | 1.033× |
| Gray Matter | 30-40 mm | 0.019522 | 0.006662 | 2.930× |
| Gray Matter | 40-50 mm | 0.001068 | 0.000095 | 11.272× |
| Gray Matter | >=50 mm | 0.000116 | 0.000003 | 39.925× |
| White Matter | <10 mm | 0.001405 | 0.000078 | 17.932× |
| White Matter | 10-20 mm | 0.062139 | 0.011777 | 5.276× |
| White Matter | 20-30 mm | 0.224040 | 0.023854 | 9.392× |
| White Matter | 30-40 mm | 0.018203 | 0.000938 | 19.412× |
| White Matter | 40-50 mm | 0.000761 | 0.000021 | 35.986× |
| White Matter | >=50 mm | 0.000023 | 0.000000 | 1054.264× |

## Scaling

For a real total launched energy `E` joules, multiply every `J per 100 J` value by `E/100`. For continuous total optical power `P` watts, each reported mean `mJ/cm³ per 100 J` becomes `mW/cm³` after multiplying by `P/100`. This assumes the real emitter weighting matches the equal-total uniform model.

Absorbed-energy density is an optical deposition metric. It does not by itself predict temperature, photochemistry, or biological efficacy.

## Verification

- 810 stored absorbed field consistency: maximum absolute error `2.711e-20`.
- 810 whole-brain absorbed fraction: `0.011335479848`.
- 1070 whole-brain absorbed fraction: `0.012142482485`.
- All declared input and output files are SHA-256 recorded in `manifest.json`.
