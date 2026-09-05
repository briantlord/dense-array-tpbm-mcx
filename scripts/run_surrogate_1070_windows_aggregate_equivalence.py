#!/usr/bin/env python3
"""Cross-check two Windows basis fields against one direct two-source MCX-CL run."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from mcx_project.basis import deterministic_seed
from mcx_project.benchmark import masked_integrals, sample_axis_profile
from mcx_project.hashing import sha256_file
from mcx_project.standalone import (
    load_jnii_field,
    parse_absorbed_energy_percent,
    render_mcxcl_input,
)
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = Path(
    "configs/surrogate_yue277_1070_windows_rtx3080ti_aggregate_equivalence_v1.json"
)
ANATOMY_PATH = Path(
    "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/colin27_labels_native12_1mm_v3.nii"
)
INVENTORY_PATH = Path(
    "results/surrogate_yue277_1070_windows_rtx3080ti_opencl_v1/post_run_inventory.json"
)
OUTPUT_DIR = Path(
    "benchmarks/surrogate_yue277_1070_windows_rtx3080ti_opencl/aggregate_equivalence_v1"
)
BINARY_PATH = Path(".local/windows/mcxcl-v2025.10/mcxcl/bin/mcxcl.exe")


def _write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _strip_gate(field: np.ndarray) -> np.ndarray:
    while field.ndim > 3 and field.shape[-1] == 1:
        field = field[..., 0]
    return field


def _relative_error(reference: np.ndarray, observed: np.ndarray) -> np.ndarray:
    output = np.full(reference.shape, np.nan, dtype=np.float64)
    np.divide(np.abs(observed - reference), reference, out=output, where=reference > 0)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--binary", type=Path, default=BINARY_PATH)
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    output_dir = arguments.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    binary = arguments.binary
    if not binary.is_absolute():
        binary = root / binary
    if not binary.is_file():
        raise SystemExit(f"MCX-CL binary is missing: {binary}")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise SystemExit("aggregate-equivalence output exists; version rather than overwrite it")

    protocol = load_json(root / PROTOCOL_PATH)
    inventory = load_json(root / INVENTORY_PATH)
    if sha256_file(binary) != inventory["engine"]["executable_sha256"]:
        raise SystemExit("MCX-CL binary checksum does not match the completed-basis inventory")
    index_path = root / protocol["basis_index_path"]
    index = load_json(index_path)
    runs = {row["emitter_id"]: row for row in index["runs"]}
    source_ids = protocol["source_emitter_ids"]
    configs = [load_json(root / runs[source_id]["configuration_path"]) for source_id in source_ids]
    basis_fields = []
    basis_hashes = {}
    manifest_hashes = {}
    for source_id in source_ids:
        run = runs[source_id]
        manifest_path = root / run["manifest_path"]
        manifest = load_json(manifest_path)
        records = [row for row in manifest["outputs"] if row["kind"] == "fluence"]
        if manifest["status"] != "complete" or len(records) != 1:
            raise SystemExit(f"basis source is incomplete: {source_id}")
        field_path = root / records[0]["path"]
        actual = sha256_file(field_path)
        if actual != records[0]["sha256"]:
            raise SystemExit(f"basis field checksum mismatch: {source_id}")
        basis_fields.append(_strip_gate(load_jnii_field(field_path)))
        basis_hashes[source_id] = actual
        manifest_hashes[source_id] = sha256_file(manifest_path)
    basis_sum = np.sum(np.stack(basis_fields), axis=0, dtype=np.float64)

    base = json.loads(json.dumps(configs[0]))
    base["nphoton"] = protocol["direct_total_photons"]
    base["seed"] = deterministic_seed(protocol["protocol_id"], "direct_two_source", 1)
    image = nib.load(root / ANATOMY_PATH)
    labels = np.asarray(image.dataobj, dtype=np.uint8)
    volume_path = output_dir / "volume.uint8.bin"
    volume_path.write_bytes(labels.tobytes(order="F"))
    document = render_mcxcl_input(base, "direct_two_source", volume_file=volume_path.name)
    document["Optode"]["Source"] = {
        "Type": configs[0]["source"]["type"],
        "Pos": [config["source"]["position_voxels"] for config in configs],
        "Dir": [config["source"]["direction"] for config in configs],
    }
    input_path = output_dir / "mcx_input.json"
    _write_json(input_path, document)
    started = time.perf_counter()
    completed = subprocess.run(
        [str(binary), "-f", input_path.name, "-Z", "2", "--srcid", "0"],
        cwd=output_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    log = completed.stdout + completed.stderr
    log_path = output_dir / "mcxcl.log"
    log_path.write_text(log, encoding="utf-8")
    if completed.returncode != 0:
        raise SystemExit(f"direct MCX-CL run failed with status {completed.returncode}")
    field_path = output_dir / "direct_two_source.jnii"
    direct = _strip_gate(load_jnii_field(field_path))
    direct *= float(protocol["direct_normalization_correction"])

    groups = {"gray_matter": [2], "white_matter": [3], "brain_total": [2, 3]}
    basis_integrals = masked_integrals(basis_sum, labels, groups)
    direct_integrals = masked_integrals(direct, labels, groups)
    tissue_errors = {
        name: abs(direct_integrals[name] - value) / value
        for name, value in basis_integrals.items()
    }
    source = configs[0]["source"]
    depths = np.arange(
        protocol["axis_depth_range_mm"][0],
        protocol["axis_depth_range_mm"][1] + protocol["axis_depth_step_mm"],
        protocol["axis_depth_step_mm"],
        dtype=np.float64,
    )
    source_world = (
        np.asarray(image.affine, dtype=np.float64)
        @ np.r_[source["position_voxels"], 1.0]
    )[:3]
    axis_basis = sample_axis_profile(
        basis_sum, image.affine, source_world, source["direction"], depths
    )
    axis_direct = sample_axis_profile(
        direct, image.affine, source_world, source["direction"], depths
    )
    axis_error = _relative_error(axis_basis, axis_direct)
    valid_voxels = basis_sum > (
        float(protocol["voxel_validity_fraction_of_basis_max"]) * float(np.max(basis_sum))
    )
    voxel_error = _relative_error(basis_sum[valid_voxels], direct[valid_voxels])
    metrics = {
        "maximum_tissue_integral_relative_error": max(tissue_errors.values()),
        "median_axis_profile_relative_error": float(np.nanmedian(axis_error)),
        "median_valid_voxel_relative_error": float(np.nanmedian(voxel_error)),
    }
    acceptance = {
        name: metrics[name] <= threshold
        for name, threshold in protocol["acceptance"].items()
    }
    result = {
        "result_id": "surrogate_yue277_1070_windows_rtx3080ti_aggregate_equivalence_v1",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "scientific_status": protocol["scientific_status"],
        "protocol_path": PROTOCOL_PATH.as_posix(),
        "protocol_sha256": sha256_file(root / PROTOCOL_PATH),
        "basis_index_path": protocol["basis_index_path"],
        "basis_index_sha256": sha256_file(index_path),
        "basis_manifest_sha256": manifest_hashes,
        "basis_field_sha256": basis_hashes,
        "engine": {
            **inventory["engine"],
            "executable_path": binary.relative_to(root).as_posix(),
        },
        "direct_total_photons": protocol["direct_total_photons"],
        "direct_seed": base["seed"],
        "direct_elapsed_seconds": elapsed,
        "direct_absorbed_energy_percent": parse_absorbed_energy_percent(log),
        "direct_field_sha256": sha256_file(field_path),
        "direct_input_sha256": sha256_file(input_path),
        "direct_log_sha256": sha256_file(log_path),
        "normalization_correction": protocol["direct_normalization_correction"],
        "tissue_integrals_basis_sum": basis_integrals,
        "tissue_integrals_corrected_direct": direct_integrals,
        "tissue_integral_relative_errors": tissue_errors,
        "metrics": metrics,
        "thresholds": protocol["acceptance"],
        "acceptance_components": acceptance,
        "status": "pass" if all(acceptance.values()) else "fail",
    }
    _write_json(output_dir / "result.json", result)
    print(json.dumps({"status": result["status"], "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
