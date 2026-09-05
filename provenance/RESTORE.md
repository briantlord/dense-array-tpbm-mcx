# Restore and reproduction

The reviewed state is preserved at `e183ac4f`. Keep the hardening branch too: it contains historical source snapshots, the current scenario index, improved checks and the new analyses. Exact line endings are deliberately retained by `.gitattributes`.

GitHub uses a separately prepared history that excludes publisher papers. Some original local revision IDs are not reachable from that history. See `GITHUB_SYNC.md`; use the exact source snapshots for hash verification and retain the original local repository for revision-based recovery.

## Historical code

`historical_analyzers_v1.json` identifies the original 1070 analyzer and the reviewed shared analyzer/810 entrypoint. `legacy_analysis_source_recovery_v1.json` identifies reviewed fat, water and regional scripts whose original manifests omitted code identity. The latter is a recovery supplement, not retrospective proof of execution provenance.

`mcx_project.provenance.resolve_recorded_code` accepts the current path only if its hash matches; otherwise it requires an exact content-addressed snapshot. Never update a historical result's code checksum merely to make a test pass. To rerun old scripts, restore the original relative directory structure and their corresponding source revision in an isolated checkout; running a snapshot directly inside its hash directory changes its inferred project root.

## Large artifacts

The working OneDrive project currently holds the native fields and anatomy. No separate verified archival mirror has been identified. `external_artifacts_20260904_v1.json` lists the available non-Git artifacts referenced by the three controlling comparison bases and result manifests; its scope is recorded inside the inventory. It is not a backup.

Read-only check from the project root:

```powershell
.\.venv-win\Scripts\python.exe scripts/restore_artifacts.py --inventory provenance/external_artifacts_20260904_v1.json
```

Restore missing files from an independently retained mirror with the same relative layout:

```powershell
.\.venv-win\Scripts\python.exe scripts/restore_artifacts.py --inventory provenance/external_artifacts_20260904_v1.json --source D:\MCX-archive
```

The example drive is a placeholder, not a verified location. The tool verifies source and destination SHA-256, rejects escaping paths and corrupt mirrors, and never overwrites an existing artifact. Preserve a corrupted local file for investigation before arranging a separate recovery. Synthetic tests exercise successful restore, corrupt mirror and local-overwrite rejection.

For new compute, use an isolated local checkout on a local disk and archive completed immutable directories after execution. Do not move a live run or its lock between machines. Retain relative paths and verify the archive against this inventory. No automatic folder move or OneDrive reconfiguration has been performed.

## Regeneration

Restore anatomy from its recorded acquisition/derivation metadata and checksum, install the frozen Python environment, and obtain the exact MCX binary recorded in the Windows environment. Native fields can be recomputed from the frozen basis index/manifest configuration, but hardware/runtime stochastic differences may prevent bit-identical field hashes. Such a recomputation is a **new versioned run**, not a checksum substitute for a missing historical field. Preparation and execution refuse completed directories; use new plan/run identities and rerun the declared validation gates.

The corrected overlap is reproducible with:

```powershell
.\.venv-win\Scripts\python.exe scripts/analyze_surrogate_1070_windows_basis.py --spec configs/corrected_1070_overlap_20260904_v1.json
```

Use a new output identity to repeat it, or an isolated restored checkout where that output is absent. The convergence audit likewise has a frozen protocol and refuses an existing output directory. Its native fields, inputs, logs and summaries are checksum-addressed by its result manifest.
