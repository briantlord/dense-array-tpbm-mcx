#!/usr/bin/env python3
"""Analyze the completed 1070-nm fat-absorption bracket and baseline."""

from __future__ import annotations

import csv
import json
import sys
from mcx_project.provenance import capture_code
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from mcx_project.hashing import sha256_file
from mcx_project.standalone import load_jnii_field


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = Path("inputs/fat_absorption_bracket_v1/protocol.json")
OUTPUT_ROOT = Path("results/surrogate_yue277_1070_fat_absorption_bracket_v1")
BASELINE_FIELD = Path(
    "results/surrogate_yue277_1070_windows_rtx3080ti_opencl_analysis_v1/"
    "total_fluence_constant_total.npy"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_json(root: Path, path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "show", f"HEAD:{path.as_posix()}"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout)


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_npy(path: Path, value: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            np.save(stream, value, allow_pickle=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _strip_gate(field: np.ndarray) -> np.ndarray:
    while field.ndim > 3 and field.shape[-1] == 1:
        field = field[..., 0]
    return np.asarray(field, dtype=np.float64)


def _stream_total(root: Path, index_path: Path, shape: tuple[int, ...]) -> tuple[np.ndarray, dict[str, Any]]:
    index = _load_json(root / index_path)
    if len(index["runs"]) != 277:
        raise RuntimeError(f"{index_path} does not contain 277 runs")
    total = np.zeros(shape, dtype=np.float64)
    execution_seconds = 0.0
    for number, run in enumerate(index["runs"], start=1):
        manifest_path = root / run["manifest_path"]
        manifest = _load_json(manifest_path)
        if manifest["status"] != "complete":
            raise RuntimeError(f"incomplete manifest: {manifest_path}")
        fields = [row for row in manifest["outputs"] if row["kind"] == "fluence"]
        if len(fields) != 1:
            raise RuntimeError(f"manifest lacks one fluence field: {manifest_path}")
        field_record = fields[0]
        field_path = root / field_record["path"]
        if sha256_file(field_path) != field_record["sha256"]:
            raise RuntimeError(f"fluence checksum mismatch: {field_path}")
        field = _strip_gate(load_jnii_field(field_path))
        if field.shape != shape:
            raise RuntimeError(f"field shape mismatch: {field_path} {field.shape}")
        total += field
        execution_path = manifest_path.parent / "execution.json"
        execution = _load_json(execution_path)
        started = datetime.fromisoformat(execution["started_at"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(execution["completed_at"].replace("Z", "+00:00"))
        execution_seconds += (completed - started).total_seconds()
        if number == 1 or number % 25 == 0 or number == 277:
            print(f"verified and accumulated {index['basis_set_id']} {number}/277", flush=True)
    total /= 277.0
    return total, {
        "basis_set_id": index["basis_set_id"],
        "manifest_count": 277,
        "all_manifests_complete": True,
        "all_fluence_checksums_verified": True,
        "summed_execution_seconds": execution_seconds,
    }


def _summarize(
    labels: np.ndarray,
    total: np.ndarray,
    optical: dict[str, Any],
    voxel_volume_mm3: float,
) -> dict[str, Any]:
    tissues: list[dict[str, Any]] = []
    by_id: dict[int, dict[str, Any]] = {}
    total_absorbed = 0.0
    for row in optical["tissues"]:
        tissue_id = int(row["tissue_id"])
        mask = labels == tissue_id
        integrated_fluence = float(np.sum(total[mask], dtype=np.float64) * voxel_volume_mm3)
        mua = float(row["mua_mm-1"])
        absorbed = integrated_fluence * mua
        record = {
            "tissue_id": tissue_id,
            "tissue_name": row["tissue_name"],
            "voxel_count": int(np.count_nonzero(mask)),
            "mua_mm-1": mua,
            "integrated_fluence": integrated_fluence,
            "absorbed_fraction_of_launched_energy": absorbed,
            "absorbed_percent_of_launched_energy": absorbed * 100.0,
        }
        tissues.append(record)
        by_id[tissue_id] = record
        total_absorbed += absorbed
    brain_absorbed = (
        by_id[2]["absorbed_fraction_of_launched_energy"]
        + by_id[3]["absorbed_fraction_of_launched_energy"]
    )
    brain_fluence = by_id[2]["integrated_fluence"] + by_id[3]["integrated_fluence"]
    fat_absorbed = (
        by_id[4]["absorbed_fraction_of_launched_energy"]
        + by_id[9]["absorbed_fraction_of_launched_energy"]
    )
    for record in tissues:
        record["share_of_all_tissue_absorption_percent"] = (
            record["absorbed_fraction_of_launched_energy"] / total_absorbed * 100.0
            if total_absorbed > 0
            else None
        )
    return {
        "scenario_id": optical["scenario_id"],
        "fat_mua_mm-1": by_id[4]["mua_mm-1"],
        "brain_integrated_fluence": brain_fluence,
        "gray_matter_absorbed_percent": by_id[2]["absorbed_percent_of_launched_energy"],
        "white_matter_absorbed_percent": by_id[3]["absorbed_percent_of_launched_energy"],
        "brain_absorbed_percent": brain_absorbed * 100.0,
        "fat_absorbed_percent": fat_absorbed * 100.0,
        "total_tissue_absorbed_percent": total_absorbed * 100.0,
        "escaped_or_unabsorbed_percent": (1.0 - total_absorbed) * 100.0,
        "tissues": tissues,
    }


def main() -> int:
    root = ROOT.resolve()
    output_root = root / OUTPUT_ROOT
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"refusing to overwrite nonempty output directory: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    protocol = _load_json(root / PROTOCOL_PATH)
    anatomy = _load_json(root / "inputs/fat_absorption_bracket_v1/anatomy_metadata.json")
    image = nib.load(root / anatomy["volume_representation"])
    labels = np.asarray(image.dataobj, dtype=np.uint8)
    shape = tuple(int(value) for value in anatomy["shape_voxels"])
    if labels.shape != shape:
        raise SystemExit("anatomy shape mismatch")
    voxel_volume = float(np.prod(image.header.get_zooms()[:3]))

    central = _git_json(
        root, Path("inputs/optical_properties/provisional_1070_v1/central.json")
    )
    baseline_total = np.asarray(np.load(root / BASELINE_FIELD), dtype=np.float64)
    if baseline_total.shape != shape:
        raise SystemExit("baseline aggregate shape mismatch")
    summaries: list[dict[str, Any]] = []
    baseline = _summarize(labels, baseline_total, central, voxel_volume)
    baseline.update(
        {
            "case": "fat_abs_103_existing_baseline",
            "role": "existing_extreme_high",
            "execution": {
                "basis_set_id": "surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1",
                "manifest_count": 277,
                "all_manifests_complete": True,
                "aggregate_source": BASELINE_FIELD.as_posix(),
            },
        }
    )
    summaries.append(baseline)

    for case in protocol["cases"]:
        total, execution = _stream_total(root, Path(case["run_root"]) / "index.json", shape)
        case_dir = output_root / case["case"]
        case_dir.mkdir(parents=True, exist_ok=False)
        aggregate_path = case_dir / "total_fluence_constant_total.npy"
        _atomic_npy(aggregate_path, total)
        optical = _load_json(root / case["optical_path"])
        summary = _summarize(labels, total, optical, voxel_volume)
        summary.update({"case": case["case"], "role": case["role"], "execution": execution})
        _atomic_json(case_dir / "summary.json", summary)
        summaries.append(summary)

    baseline_brain = baseline["brain_absorbed_percent"]
    baseline_fluence = baseline["brain_integrated_fluence"]
    comparison_rows: list[dict[str, Any]] = []
    for summary in summaries:
        summary["brain_absorption_change_vs_existing_percent"] = (
            (summary["brain_absorbed_percent"] / baseline_brain - 1.0) * 100.0
        )
        summary["brain_fluence_change_vs_existing_percent"] = (
            (summary["brain_integrated_fluence"] / baseline_fluence - 1.0) * 100.0
        )
        comparison_rows.append(
            {
                "case": summary["case"],
                "role": summary["role"],
                "fat_mua_mm-1": summary["fat_mua_mm-1"],
                "brain_absorbed_percent": summary["brain_absorbed_percent"],
                "brain_absorption_change_vs_existing_percent": summary[
                    "brain_absorption_change_vs_existing_percent"
                ],
                "brain_integrated_fluence": summary["brain_integrated_fluence"],
                "brain_fluence_change_vs_existing_percent": summary[
                    "brain_fluence_change_vs_existing_percent"
                ],
                "fat_absorbed_percent": summary["fat_absorbed_percent"],
                "total_tissue_absorbed_percent": summary["total_tissue_absorbed_percent"],
                "escaped_or_unabsorbed_percent": summary["escaped_or_unabsorbed_percent"],
            }
        )

    comparison_csv = output_root / "comparison.csv"
    with comparison_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparison_rows[0]))
        writer.writeheader()
        writer.writerows(comparison_rows)
    tissue_csv = output_root / "tissue_absorption_by_case.csv"
    tissue_rows = [
        {"case": summary["case"], **row}
        for summary in summaries
        for row in summary["tissues"]
    ]
    with tissue_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(tissue_rows[0]))
        writer.writeheader()
        writer.writerows(tissue_rows)

    result = {
        "result_id": "surrogate_yue277_1070_fat_absorption_bracket_v1",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "scientific_status": protocol["scientific_status"],
        "protocol_path": PROTOCOL_PATH.as_posix(),
        "constant_total_source_weighting": "1/277 per emitter",
        "cases": summaries,
    }
    _atomic_json(output_root / "result.json", result)
    manifest = {
        "provenance": capture_code(root, Path(__file__), sys.argv[1:]),
        "result_id": result["result_id"],
        "created_at": result["created_at"],
        "inputs": [
            {"path": PROTOCOL_PATH.as_posix(), "sha256": sha256_file(root / PROTOCOL_PATH)},
            {"path": BASELINE_FIELD.as_posix(), "sha256": sha256_file(root / BASELINE_FIELD)},
        ],
        "outputs": [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(output_root.rglob("*"))
            if path.is_file() and path.name != "manifest.json"
        ],
    }
    _atomic_json(output_root / "manifest.json", manifest)
    print(json.dumps({"status": "complete", "output": str(output_root), "comparison": comparison_rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
