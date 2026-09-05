#!/usr/bin/env python3
"""Preflight a completed Windows basis and write a compact immutable inventory."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcx_project.hashing import sha256_file
from mcx_project.preflight import preflight_manifest
from mcx_project.validation import load_json


def _project_path(root: Path, value: Path) -> Path:
    path = value if value.is_absolute() else root / value
    path = path.resolve()
    if not path.is_relative_to(root):
        raise RuntimeError(f"path escapes project root: {value}")
    return path


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _transcript_time(text: str, label: str) -> datetime:
    prefix = f"{label}: "
    values = [line.removeprefix(prefix) for line in text.splitlines() if line.startswith(prefix)]
    if len(values) != 1:
        raise RuntimeError(f"transcript must contain exactly one {label}")
    return datetime.strptime(values[0], "%Y%m%d%H%M%S")


def _write_immutable(path: Path, value: dict[str, Any]) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        raise RuntimeError(f"refusing to replace post-run inventory: {path}")
    if not path.exists():
        path.write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--equivalence", type=Path, required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()

    root = arguments.project_root.resolve()
    index_path = _project_path(root, arguments.index)
    environment_path = _project_path(root, arguments.environment)
    equivalence_path = _project_path(root, arguments.equivalence)
    transcript_path = _project_path(root, arguments.transcript)
    output_path = _project_path(root, arguments.output)
    index = load_json(index_path)
    environment = load_json(environment_path)
    equivalence = load_json(equivalence_path)
    if not equivalence.get("all_thresholds_pass"):
        raise RuntimeError("backend-equivalence result does not pass")

    statuses: dict[str, int] = {}
    execution_seconds = 0.0
    failures: list[str] = []
    native_fields = 0
    for row in index["runs"]:
        manifest_path = _project_path(root, Path(row["manifest_path"]))
        preflight_manifest(manifest_path, root)
        manifest = load_json(manifest_path)
        status = manifest["status"]
        statuses[status] = statuses.get(status, 0) + 1
        failure_path = manifest_path.parent / "failure.json"
        if failure_path.exists():
            failures.append(failure_path.relative_to(root).as_posix())
        native_fields += sum(
            1 for output in manifest["outputs"] if output["kind"] == "fluence"
        )
        execution = load_json(manifest_path.parent / "execution.json")
        execution_seconds += (
            _parse_utc(execution["completed_at"])
            - _parse_utc(execution["started_at"])
        ).total_seconds()

    if statuses != {"complete": len(index["runs"])}:
        raise RuntimeError(f"basis is not complete: {statuses}")
    if failures:
        raise RuntimeError(f"basis contains failure records: {failures}")

    run_root = index_path.parent
    run_bytes = sum(path.stat().st_size for path in run_root.rglob("*") if path.is_file())
    transcript = transcript_path.read_text(encoding="utf-8-sig")
    transcript_start = _transcript_time(transcript, "Start time")
    transcript_end = _transcript_time(transcript, "End time")
    inventory = {
        "inventory_id": "surrogate_yue277_1070_windows_rtx3080ti_opencl_postrun_v1",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "basis_set_id": index["basis_set_id"],
        "index_path": index_path.relative_to(root).as_posix(),
        "index_sha256": sha256_file(index_path),
        "manifest_count": len(index["runs"]),
        "manifest_status_counts": statuses,
        "checksum_preflight_manifest_count": len(index["runs"]),
        "native_fluence_field_count": native_fields,
        "failure_record_count": len(failures),
        "failure_records": failures,
        "backend_equivalence_path": equivalence_path.relative_to(root).as_posix(),
        "backend_equivalence_sha256": sha256_file(equivalence_path),
        "backend_equivalence_passed": True,
        "environment_path": environment_path.relative_to(root).as_posix(),
        "environment_sha256": sha256_file(environment_path),
        "engine": {
            "backend": environment["backend"],
            "binding": environment["binding"],
            "device": environment["device"],
            "engine_version": environment["engine_version"],
            "executable_sha256": environment["executable_sha256"],
            "platform": environment["platform"],
            "code_revision": environment["code_revision"],
        },
        "batch_transcript_path": transcript_path.relative_to(root).as_posix(),
        "batch_transcript_sha256": sha256_file(transcript_path),
        "batch_started_local": transcript_start.isoformat(),
        "batch_completed_local": transcript_end.isoformat(),
        "batch_elapsed_seconds": (transcript_end - transcript_start).total_seconds(),
        "summed_field_execution_seconds": execution_seconds,
        "run_root_bytes": run_bytes,
        "free_disk_bytes_after_run": shutil.disk_usage(root).free,
        "scientific_status": (
            "provisional_yue_derived_spatial_surrogate_not_target_helmet_"
            "not_measured_dose_not_biological_efficacy"
        ),
    }
    _write_immutable(output_path, inventory)
    print(json.dumps(inventory, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
