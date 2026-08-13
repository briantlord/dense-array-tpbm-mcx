# Execution Environment Record

## Verified Apple Silicon environment

Recorded 2026-08-13 from the local smoke-test environment:

| Component | Version/detail | License/status |
|---|---|---|
| macOS | 26.5, build 25F71, arm64 | host operating system |
| Hardware | MacBook Pro, Apple M4 Pro | 20 OpenCL compute units; 40,200,896,512 bytes reported global memory |
| Python | 3.13.12 | PSF License |
| uv | 0.8.12 | environment and lockfile tool |
| MCX-CL engine | v2025.10; official source commit `bf695e81e239359f92a8fdd845bcdcacc50a7c31`; local ARM64 build | GPLv3; built by `scripts/build_mcxcl.sh` |
| MCX-CL executable | `.local/bin/mcxcl`; locally reported revision 5233733 | ignored machine artifact; SHA-256 recorded per completed run |
| NumPy | 2.5.2 | SPDX expression recorded by package: BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| NiBabel | 5.4.2 | MIT; used for NIfTI header, affine, scaling, and label validation |
| SciPy | 1.18.0 | BSD-3-Clause; used for anatomy connectivity and distance-envelope QC |
| Pillow | 12.3.0 | HPND; used for deterministic anatomy QC renders |
| jsonschema | 4.26.0 | MIT |
| pytest | 9.1.1 | MIT |

The exact resolved Python dependency hashes are in `uv.lock`. PMCXCL 0.7.1 was evaluated but removed from the execution environment after its returned NumPy field proved intermittently corrupt; PMCXCL 0.7.2's nominal macOS universal wheels were also locally observed to contain x86-64-only extensions. The runner therefore uses the pinned standalone source build and records its executable hash with each completed run.

## Declared but unverified CUDA environment

PMCX 0.7.1 is locked as the optional CUDA binding. It is not installed in the Apple OpenCL environment, and no CUDA GPU, driver, runtime, engine build, or backend-equivalence result has been recorded. Those fields must be captured on the actual NVIDIA host before a CUDA result can enter a frozen basis set.

Environment recording establishes software provenance; it is not anatomy, hardware, benchmark, or scientific validation.
