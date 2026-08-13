# Yue 2015 approximation v1

This directory defines the executable 850-nm benchmark approximation. It is not an exact reconstruction of the unpublished MCXLAB configuration.

## Frozen reported inputs

- 850 nm;
- the five `mua` and reduced-scattering rows from Table 2, in `mm^-1`;
- 1-mm Colin27 anatomy;
- the Table-1 layer elevations and counts totaling 277 sources;
- inward source axes, unit initial source weight, and `10^9` photons per source for the eventual paper-scale comparison;
- density counts 13, 53, 105, 181, 229, and 277.

## Declared project approximations

- `colin27_2008_yue5_1mm_v1` is derived from the accepted native-label atlas, not the paper's unavailable SPM12 segmentation.
- Native vessels are assigned spatially to the nearest non-vessel tissue; they are not globally mapped to scalp or brain.
- Every elevation ring begins at zero azimuth because the paper omits per-ring phase.
- Lower-density tiers are deterministic nested farthest-point subsets seeded at the north pole because their coordinates are not reported.
- The executable comparison uses a zero-width pencil source. The paper's Gaussian width is not reported; Figure 4's enhancement ratio is explicitly the pencil comparison.
- The paper reports reduced scattering and an isotropic assumption. This implementation sets `g=0` and therefore `mus=musp`.
- The paper says approximate refractive indices were used but does not give them. Version 1 sets every `n=1.0` to remove an otherwise arbitrary boundary mismatch. Refractive-index sensitivity remains required.
- The output contract is MCX normalized fluence. This is deliberately distinguished from the paper's deposited photon weight, which it calls photon flux.

## Rebuild and validate

The official Colin27 source and accepted native derivative must already exist locally. Then run:

```bash
.venv/bin/python scripts/build_yue2015_approx_v1.py
.venv/bin/mcx-project preflight \
  benchmarks/yue2015_approx_v1/template_manifest.json \
  --project-root .
```

The ignored five-tissue NIfTI is reconstructed locally. Tracked outputs include its metadata, derivation transitions, compact QC, the 277-source geometry and visualization, nested density tiers, optical table, calibration convention, registration, base MCX configuration, and manifest.

`configs/yue2015_approx_v1_basis_plan.json` defines the 277 independent, unit-source, one-billion-photon pencil runs. Do not launch that full plan until photon-count and replicate convergence tiers are frozen; its presence records the paper-scale target, not a claim that the computation has run.

## Current validation boundary

A 100,000-photon north-pole implementation check passed on standalone MCX-CL v2025.10 using the Apple M4 Pro OpenCL device. It verified the real label-volume adapter and produced a finite, nonuniform `181 x 217 x 181 x 1` field. It is not a convergence result, a Yue curve reproduction, or evidence that the benchmark gate has passed.
