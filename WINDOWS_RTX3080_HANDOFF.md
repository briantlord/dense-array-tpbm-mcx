# Windows RTX 3080 handoff: 277-source surrogate basis

This is the authoritative start point for the Windows chat. The scientific inputs and 100-million-photon run size are ready, but the 277 fields have **not** been executed.

## Non-negotiable boundary

Do **not** execute `runs/surrogate_yue277_1070_basis_v1/index.json` on Windows. That index and its manifests explicitly record the Apple M4 Pro, macOS arm64, and the local Apple OpenCL build. Reusing them would make the execution provenance false even if MCX-CL happened to run.

The supported handoff path is the official **MCX-CL v2025.10** Windows executable using the RTX 3080 through NVIDIA OpenCL. The repository's tested standalone adapter is for MCX-CL. A CUDA `mcx.exe` or PMCX run is a separate backend implementation and validation task; do not substitute it into this plan.

## What is frozen

- Geometry: 277 enabled pencil sources in the Yue-derived spatial surrogate.
- Anatomy: Colin27 native12 1-mm, five modeled labels.
- Optical scenario: `provisional_1070_v1`.
- Photon count: 100,000,000 per source, one replicate.
- Convergence evidence: five-region 100-million-photon extension passed the frozen checks.
- Scientific scope: provisional computational surrogate, not the eventual helmet and not biological efficacy or measured dose.

The machine-readable checkpoint is in `handoff/windows_rtx3080/state.json`.

## First message for the new Windows chat

Paste this into the new chat:

> Read `WINDOWS_RTX3080_HANDOFF.md` and `handoff/windows_rtx3080/state.json` completely. Inspect the repository and Git status before changing anything. Do not execute the Apple-bound basis index. Set up the official MCX-CL v2025.10 Windows binary on the RTX 3080, run `scripts/windows_preflight.ps1`, prepare the distinct Windows basis manifests, execute only the SUR1070_011 equivalence field, and release the remaining batch only if `backend_equivalence.json` passes. Preserve all provisional-science boundaries and commit the Windows environment/plan artifacts before the long batch if their provenance is correct.

## Windows sequence

1. Let OneDrive finish syncing, make the project folder locally available, and confirm adequate free disk space. The full set is expected to occupy roughly 12 GB, plus temporary and synchronization overhead.

2. Open PowerShell in the project root. Confirm that Git is clean and that this handoff commit is present.

3. Obtain the official MCX-CL **v2025.10** Windows executable. Do not use an unversioned binary. Then run:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\scripts\windows_preflight.ps1 -McxclBinary "C:\path\to\mcxcl.exe"
   ```

   This creates `.venv-win`, installs the project, runs the test and freshness gates, probes the real executable and GPU, and writes a new environment-bound template and plan. It does not prepare or execute fields.

4. Inspect these newly generated files. They must name Windows, MCX-CL v2025.10, and NVIDIA GeForce RTX 3080, and contain the actual executable hash:

   - `environment/windows_rtx3080_opencl_v1.json`
   - `runs/surrogate_yue277_1070_windows_opencl_v1/template_manifest.json`
   - `configs/surrogate_yue277_1070_windows_opencl_basis_v1.json`

5. Prepare the distinct Windows run index:

   ```powershell
   $Python = ".\.venv-win\Scripts\python.exe"
   $env:MCXCL_BINARY = "C:\path\to\mcxcl.exe"
   & $Python -m mcx_project.cli prepare-basis configs/surrogate_yue277_1070_windows_opencl_basis_v1.json --project-root .
   ```

6. Execute only the representative anterior source and compare it with the saved M4 Pro three-replicate mean:

   ```powershell
   & $Python scripts/windows_backend_equivalence.py --index runs/surrogate_yue277_1070_windows_opencl_basis_v1/index.json --project-root .
   ```

   This runs `SUR1070_011` at 100 million photons. It passes only when all gray-matter, white-matter, and total-brain integrals are within 5% symmetric relative change and the median valid 20–60 mm profile difference is at most 10%. The result is written to `results/surrogate_yue277_1070_windows_opencl_v1/backend_equivalence.json`.

7. Stop if the equivalence result fails, if the GPU is not the RTX 3080, or if the engine is not v2025.10. Diagnose and version a replacement plan; never edit a failed or completed run in place.

8. If the equivalence result passes, prevent Windows sleep, start a PowerShell transcript, and run the resumable batch:

   ```powershell
   Start-Transcript -Path .\windows_277_run_transcript.log
   & $Python scripts/execute_basis_index.py runs/surrogate_yue277_1070_windows_opencl_basis_v1/index.json --project-root .
   Stop-Transcript
   ```

   `SUR1070_011` will be checksum-verified and skipped because it is already complete. The runner stops on the first failure. Rerunning the same command safely skips verified completed runs, but a failed immutable manifest requires a versioned replacement rather than an overwrite.

## Completion condition

The compute stage is complete only when all 277 Windows manifests are `complete`, every output checksum preflights, and a compact post-run inventory records elapsed time, failures, engine identity, and disk usage. Field generation alone does not establish target-helmet performance; aggregation and the prespecified single-source/total-field depth and enhancement analyses follow afterward.
