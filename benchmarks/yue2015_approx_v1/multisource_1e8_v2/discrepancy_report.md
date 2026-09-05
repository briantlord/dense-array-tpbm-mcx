# Yue 2015 850-nm multisource discrepancy report

This is an approximate reconstruction, not an exact rerun of the unpublished MCXLAB configuration. The field basis uses the accepted project Colin27 derivative, the paper's Table-2 optical coefficients, deterministic project source coordinates, pencil sources, and `10^8` photons per source.

## North-pole reference-source enhancement

| Depth (mm) | Modeled EF_ref | Digitized Yue | Modeled/paper | Within digitization interval |
|---:|---:|---:|---:|:---:|
| 0 | 1.002 | 1.175 | 0.853 | yes |
| 10 | 1.509 | 1.266 | 1.192 | no |
| 20 | 7.225 | 2.26 | 3.197 | no |
| 30 | 12.95 | 4.792 | 2.702 | no |
| 40 | 23.11 | 7.775 | 2.972 | no |
| 50 | 25.43 | 10.94 | 2.324 | no |
| 60 | 22.43 | 15.64 | 1.434 | no |
| 70 | 31.27 | 21.16 | 1.478 | no |
| 80 | 146.9 | 32.37 | 4.539 | no |
| 90 | 67.23 | 54.39 | 1.236 | no |
| 100 | 241.5 | 98.55 | 2.451 | no |

Frozen 40/60-mm 25% error gate: **fail**.
Frozen profile Spearman gate: **pass**.

## Density tiers at 60 mm

| Sources | Modeled EF_ref | Digitized Yue | Modeled/paper |
|---:|---:|---:|---:|
| 13 | 1.006 | 1.209 | 0.832 |
| 53 | 2.122 | 3.007 | 0.706 |
| 105 | 5.42 | 6.151 | 0.881 |
| 181 | 10.73 | 11.08 | 0.969 |
| 229 | 15.61 | 12.15 | 1.285 |
| 277 | 22.43 | 14.06 | 1.595 |

Frozen increasing-density ordering gate: **pass**.

## Regional single-source profiles at 60 mm

| Region surrogate | Modeled normalized fluence | Digitized Yue | Modeled/paper |
|:---|---:|---:|---:|
| frontal_open_square | 1.071e-07 | 4.022e-06 | 0.027 |
| occipital_open_circle | 9.114e-09 | 7.006e-08 | 0.130 |
| temporal_open_triangle | 5.129e-09 | 1.235e-07 | 0.042 |
| parietal_filled_circle | 1.827e-08 | 4.497e-07 | 0.041 |
| north_pole_filled_square | 7.515e-08 | 1.211e-06 | 0.062 |

The four non-north regional coordinates were not reported by Yue; these values assess qualitative regional behavior using frozen directional surrogates and are not exact-coordinate acceptance tests.

## Uniformity boundary

Yue defines uniformity as spatial SD/mean but does not report the sampled spatial mask. Exact scalar reproduction is therefore not identifiable. The project reports four explicit alternatives and uses their direction with density as trend-only evidence.

| Sources | Intracranial raw | Whole-head raw | 40-mm shell | Five-axis median (20-60 mm) |
|---:|---:|---:|---:|---:|
| 13 | 4.659 | 30.42 | 2.652 | 1.047 |
| 53 | 2.639 | 15.17 | 2.004 | 0.8222 |
| 105 | 2.381 | 10.79 | 1.781 | 0.8218 |
| 181 | 2.229 | 8.138 | 1.804 | 0.7679 |
| 229 | 2.224 | 7.244 | 1.916 | 0.8622 |
| 277 | 2.196 | 6.577 | 2.038 | 0.9353 |

## Known sources of discrepancy

- The paper's SPM12 five-tissue segmentation and preprocessing parameters are unavailable; the project uses a separately documented Colin27 derivative.
- Per-ring azimuth phases and lower-density coordinates are unreported; the project uses frozen deterministic approximations.
- The paper omits refractive indices; the project uses `n=1.0` for all media in this version.
- The paper calls deposited weight photon flux, whereas this implementation records MCX normalized fluence.
- Regional source coordinates and the uniformity mask are unreported and cannot be exactly reconstructed.
