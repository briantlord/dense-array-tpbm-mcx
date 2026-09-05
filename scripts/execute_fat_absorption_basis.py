#!/usr/bin/env python3
"""Execute a prepared fat-absorption basis index sequentially and resumably.

This local runner mirrors ``execute_basis_index.py``. It exists because the
tracked generic runner can be an unhydrated OneDrive placeholder on Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any

from mcx_project.basis import BasisExecutionError, execute_basis_run
from mcx_project.standalone import probe_mcxcl, resolve_mcxcl_binary, standalone_field_from_config
from mcx_project.validation import load_json


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json_with_sync_retry(path: Path, value: Any) -> None:
    """Replace JSON atomically, tolerating short OneDrive file locks."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(20):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.5)
    finally:
        temporary.unlink(missing_ok=True)


def _repair_completed_sync_failure(manifest_path: Path, root: Path) -> bool:
    """Recover a complete MCX run whose final manifest rename was sync-locked."""

    manifest = load_json(manifest_path)
    if manifest.get("status") != "failed" or "PermissionError" not in str(
        manifest.get("error")
    ):
        return False
    run_directory = manifest_path.parent
    execution_path = run_directory / "execution.json"
    summary_path = run_directory / "summary.json"
    required = {
        "volume.uint8.bin": "qc",
        "mcx_input.json": "qc",
        "mcxcl.log": "log",
        "mcx_field.jnii": "fluence",
    }
    if not execution_path.is_file() or not summary_path.is_file():
        return False
    execution = load_json(execution_path)
    summary = load_json(summary_path)
    if execution.get("status") != "complete" or summary.get("run_id") != manifest["run_id"]:
        return False
    engine = summary.get("engine", {})
    declared_hashes = {
        "volume.uint8.bin": engine.get("prepared_volume_sha256"),
        "mcx_input.json": engine.get("input_sha256"),
        "mcxcl.log": engine.get("log_sha256"),
        "mcx_field.jnii": engine.get("jnifti_sha256"),
    }
    for name, declared in declared_hashes.items():
        artifact = run_directory / name
        if not artifact.is_file() or not declared or _sha256_file(artifact) != declared:
            return False

    def record(path: Path, kind: str) -> dict[str, str]:
        return {
            "kind": kind,
            "path": path.resolve().relative_to(root).as_posix(),
            "sha256": _sha256_file(path),
        }

    manifest["outputs"] = [
        record(summary_path, "summary"),
        record(execution_path, "log"),
        *(record(run_directory / name, kind) for name, kind in required.items()),
    ]
    manifest["status"] = "complete"
    manifest["error"] = None
    _atomic_json_with_sync_retry(manifest_path, manifest)
    return True


def _reset_preexecution_sync_failure(manifest_path: Path) -> bool:
    """Reset only a sync-lock failure proven to have occurred before MCX ran."""

    manifest = load_json(manifest_path)
    if manifest.get("status") != "failed" or "PermissionError" not in str(
        manifest.get("error")
    ):
        return False
    run_directory = manifest_path.parent
    executed_artifacts = (
        "execution.json",
        "summary.json",
        "volume.uint8.bin",
        "mcx_input.json",
        "mcxcl.log",
        "mcx_field.jnii",
    )
    if any((run_directory / name).exists() for name in executed_artifacts):
        return False
    failure = run_directory / "failure.json"
    archived_failure = run_directory / "preexecution_sync_failure.json"
    if not failure.is_file() or archived_failure.exists():
        return False
    for attempt in range(20):
        try:
            os.replace(failure, archived_failure)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.5)
    manifest["status"] = "planned"
    manifest["error"] = None
    manifest["outputs"] = []
    _atomic_json_with_sync_retry(manifest_path, manifest)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--limit", type=int)
    parser.add_argument("--continue-on-error", action="store_true")
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    index_path = arguments.index.resolve()
    if not index_path.is_relative_to(root):
        raise SystemExit("index must be inside the project root")
    index = load_json(index_path)
    runs = index["runs"]
    if arguments.limit is not None:
        if arguments.limit < 1:
            raise SystemExit("--limit must be positive")
        runs = runs[: arguments.limit]
    binary = resolve_mcxcl_binary(root)
    identity = probe_mcxcl(binary)
    complete = 0
    skipped = 0
    failed = 0

    def execute(config: dict[str, Any], run_directory: Path):
        return standalone_field_from_config(
            config,
            run_directory,
            binary,
            project_root=root,
            expected_identity=identity,
        )

    for number, run in enumerate(runs, start=1):
        manifest_path = root / run["manifest_path"]
        reset_after_sync_lock = _reset_preexecution_sync_failure(manifest_path)
        if reset_after_sync_lock:
            print(
                json.dumps(
                    {
                        "basis_set_id": index["basis_set_id"],
                        "emitter_id": run["emitter_id"],
                        "number": number,
                        "status": "reset_after_preexecution_sync_lock",
                        "total": len(runs),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        try:
        status = execute_basis_run(manifest_path, root, execute, engine_probe=lambda: identity)
            complete += status == "complete"
            skipped += status == "skipped"
            print(
                json.dumps(
                    {
                        "basis_set_id": index["basis_set_id"],
                        "emitter_id": run["emitter_id"],
                        "number": number,
                        "status": status,
                        "total": len(runs),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        except BasisExecutionError as error:
            if _repair_completed_sync_failure(manifest_path, root):
                complete += 1
                print(
                    json.dumps(
                        {
                            "basis_set_id": index["basis_set_id"],
                            "emitter_id": run["emitter_id"],
                            "number": number,
                            "status": "complete_after_sync_lock_repair",
                            "total": len(runs),
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                continue
            failed += 1
            print(
                json.dumps(
                    {
                        "basis_set_id": index["basis_set_id"],
                        "emitter_id": run["emitter_id"],
                        "error": str(error),
                        "number": number,
                        "status": "failed",
                        "total": len(runs),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            if not arguments.continue_on_error:
                raise SystemExit(2) from error
    print(
        json.dumps(
            {
                "basis_set_id": index["basis_set_id"],
                "complete": complete,
                "failed": failed,
                "skipped": skipped,
                "status": "complete" if failed == 0 else "completed_with_failures",
                "total": len(runs),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
