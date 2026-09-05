#!/usr/bin/env python3
"""Analyze the whole-head water-only counterfactual against corrected 1070."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import nibabel as nib
import numpy as np

from mcx_project.hashing import sha256_file
from mcx_project.standalone import load_jnii_field


ROOT = Path(__file__).resolve().parents[1]
INDEX = Path(
    "runs/surrogate_yue277_1070_windows_rtx3080ti_water_whole_head_basis_v1/index.json"
)
OPTICAL = Path(
    "inputs/optical_properties/provisional_1070_water_sensitivity_v1/"
    "whole_head_water_to_810_effective.json"
)
ANATOMY = Path("inputs/fat_absorption_bracket_v1/colin27_labels_native12_1mm_v3.nii")
BASELINE_SUMMARY = Path(
    "results/surrogate_yue277_1070_fat_absorption_bracket_v1/fat_abs_010/summary.json"
)
BASELINE_FIELD = Path(
    "results/surrogate_yue277_1070_fat_absorption_bracket_v1/fat_abs_010/"
    "total_fluence_constant_total.npy"
)
TARGETED_BASELINE = Path(
    "results/surrogate_yue277_1070_targeted_penetration_tallies_v1/result.json"
)
TARGETED_BRAIN = Path(
    "results/surrogate_yue277_1070_targeted_water_brain_csf_v1/result.json"
)
TARGETED_WHOLE = Path(
    "results/surrogate_yue277_1070_targeted_water_whole_head_v1/result.json"
)
OUTPUT = Path("results/surrogate_yue277_1070_water_counterfactual_v1")


def _load_json(relative: Path) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


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
    if field.ndim != 3:
        raise RuntimeError(f"unexpected field shape: {field.shape}")
    return np.asarray(field, dtype=np.float64)


def _stream_total(shape: tuple[int, ...]) -> tuple[np.ndarray, dict[str, Any]]:
    index = _load_json(INDEX)
    if len(index["runs"]) != 277:
        raise RuntimeError("counterfactual index does not contain 277 runs")
    total = np.zeros(shape, dtype=np.float64)
    for number, run in enumerate(index["runs"], start=1):
        manifest_path = ROOT / run["manifest_path"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["status"] != "complete":
            raise RuntimeError(f"incomplete manifest: {manifest_path}")
        records = [row for row in manifest["outputs"] if row["kind"] == "fluence"]
        if len(records) != 1:
            raise RuntimeError(f"missing unique fluence output: {manifest_path}")
        record = records[0]
        field_path = ROOT / record["path"]
        if sha256_file(field_path) != record["sha256"]:
            raise RuntimeError(f"fluence checksum mismatch: {field_path}")
        field = _strip_gate(load_jnii_field(field_path))
        if field.shape != shape:
            raise RuntimeError(f"field shape mismatch: {field_path}")
        total += field
        if number == 1 or number % 25 == 0 or number == 277:
            print(f"verified and accumulated {number}/277", flush=True)
    total /= 277.0
    return total, {
        "basis_set_id": index["basis_set_id"],
        "manifest_count": 277,
        "all_manifests_complete": True,
        "all_fluence_checksums_verified": True,
    }


def _summarize(
    labels: np.ndarray,
    field: np.ndarray,
    optical: dict[str, Any],
    voxel_volume_mm3: float,
) -> dict[str, Any]:
    tissues: list[dict[str, Any]] = []
    by_id: dict[int, dict[str, Any]] = {}
    total_absorbed = 0.0
    for row in optical["tissues"]:
        tissue_id = int(row["tissue_id"])
        mask = labels == tissue_id
        integrated = float(np.sum(field[mask], dtype=np.float64) * voxel_volume_mm3)
        absorbed = integrated * float(row["mua_mm-1"])
        record = {
            "tissue_id": tissue_id,
            "tissue_name": row["tissue_name"],
            "mua_mm-1": float(row["mua_mm-1"]),
            "integrated_fluence": integrated,
            "absorbed_percent_of_launched_energy": absorbed * 100.0,
        }
        tissues.append(record)
        by_id[tissue_id] = record
        total_absorbed += absorbed
    brain_fluence = by_id[2]["integrated_fluence"] + by_id[3]["integrated_fluence"]
    brain_absorbed = (
        by_id[2]["absorbed_percent_of_launched_energy"]
        + by_id[3]["absorbed_percent_of_launched_energy"]
    )
    return {
        "scenario_id": optical["scenario_id"],
        "brain_integrated_fluence": brain_fluence,
        "gray_matter_absorbed_percent": by_id[2]["absorbed_percent_of_launched_energy"],
        "white_matter_absorbed_percent": by_id[3]["absorbed_percent_of_launched_energy"],
        "brain_absorbed_percent": brain_absorbed,
        "total_tissue_absorbed_percent": total_absorbed * 100.0,
        "escaped_or_unabsorbed_percent": (1.0 - total_absorbed) * 100.0,
        "tissues": tissues,
    }


def _percent_change(value: float, baseline: float) -> float:
    return (value / baseline - 1.0) * 100.0


def main() -> int:
    output = ROOT / OUTPUT
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite nonempty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    image = nib.load(ROOT / ANATOMY)
    labels = np.asarray(image.dataobj, dtype=np.uint8)
    voxel_volume = float(np.prod(image.header.get_zooms()[:3]))
    optical = _load_json(OPTICAL)
    total, execution = _stream_total(labels.shape)
    _atomic_npy(output / "total_fluence_constant_total.npy", total)
    counterfactual = _summarize(labels, total, optical, voxel_volume)
    baseline = _load_json(BASELINE_SUMMARY)

    changes = {
        "brain_integrated_fluence_percent": _percent_change(
            counterfactual["brain_integrated_fluence"], baseline["brain_integrated_fluence"]
        ),
        "brain_absorbed_percent_relative": _percent_change(
            counterfactual["brain_absorbed_percent"], baseline["brain_absorbed_percent"]
        ),
        "brain_absorbed_percentage_point": (
            counterfactual["brain_absorbed_percent"] - baseline["brain_absorbed_percent"]
        ),
        "total_tissue_absorption_percent_relative": _percent_change(
            counterfactual["total_tissue_absorbed_percent"],
            baseline["total_tissue_absorbed_percent"],
        ),
    }

    baseline_tissues = {int(row["tissue_id"]): row for row in baseline["tissues"]}
    tissue_comparison: list[dict[str, Any]] = []
    for row in counterfactual["tissues"]:
        old = baseline_tissues[row["tissue_id"]]
        tissue_comparison.append(
            {
                "tissue_id": row["tissue_id"],
                "tissue_name": row["tissue_name"],
                "baseline_mua_mm-1": old["mua_mm-1"],
                "counterfactual_mua_mm-1": row["mua_mm-1"],
                "baseline_integrated_fluence": old["integrated_fluence"],
                "counterfactual_integrated_fluence": row["integrated_fluence"],
                "fluence_change_percent": _percent_change(
                    row["integrated_fluence"], old["integrated_fluence"]
                ) if old["integrated_fluence"] else None,
                "baseline_absorbed_percent": old["absorbed_percent_of_launched_energy"],
                "counterfactual_absorbed_percent": row["absorbed_percent_of_launched_energy"],
                "absorption_change_percent": _percent_change(
                    row["absorbed_percent_of_launched_energy"],
                    old["absorbed_percent_of_launched_energy"],
                ) if old["absorbed_percent_of_launched_energy"] else None,
            }
        )

    targeted = {
        "baseline": _load_json(TARGETED_BASELINE)["retention"],
        "brain_csf_only": _load_json(TARGETED_BRAIN)["retention"],
        "whole_head": _load_json(TARGETED_WHOLE)["retention"],
    }
    result = {
        "result_id": "surrogate_yue277_1070_water_counterfactual_v1",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "scientific_status": "provisional_counterfactual_component_isolation_not_physical_810_model",
        "question": "Contribution of the 1070-vs-810 pure-water absorption spectrum with all other terms frozen at corrected 1070 values",
        "water_absorption": {
            "mua_810_mm-1": 0.0019858,
            "mua_1070_mm-1": 0.0125,
            "difference_mm-1": 0.0105142,
        },
        "execution": execution,
        "baseline": baseline,
        "counterfactual": counterfactual,
        "changes_vs_corrected_1070": changes,
        "targeted_first_entry": targeted,
        "tissue_comparison": tissue_comparison,
    }
    _atomic_json(output / "result.json", result)
    with (output / "tissue_comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(tissue_comparison[0]))
        writer.writeheader()
        writer.writerows(tissue_comparison)
    manifest = {
        "result_id": result["result_id"],
        "inputs": [
            {"path": path.as_posix(), "sha256": sha256_file(ROOT / path)}
            for path in (
                INDEX, OPTICAL, ANATOMY, BASELINE_SUMMARY, BASELINE_FIELD,
                TARGETED_BASELINE, TARGETED_BRAIN, TARGETED_WHOLE,
            )
        ],
        "outputs": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(output.iterdir())
            if path.is_file() and path.name != "manifest.json"
        ],
    }
    _atomic_json(output / "manifest.json", manifest)
    print(json.dumps({"status": "complete", "changes": changes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
