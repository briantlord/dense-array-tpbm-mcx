#!/usr/bin/env python3
"""Run and compare one Windows RTX 3080 field before releasing the 277-run batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from mcx_project.basis import execute_basis_run
from mcx_project.benchmark import masked_integrals, sample_axis_profile, symmetric_relative_change
from mcx_project.hashing import sha256_file
from mcx_project.standalone import load_jnii_field, resolve_mcxcl_binary, standalone_field_from_config, probe_mcxcl
from mcx_project.validation import load_json


REFERENCE_EMITTER = "SUR1070_011"
REFERENCE_RESULT = Path(
    "results/surrogate_yue277_1070_v1/regional_convergence_v2/results.json"
)
OUTPUT = Path(
    "results/surrogate_yue277_1070_windows_opencl_v1/backend_equivalence.json"
)
INTEGRAL_CHANGE_MAX = 0.05
PROFILE_MEDIAN_CHANGE_MAX = 0.10


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _load_field(manifest: dict[str, Any], root: Path) -> np.ndarray:
    outputs = [row for row in manifest["outputs"] if row["kind"] == "fluence"]
    if len(outputs) != 1:
        raise RuntimeError("completed representative run must have one fluence output")
    path = root / outputs[0]["path"]
    if sha256_file(path) != outputs[0]["sha256"]:
        raise RuntimeError("representative fluence checksum mismatch")
    return np.load(path, allow_pickle=False) if path.suffix == ".npy" else load_jnii_field(path)


def _write_immutable_json(path: Path, payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True, default=_jsonable) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        raise RuntimeError(f"refusing to replace backend-equivalence result: {path}")
    if not path.exists():
        path.write_text(rendered, encoding="utf-8")


def compare_to_m4_reference(field: np.ndarray, root: Path) -> dict[str, Any]:
    reference = load_json(root / REFERENCE_RESULT)
    summary = reference["summaries_by_region"]["anterior"]["100000000"]
    anatomy = load_json(root / "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/anatomy_metadata.json")
    geometry = load_json(root / "inputs/emitters/surrogate_yue277_1070_v1/emitter_geometry.json")
    emitter = next(row for row in geometry["emitters"] if row["emitter_id"] == REFERENCE_EMITTER)
    image = nib.load(root / anatomy["volume_representation"])
    labels = np.asarray(image.dataobj, dtype=np.uint8)
    direction = np.asarray(emitter["normal"], dtype=np.float64)
    direction /= np.linalg.norm(direction)
    depths = np.asarray(reference["depths_mm"], dtype=np.float64)
    profile = sample_axis_profile(
        field,
        image.affine,
        emitter["position_mm"],
        direction,
        depths,
    )
    integral_names = summary["integral_names"]
    integrals = masked_integrals(
        field,
        labels,
        {"gray_matter": [2], "white_matter": [3], "brain_total": [2, 3]},
    )
    current_integrals = np.asarray([integrals[name] for name in integral_names])
    reference_integrals = np.asarray(summary["integral_statistics"]["mean"])
    integral_change = symmetric_relative_change(reference_integrals, current_integrals)

    reference_profile = np.asarray(summary["profile_statistics"]["mean"])
    low, high = (20.0, 60.0)
    valid = (
        (depths >= low)
        & (depths <= high)
        & np.isfinite(profile)
        & np.isfinite(reference_profile)
        & (reference_profile >= np.nanmax(reference_profile) * 1e-8)
    )
    if not np.any(valid):
        raise RuntimeError("backend-equivalence profile mask selects no valid depths")
    profile_change = symmetric_relative_change(reference_profile[valid], profile[valid])
    checks = {
        "tissue_integral_change": bool(np.all(integral_change <= INTEGRAL_CHANGE_MAX)),
        "profile_median_change": bool(np.median(profile_change) <= PROFILE_MEDIAN_CHANGE_MAX),
    }
    return {
        "all_thresholds_pass": all(checks.values()),
        "checks": checks,
        "emitter_id": REFERENCE_EMITTER,
        "reference": "M4 Pro MCX-CL v2025.10 three-replicate 100M anterior mean",
        "reference_result_path": REFERENCE_RESULT.as_posix(),
        "reference_result_sha256": sha256_file(root / REFERENCE_RESULT),
        "thresholds": {
            "tissue_integral_symmetric_relative_change_max": INTEGRAL_CHANGE_MAX,
            "profile_median_symmetric_relative_change_max": PROFILE_MEDIAN_CHANGE_MAX,
        },
        "integral_names": integral_names,
        "reference_integrals": reference_integrals,
        "current_integrals": current_integrals,
        "integral_symmetric_relative_change": integral_change,
        "profile_valid_depth_count": int(np.count_nonzero(valid)),
        "profile_median_symmetric_relative_change": float(np.median(profile_change)),
        "profile_maximum_symmetric_relative_change": float(np.max(profile_change)),
        "scientific_status": "backend_equivalence_only_not_target_hardware_validation",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    index_path = arguments.index if arguments.index.is_absolute() else root / arguments.index
    index_path = index_path.resolve()
    if not index_path.is_relative_to(root):
        raise SystemExit("index must be inside the project root")
    index = load_json(index_path)
    selected = [row for row in index["runs"] if row["emitter_id"] == REFERENCE_EMITTER]
    if len(selected) != 1:
        raise SystemExit(f"index must contain exactly one {REFERENCE_EMITTER} run")
    manifest_path = root / selected[0]["manifest_path"]
    binary = resolve_mcxcl_binary(root)

    def execute(config: dict[str, Any], run_directory: Path):
        return standalone_field_from_config(config, run_directory, binary, project_root=root)

    execute_basis_run(manifest_path, root, execute, engine_probe=lambda: probe_mcxcl(binary))
    manifest = load_json(manifest_path)
    result = compare_to_m4_reference(_load_field(manifest, root), root)
    result.update(
        {
            "execution_status": manifest["status"],
            "index_path": index_path.relative_to(root).as_posix(),
            "index_sha256": sha256_file(index_path),
            "manifest_path": manifest_path.resolve().relative_to(root).as_posix(),
            "manifest_sha256": sha256_file(manifest_path),
        }
    )
    output = (
        arguments.output
        if arguments.output.is_absolute()
        else root / arguments.output
    )
    output = output.resolve()
    if not output.is_relative_to(root):
        raise SystemExit("output must be inside the project root")
    _write_immutable_json(output, result)
    print(json.dumps(result, indent=2, sort_keys=True, default=_jsonable))
    if not result["all_thresholds_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
