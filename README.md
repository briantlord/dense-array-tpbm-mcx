# Dense-array tPBM Monte Carlo research

This project models near-infrared light transport through a labeled head atlas using Python and the standalone MCX-CL simulator. The current research compares **810 nm and 1070 nm across a 277-source, Yue-derived surrogate array**.

The results are conditional simulations of light transport. They are not measured device dose, a validated device model, or evidence of biological efficacy.

## Start here

- **[Current research status](CURRENT_STATE.md):** current versus historical scenarios and unresolved work.
- **[Qualified wavelength comparison](results/review_comparison_public_20260905_v1/report.md):** results, uncertainty checks, and corrected overlap comparison.
- **[Regional absorption report](results/surrogate_yue277_810_vs_1070_regional_absorbed_energy_v2/report.md):** tissue and depth summaries with unsupported ratios suppressed.
- **[Project review](reviews/PROJECT_REVIEW_2026-09-04.md)** and **[task list](TASKS.md):** quality assessment and remaining work.

## Current findings

The saved bases use the same spatial source layout and total launched-energy normalization:

| Provisional scenario | Total brain absorption | Integrated brain fluence, relative to corrected 1070 |
|---|---:|---:|
| Corrected 1070 nm, fat absorption 0.010 mm^-1 | 1.21425% | 1.000 |
| Refined 810 nm | 1.13355% | 2.323 |

Absorption and fluence are different observables. These results do not establish an overall wavelength winner.

An independent **18-run Monte Carlo audit** tested both wavelengths with repeated seeds, two photon counts, and a longer time window. **18 of 21 endpoint ratios passed** the declared numerical screening criteria. All three ratios at depths of 50 mm or more failed and are suppressed in the revised report. These checks address sampling and selected numerical stability; they do not include optical-property, anatomy, placement, or coupling uncertainty.

The earlier high-fat 1070 results remain a historical sensitivity baseline. Use the **corrected 1070 comparator**, not the original high-fat overlap maps, for current comparisons. The [scenario inventory](provenance/scenario_inventory_20260904_v1.json) identifies the bases and their roles.

## What this public repository contains

It includes code, schemas, configurations, compact run records, project-generated reports and plots, source citations, and checksum/provenance records.

**Manufacturer information, device images, and research-paper files are excluded.** Citations and research-source metadata remain. Some documentation is a redacted publication copy; the complete original research workspace is retained locally. Simulation plots are research visualizations, not device images.

Large raw simulation fields, most downloaded anatomy, the local simulator binary, and Python environments are also excluded. A GitHub clone is therefore **not a complete backup of the research data**. See [restore instructions](provenance/RESTORE.md) and [publication provenance](provenance/GITHUB_SYNC.md).

## Install and run software checks

Use **Python 3.13** and [uv](https://docs.astral.sh/uv/). No GPU or raw simulation data is needed for the portable checks.

```sh
git clone https://github.com/briantlord/dense-array-tpbm-mcx.git
cd dense-array-tpbm-mcx
uv sync --frozen --group dev
uv run --frozen python scripts/check_software.py
```

These commands work in a shell or PowerShell and use `.venv` by default. If you use the existing Windows `.venv-win` convention, set `$env:UV_PROJECT_ENVIRONMENT = ".venv-win"` before running them.

The [GitHub Actions workflow](.github/workflows/software.yml) runs the same portable checks. The complete local suite additionally checks research artifacts that may be absent from a clone; run `uv run --frozen pytest -q` after restoring its required data.

## Publication privacy

Personal directory prefixes have been removed from published records, and published commit identities use GitHub no-reply addresses. Numerical results are unchanged. The [redaction record](provenance/publication_redactions_20260905.json) lists original and public file digests; original provenance hashes still refer to the preserved research originals.

Before contributing, configure your GitHub-provided no-reply email and enable the checked-in push hook:

```sh
git config user.email YOUR_GITHUB_NOREPLY_ADDRESS
git config core.hooksPath .githooks
uv run --frozen python scripts/check_publication.py --ref HEAD --history
```

The hook checks outgoing branch history for personal paths, unapproved emails, credential patterns, excluded documents, and unreviewed image/binary assets. CI repeats the check. After staging changes, run `uv run --frozen python scripts/check_publication.py` to check the staged files. New binary assets require a deliberate review and an update to the [publication policy](provenance/publication_policy.json).

The September 2026 privacy cleanup rewrote public history. Existing clones must be replaced or carefully reconciled before contributing; old branches must not be merged back. See [publication notes](provenance/GITHUB_SYNC.md).

## Reproduce analyses or launch new simulations

1. Select a versioned scenario from [CURRENT_STATE.md](CURRENT_STATE.md). Do not substitute historical defaults for a current comparison.
2. Restore the required anatomy and native fields and verify their recorded SHA-256 checksums using [RESTORE.md](provenance/RESTORE.md).
3. Regenerate reports using their associated script and a new output identity, or an isolated checkout where that output is absent. Frozen outputs must not be overwritten.
4. For new GPU work, obtain the exact MCX-CL executable recorded by the environment and prepare a new versioned run binding. The runner checks executable identity, GPU, geometry, optical coefficients, and supported input scope before execution.

The validated implementation uses **MCX-CL v2025.10 through OpenCL** on Apple Silicon and Windows/NVIDIA. The Windows records identify an RTX 3080 Ti. The separate CUDA backend remains unvalidated. Current source/grid adapters support pencil sources and orthogonal, 1-mm voxels.

The [Windows handoff](WINDOWS_RTX3080TI_HANDOFF.md) and [environment notes](ENVIRONMENT.md) document the historical setup. Their prepared plans and completed directories retain their original identities; they are not instructions to overwrite existing runs.

## Scientific limitations and next work

- Optical tables are provisional; unresolved production optical cells remain blocked.
- The Yue quantitative external benchmark still fails its declared tolerance. Internal consistency is not independent experimental validation.
- Current regions are whole gray matter, white matter, their union, and geometric depth shells. Validated cortical-ribbon and named target-region masks remain to be added.
- Broader parameter uncertainty and the inputs needed for a validated device model remain future work.

Read [MODEL_SPEC.md](MODEL_SPEC.md), [VALIDATION_AND_SENSITIVITY.md](VALIDATION_AND_SENSITIVITY.md), and [REFERENCES.md](REFERENCES.md) for the model contracts, validation plan, and literature sources.
