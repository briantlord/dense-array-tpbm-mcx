# Yue five-tissue derivative QC

Status: accepted for the declared approximation, not an exact reconstruction.

- Shape: `[181, 217, 181]` at 1 mm isotropic.
- Labels: `{0: 3286799, 1: 1363120, 2: 447791, 3: 358004, 4: 1012425, 5: 640998}`.
- Vessel reassignment is spatial (nearest non-vessel tissue), not a global merge.
- 277 source rays intersect the head; every inward normal is unit length.
- Density tiers are nested deterministic farthest-point subsets.
- Template preflight validated 7 artifacts and 8 checksums.

The source coordinates, refractive indices, beam width, boundary settings, and output interpretation remain declared approximations because the paper does not report enough information to reconstruct them uniquely.
