# 1070-nm Dense-Array tPBM Monte Carlo Project

This repository is a Python-first, provenance-gated workflow for MCX-family photon-transport simulations. Python validates and orchestrates the official standalone MCX-CL executable on Apple Silicon; PMCX/MCX is reserved for a later NVIDIA CUDA backend. MATLAB is optional and is not required for production execution.

The repository is currently at the V0 scaffold stage. All numeric fixtures under `inputs/synthetic_test_only/` are software-test values and must not be interpreted as tissue or device measurements.

## Environment

The project is pinned to Python 3.13. From the repository root:

```bash
UV_CACHE_DIR=/tmp/mcx-project-uv-cache uv sync --group dev
./scripts/build_mcxcl.sh
```

This creates `.venv`, installs the test tools, checks out the official MCX-CL `v2025.10` source at commit `bf695e81e239359f92a8fdd845bcdcacc50a7c31`, and builds an ignored local ARM64 executable at `.local/bin/mcxcl`. On an NVIDIA CUDA host, install the optional backend with `uv sync --extra cuda --group dev` after its separate validation gate is implemented.

PMCXCL was evaluated but is not used by the runner: the current macOS wheel set has architecture inconsistencies, and the ARM64-loadable wheel intermittently returned corrupted in-process NumPy fields despite a successful GPU kernel. File-based JNIfTI output from the pinned standalone executable passed the same M4 Pro simulation and avoids that buffer boundary.

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

The smoke command refuses to launch until the manifest, all seven referenced artifacts, their schemas, checksums, and cross-file invariants pass. The standalone M4 Pro smoke run completed 100,000 photons, reported 27.20888% absorbed energy, and produced a spatially non-uniform 60 x 60 x 60 field. The earlier PMCXCL smoke provenance is retained under `runs/synthetic_smoke_m4pro/` as a legacy bootstrap record; new basis execution uses standalone MCX-CL. These runs use a homogeneous synthetic cube, not production anatomy, properties, or helmet geometry.

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
