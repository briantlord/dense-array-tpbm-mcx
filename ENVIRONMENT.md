# Execution Environment Record

## Verified Apple Silicon environment

Recorded 2026-08-13 from the local smoke-test environment:

| Component | Version/detail | License/status |
|---|---|---|
| macOS | 26.5, build 25F71, arm64 | host operating system |
| Hardware | MacBook Pro, Apple M4 Pro | 20 OpenCL compute units; 40,200,896,512 bytes reported global memory |
| Python | 3.13.12 | PSF License |
| uv | 0.8.12 | environment and lockfile tool |
| PMCXCL | 0.7.1 | GPLv3+ in installed package metadata; verified ARM64 wheel |
| MCX-CL engine | v2025.10, revision dc0f3e, OpenCL build 2026-05-01 | GPL family; exact engine banner retained in the smoke log/manifest |
| NumPy | 2.5.2 | SPDX expression recorded by package: BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| jsonschema | 4.26.0 | MIT |
| pytest | 9.1.1 | MIT |

The exact resolved dependency hashes are in `uv.lock`. The PMCXCL 0.7.1 macOS 14 wheel is intentionally pinned because it was locally inspected as ARM64-capable and passed the M4 Pro smoke test.

## Declared but unverified CUDA environment

PMCX 0.7.1 is locked as the optional CUDA binding. It is not installed in the Apple OpenCL environment, and no CUDA GPU, driver, runtime, engine build, or backend-equivalence result has been recorded. Those fields must be captured on the actual NVIDIA host before a CUDA result can enter a frozen basis set.

Environment recording establishes software provenance; it is not anatomy, hardware, benchmark, or scientific validation.
