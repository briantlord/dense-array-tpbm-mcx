#!/usr/bin/env python3
"""Cross-check two summed basis fields against one direct two-source MCX run."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
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
    resolve_mcxcl_binary,
)
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = Path("configs/yue2015_aggregate_equivalence_v1.json")
INDEX_PATH = Path("runs/yue2015_850_277_pencil_basis_v2/index.json")
ANATOMY_PATH = Path(
    "inputs/anatomy/colin27_2008/derived/yue5_1mm_v1/"
    "colin27_labels_yue5_1mm_v1.nii"
)
OUTPUT_DIR = Path("benchmarks/yue2015_approx_v1/aggregate_equivalence_v1")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _relative_error(reference: np.ndarray, observed: np.ndarray) -> np.ndarray:
    output = np.full(reference.shape, np.nan, dtype=np.float64)
    np.divide(np.abs(observed - reference), reference, out=output, where=reference > 0)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    output_dir = arguments.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    if (output_dir / "result.json").exists():
        raise SystemExit("aggregate-equivalence result already exists; version rather than overwrite it")

    protocol = load_json(root / PROTOCOL_PATH)
    index = load_json(root / INDEX_PATH)
    runs = {row["emitter_id"]: row for row in index["runs"]}
    source_ids = protocol["source_emitter_ids"]
    configs = [load_json(root / runs[source_id]["configuration_path"]) for source_id in source_ids]
    basis_fields = []
    basis_hashes = {}
    for source_id in source_ids:
        run = runs[source_id]
        manifest = load_json(root / run["manifest_path"])
        field_path = root / Path(run["manifest_path"]).parent / "mcx_field.jnii"
        if manifest["status"] != "complete" or not field_path.is_file():
            raise SystemExit(f"basis source is incomplete: {source_id}")
        basis_fields.append(load_jnii_field(field_path)[..., 0])
        basis_hashes[source_id] = sha256_file(field_path)
    basis_sum = np.sum(np.stack(basis_fields), axis=0, dtype=np.float64)

    base = json.loads(json.dumps(configs[0]))
    base["nphoton"] = protocol["direct_total_photons"]
    base["seed"] = deterministic_seed(protocol["protocol_id"], "direct_two_source", 1)
    image = nib.load(root / ANATOMY_PATH)
    labels = np.asarray(image.dataobj, dtype=np.uint8)
    volume_path = output_dir / "volume.uint8.bin"
    volume_path.write_bytes(labels.tobytes(order="F"))
    document = render_mcxcl_input(base, "direct_two_source", volume_file=volume_path.name)
    # MCX-CL encodes multiple geometrically independent sources as nested
    # Pos/Dir arrays inside one Source object, not as an array of Source objects.
    document["Optode"]["Source"] = {
        "Type": configs[0]["source"]["type"],
        "Pos": [config["source"]["position_voxels"] for config in configs],
        "Dir": [config["source"]["direction"] for config in configs],
    }
    input_path = output_dir / "mcx_input.json"
    _write_json(input_path, document)
    binary = resolve_mcxcl_binary(root)
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
    direct = load_jnii_field(field_path)[..., 0]
    direct *= float(protocol["direct_normalization_correction"])

    groups = {"gray_matter": [4], "white_matter": [5], "brain_total": [3, 4, 5]}
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
    # sample_axis_profile accepts world coordinates, not voxels.
    source_world = (np.asarray(image.affine, dtype=np.float64) @ np.r_[source["position_voxels"], 1.0])[:3]
    axis_basis = sample_axis_profile(basis_sum, image.affine, source_world, source["direction"], depths)
    axis_direct = sample_axis_profile(direct, image.affine, source_world, source["direction"], depths)
    axis_error = _relative_error(axis_basis, axis_direct)
    valid_voxels = basis_sum > float(protocol["voxel_validity_fraction_of_basis_max"]) * float(np.max(basis_sum))
    voxel_error = _relative_error(basis_sum[valid_voxels], direct[valid_voxels])
    thresholds = protocol["acceptance"]
    metrics = {
        "maximum_tissue_integral_relative_error": max(tissue_errors.values()),
        "median_axis_profile_relative_error": float(np.nanmedian(axis_error)),
        "median_valid_voxel_relative_error": float(np.nanmedian(voxel_error)),
    }
    acceptance = {
        name: metrics[name] <= threshold for name, threshold in thresholds.items()
    }
    result = {
        "result_id": "yue2015_aggregate_equivalence_m4_v1",
        "protocol_path": PROTOCOL_PATH.as_posix(),
        "protocol_sha256": sha256_file(root / PROTOCOL_PATH),
        "basis_field_sha256": basis_hashes,
        "direct_field_sha256": sha256_file(field_path),
        "direct_input_sha256": sha256_file(input_path),
        "direct_log_sha256": sha256_file(log_path),
        "direct_elapsed_seconds": elapsed,
        "direct_absorbed_energy_percent": parse_absorbed_energy_percent(log),
        "normalization_correction": protocol["direct_normalization_correction"],
        "tissue_integrals_basis_sum": basis_integrals,
        "tissue_integrals_corrected_direct": direct_integrals,
        "tissue_integral_relative_errors": tissue_errors,
        "metrics": metrics,
        "thresholds": thresholds,
        "acceptance_components": acceptance,
        "status": "pass" if all(acceptance.values()) else "fail",
    }
    _write_json(output_dir / "result.json", result)


if __name__ == "__main__":
    main()
