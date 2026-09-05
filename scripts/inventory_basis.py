#!/usr/bin/env python3
"""Checksum-preflight a completed basis and write a compact immutable inventory."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcx_project.hashing import sha256_file
from mcx_project.preflight import preflight_manifest
from mcx_project.validation import load_json


def _write_immutable(path: Path, value: dict[str, Any]) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise RuntimeError(f"refusing to replace inventory: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory-id", required=True)
    parser.add_argument("--equivalence", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.project_root.resolve()
    index_path = (root / args.index).resolve()
    output_path = (root / args.output).resolve()
    equivalence_path = (root / args.equivalence).resolve()
    for path in (index_path, output_path, equivalence_path):
        if not path.is_relative_to(root):
            raise SystemExit(f"path escapes project root: {path}")
    index = load_json(index_path)
    equivalence = load_json(equivalence_path)
    if not equivalence.get("all_thresholds_pass"):
        raise SystemExit("backend equivalence gate does not pass")

    status_counts: dict[str, int] = {}
    native_fields = 0
    output_bytes = 0
    for number, row in enumerate(index["runs"], start=1):
        manifest_path = root / row["manifest_path"]
        preflight_manifest(manifest_path, root)
        manifest = load_json(manifest_path)
        status = manifest["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        fluence = [record for record in manifest["outputs"] if record["kind"] == "fluence"]
        if status != "complete" or len(fluence) != 1:
            raise SystemExit(f"incomplete or invalid native field at basis row {number}")
        field_path = root / fluence[0]["path"]
        if sha256_file(field_path) != fluence[0]["sha256"]:
            raise SystemExit(f"native field checksum mismatch at basis row {number}")
        native_fields += 1
        output_bytes += field_path.stat().st_size
        if number == 1 or number % 25 == 0 or number == len(index["runs"]):
            print(f"preflighted {number}/{len(index['runs'])} manifests", flush=True)

    inventory = {
        "inventory_id": args.inventory_id,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "basis_set_id": index["basis_set_id"],
        "index_path": index_path.relative_to(root).as_posix(),
        "index_sha256": sha256_file(index_path),
        "manifest_count": len(index["runs"]),
        "manifest_status_counts": status_counts,
        "checksum_preflight_manifest_count": len(index["runs"]),
        "native_fluence_field_count": native_fields,
        "native_fluence_bytes": output_bytes,
        "failure_record_count": 0,
        "failure_records": [],
        "backend_equivalence_path": equivalence_path.relative_to(root).as_posix(),
        "backend_equivalence_sha256": sha256_file(equivalence_path),
        "backend_equivalence_passed": True,
        "scientific_status": (
            "provisional_yue_derived_spatial_surrogate_not_target_helmet_"
            "not_measured_dose_not_biological_efficacy"
        ),
    }
    _write_immutable(output_path, inventory)
    print(json.dumps(inventory, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
