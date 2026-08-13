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

## Colin27 anatomy source

The official MNI Colin27 high-resolution 2008 NIfTI release is the selected anatomy source and is documented under `inputs/anatomy/colin27_2008/`. Its large source images and download archive are intentionally ignored by Git; acquisition is reproducible with:

```bash
scripts/acquire_colin27.sh
```

The accepted anatomy derivative is `colin27_2008_native12_1mm_v3`: 181 x 217 x 181 voxels at 1-mm isotropic resolution with all native tissue identities retained. Reproduce it and its QC artifacts with:

```bash
.venv/bin/python scripts/derive_colin27_1mm.py
```

The anatomy metadata passes the fail-closed schema gate and automated plus visual anatomy QC. It is not yet a complete production simulation input because wavelength-specific optical properties, emitter registration, and ROI mapping remain separate gates. See the anatomy README for the source NIfTI scaling hazard and the documented removal of a superior field-of-view artifact.

## Research ledgers

- `literature/novelty_search_2026-08-13.md` documents the current novelty search, screened precedents, and allowed claim language.
- `literature/novelty_screening_2026-08-13.csv` is the machine-readable screening table.
- `benchmarks/yue_2015_benchmark_ledger.md` defines what can and cannot be reproduced from the Yue and Humayun paper.
- `benchmarks/yue_2015_parameter_ledger.csv` classifies each benchmark field as reported, inferred, missing, inconsistent, or a project decision.

The search rules out a broad “first multisource 1064/1070-nm simulation” claim: frontal 1064-nm LED-array simulations already exist. The remaining candidate gap is the combined dense whole-head 1070-nm helmet and emitter-resolved cortical-overlap analysis.

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
