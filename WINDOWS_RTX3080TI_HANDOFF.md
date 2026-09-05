# Windows RTX 3080 Ti replacement handoff: 277-source surrogate basis

This versioned replacement exists because the Windows host reports `NVIDIA GeForce RTX 3080 Ti`, not the `NVIDIA GeForce RTX 3080` required by `WINDOWS_RTX3080_HANDOFF.md`. The original plan must remain unused on this host because it would record false device provenance.

## Non-negotiable boundaries

- Do not execute `runs/surrogate_yue277_1070_basis_v1/index.json` on Windows. It is bound to the Apple M4 Pro, macOS arm64, and the Apple OpenCL build.
- Do not use the original RTX 3080 Windows plan on the RTX 3080 Ti.
- Use only the official MCX-CL v2025.10 Windows executable through NVIDIA OpenCL. CUDA `mcx.exe` and PMCX remain separate, unvalidated backends.
- Execute only `SUR1070_011` until the backend-equivalence result passes.
- Preserve the provisional-science boundary: this is a Yue-derived spatial surrogate, not the target helmet, measured dose, or evidence of biological efficacy.

The machine-readable checkpoint is `handoff/windows_rtx3080ti/state.json`. It retains the frozen scientific inputs and thresholds from the original handoff while binding new environment and run identifiers to the exact Ti device.

## Required sequence

1. Confirm that Git is clean, the checkpoint commit is present, the frozen hashes match, and at least 24 GB of disk space remains available.

2. Obtain the official MCX-CL v2025.10 Windows executable. Then run:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\scripts\windows_preflight.ps1 -Target rtx3080ti -McxclBinary "C:\path\to\mcxcl.exe"
   ```

   Preflight creates `.venv-win`, installs the project and tests, checks the frozen surrogate inputs, probes the real executable and OpenCL device, and writes a distinct RTX 3080 Ti environment, template, and plan. It does not prepare manifests or execute fields.

3. Inspect these immutable generated artifacts. They must name Windows, MCX-CL v2025.10, and `NVIDIA GeForce RTX 3080 Ti`, and record the actual executable hash:

   - `environment/windows_rtx3080ti_opencl_v1.json`
   - `runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_v1/template_manifest.json`
   - `configs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1.json`

4. Prepare the distinct manifests:

   ```powershell
   $Python = ".\.venv-win\Scripts\python.exe"
   $env:MCXCL_BINARY = "C:\path\to\mcxcl.exe"
   & $Python -m mcx_project.cli prepare-basis configs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1.json --project-root .
   ```

5. Execute only the representative anterior source and compare it with the saved M4 Pro three-replicate mean:

   ```powershell
   & $Python scripts/windows_backend_equivalence.py `
     --index runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1/index.json `
     --output results/surrogate_yue277_1070_windows_rtx3080ti_opencl_v1/backend_equivalence.json `
     --project-root .
   ```

   The frozen thresholds remain unchanged: every gray-matter, white-matter, and total-brain integral must be within 5% symmetric relative change, and the median valid 20-60 mm profile difference must be at most 10%.

6. Stop if the equivalence result fails, the OpenCL device is not exactly the RTX 3080 Ti, or the engine is not v2025.10. Never edit a failed or completed run in place.

7. If equivalence passes, commit the verified environment, template, plan, prepared manifests, representative-run records, and equivalence result before releasing the batch. Prevent Windows sleep, start a transcript, and run:

   ```powershell
   Start-Transcript -Path .\windows_277_rtx3080ti_run_transcript.log
   & $Python scripts/execute_basis_index.py runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1/index.json --project-root .
   Stop-Transcript
   ```

The compute stage is complete only when all 277 RTX 3080 Ti manifests are complete, all output checksums preflight, and a compact post-run inventory records elapsed time, failures, engine identity, and disk usage.
