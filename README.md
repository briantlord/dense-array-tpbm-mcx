# 1070-nm Dense-Array tPBM Monte Carlo Project

This repository is a Python-first, provenance-gated workflow for MCX-family photon-transport simulations. It uses PMCXCL/MCX-CL on Apple Silicon and PMCX/MCX on NVIDIA CUDA systems. MATLAB is optional and is not required for production execution.

The repository is currently at the V0 scaffold stage. All numeric fixtures under `inputs/synthetic_test_only/` are software-test values and must not be interpreted as tissue or device measurements.

## Environment

The project is pinned to Python 3.13. From the repository root:

```bash
UV_CACHE_DIR=/tmp/mcx-project-uv-cache uv sync --extra opencl --group dev
```

This creates `.venv`, installs the Apple-Silicon OpenCL binding, and installs the test tools. On an NVIDIA CUDA host, replace `--extra opencl` with `--extra cuda`.

PMCXCL is pinned to the 0.7.1 macOS 14 wheel because the macOS 15 wheel for 0.7.1 and both macOS “universal2” wheels published for 0.7.2 contain an x86-64-only native extension and cannot load natively on Apple Silicon. The selected 0.7.1 wheel was inspected and contains an ARM64 extension. Revisit this direct wheel pin only after inspecting the replacement architecture and rerunning the smoke test.

## Validate the scaffold

From a clean checkout on the Apple Silicon host, install, test, preflight every referenced artifact, and execute the manifest-locked GPU smoke run with one command:

```bash
./scripts/verify_scaffold.sh
```

For a fast software-only check that does not launch the GPU:

```bash
.venv/bin/pytest
.venv/bin/mcx-project preflight \
  runs/synthetic_smoke_m4pro/manifest.json \
  --project-root .
```

Validate an individual JSON input against its schema:

```bash
.venv/bin/mcx-project validate \
  schemas/emitter_geometry.schema.json \
  inputs/synthetic_test_only/emitter_geometry.json \
  --require-complete
```

## Probe and smoke-test the M4 Pro

```bash
.venv/bin/mcx-project probe-opencl
.venv/bin/mcx-project smoke-opencl \
  runs/synthetic_smoke_m4pro/manifest.json \
  --project-root .
```

The smoke command refuses to launch until the manifest, all seven referenced artifacts, their schemas, checksums, and cross-file invariants pass. The verified M4 Pro smoke run completed 100,000 photons, reported 27.20661% absorbed energy, and produced a spatially non-uniform 60 x 60 x 60 field. Its manifest and compact result are retained under `runs/synthetic_smoke_m4pro/`. The smoke run uses a homogeneous synthetic cube. It does not use production anatomy, optical properties, or helmet geometry.

## Scientific gate

Production simulation remains blocked until the anatomy, optical-property, hardware, registration, benchmark, and convergence gates in `PROJECT_PLAN.md` pass. A valid JSON file is not, by itself, a scientifically acceptable input.

## Per-emitter basis runner

The next execution layer prepares one immutable configuration and planned manifest per enabled emitter and replicate:

```bash
.venv/bin/mcx-project prepare-basis \
  configs/synthetic_basis_plan_v1.json \
  --project-root .
```

Execute one prepared synthetic run with:

```bash
.venv/bin/mcx-project execute-basis \
  runs/synthetic_two_emitter_basis_v1/syn001/r001/manifest.json \
  --project-root .
```

Preparation derives a deterministic independent seed from the basis-set ID, emitter ID, and replicate; refuses to replace changed generated files; and records the declared code revision. Execution preflights all inputs before launch, acquires an exclusive run lock, writes the full field and compact records atomically, skips a checksum-valid completed run, and preserves a failed run as immutable evidence. Retrying a failed source requires a replacement manifest with a new run ID.

The checked-in basis plan and generated manifests are synthetic software fixtures. Production basis preparation remains disabled until the scientific input gates pass and the runner is extended beyond the homogeneous synthetic-volume adapter.
