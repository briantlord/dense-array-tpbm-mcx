#!/usr/bin/env python3
"""Measure first-entry energy at nested tissue stages with absorbing tallies.

The original scalar fluence fields do not retain photon crossing direction.
This targeted protocol replaces each requested target tissue with a nearly
perfect absorber having the target tissue's original refractive index. Energy
deposited in those absorber voxels is therefore a first-entry tally that does
not introduce an air-index boundary at the measurement surface.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

import nibabel as nib
import numpy as np

from mcx_project.basis import deterministic_seed
from mcx_project.optics import validate_optical_table
from mcx_project.aggregate_inputs import load_aggregate_inputs
from mcx_project.engine_identity import validate_engine_identity
from mcx_project.standalone import (
    load_jnii_field,
    parse_absorbed_energy_percent,
    render_mcxcl_input,
    probe_mcxcl,
)
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = Path("configs/surrogate_yue277_1070_targeted_penetration_tallies_v1.json")
OUTPUT = Path("results/surrogate_yue277_1070_targeted_penetration_tallies_v1")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
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


def strip_gate(field: np.ndarray) -> np.ndarray:
    while field.ndim > 3 and field.shape[-1] == 1:
        field = field[..., 0]
    if field.ndim != 3:
        raise ValueError(f"expected a 3-D energy field, received shape {field.shape}")
    return np.asarray(field, dtype=np.float64)


def apply_optical_properties(
    configuration: dict[str, Any], scenario: dict[str, Any]
) -> dict[str, Any]:
    """Return a configuration whose media rows come from an optical scenario.

    The basis index supplies emitter geometry, timing, and volume metadata.  An
    explicit optical-properties path in the tally protocol can therefore change
    wavelength without regenerating 277 otherwise identical source records.
    """

    if scenario.get("coefficient_unit") != "mm^-1":
        raise ValueError("optical scenario coefficients must use mm^-1")
    updated = json.loads(json.dumps(configuration))
    properties = updated.get("properties_mm")
    if not isinstance(properties, list):
        raise ValueError("basis configuration does not contain properties_mm")
    required = {0} | {i for i, row in enumerate(properties) if row != [0.0, 0.0, 1.0, 1.0]}
    validate_optical_table(scenario, required_tissue_ids=required)
    seen: set[int] = set()
    for tissue in scenario.get("tissues", []):
        tissue_id = int(tissue["tissue_id"])
        if tissue_id in seen:
            raise ValueError(f"duplicate tissue ID in optical scenario: {tissue_id}")
        if tissue_id < 0 or tissue_id >= len(properties):
            raise ValueError(f"optical tissue ID is outside the basis media table: {tissue_id}")
        values = [
            tissue["mua_mm-1"],
            tissue["mus_mm-1"],
            tissue["g"],
            tissue["n"],
        ]
        if not all(isinstance(value, (int, float)) for value in values):
            raise ValueError(f"optical tissue {tissue_id} contains unresolved values")
        properties[tissue_id] = ([0.0, 0.0, 1.0, 1.0] if tissue_id == 0
                                 else [float(value) for value in values])
        seen.add(tissue_id)
    if not seen:
        raise ValueError("optical scenario contains no tissues")
    return updated


def apply_tissue_overrides(
    scenario: dict[str, Any], overrides: list[dict[str, Any]]
) -> dict[str, Any]:
    """Apply a small, explicit sensitivity overlay to a complete scenario."""

    updated = json.loads(json.dumps(scenario))
    by_id = {int(row["tissue_id"]): row for row in updated.get("tissues", [])}
    if len(by_id) != len(updated.get("tissues", [])):
        raise ValueError("duplicate tissue IDs in base optical scenario")
    override_ids = [row["tissue_id"] for row in overrides]
    if len(override_ids) != len(set(override_ids)):
        raise ValueError("duplicate tissue IDs in optical override")
    allowed = {"mua_mm-1", "mus_mm-1", "source_musp_mm-1", "g", "n"}
    for override in overrides:
        tissue_id = int(override["tissue_id"])
        if tissue_id not in by_id:
            raise ValueError(f"override references missing tissue ID: {tissue_id}")
        unknown = set(override) - allowed - {"tissue_id", "citation", "conversion", "notes"}
        if unknown:
            raise ValueError(f"unsupported optical override fields: {sorted(unknown)}")
        row = by_id[tissue_id]
        for key in allowed:
            if key in override:
                row[key] = override[key]
        for key in ("citation", "conversion", "notes"):
            if key in override:
                row[key] = override[key]
    # Validation is repeated on the final assembled table immediately before
    # rendering, so a partial overlay cannot silently launch a mixed scenario.
    return updated


def build_tally_volume(
    labels: np.ndarray,
    target_labels: list[int],
    blocker_labels: list[int],
    media: list[dict[str, float]],
    absorber_mua: float,
) -> tuple[np.ndarray, list[dict[str, float]], dict[int, int], dict[int, int]]:
    """Return relabeled volume, media table, and target/blocker label maps."""

    volume = labels.copy()
    expanded = json.loads(json.dumps(media))
    mappings: dict[str, dict[int, int]] = {"target": {}, "blocker": {}}
    for role, material_labels in (("target", target_labels), ("blocker", blocker_labels)):
        by_refractive_index: dict[float, int] = {}
        for material_label in material_labels:
            if material_label <= 0 or material_label >= len(media):
                raise ValueError(f"invalid {role} material label {material_label}")
            refractive_index = float(media[material_label]["n"])
            key = round(refractive_index, 12)
            if key not in by_refractive_index:
                absorber_label = len(expanded)
                if absorber_label > 255:
                    raise ValueError("absorber labels exceed byte-volume capacity")
                expanded.append(
                    {
                        "g": 1.0,
                        "mua": float(absorber_mua),
                        "mus": 0.0,
                        "n": refractive_index,
                    }
                )
                by_refractive_index[key] = absorber_label
            mappings[role][material_label] = by_refractive_index[key]
            volume[labels == material_label] = mappings[role][material_label]
    return volume, expanded, mappings["target"], mappings["blocker"]


def summarize_replicates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = np.asarray([row["target_capture_percent"] for row in rows], dtype=np.float64)
    mean = float(values.mean())
    standard_deviation = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    relative_standard_deviation = standard_deviation / mean if mean > 0 else 0.0
    half_range_relative_to_mean = (
        float((values.max() - values.min()) / (2.0 * mean)) if mean > 0 else 0.0
    )
    return {
        "mean_target_capture_percent": mean,
        "replicate_count": len(rows),
        "replicate_values_percent": values.tolist(),
        "standard_deviation_percent_points": standard_deviation,
        "relative_standard_deviation": relative_standard_deviation,
        "half_range_relative_to_mean": half_range_relative_to_mean,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--photon-count", type=int)
    parser.add_argument("--replicates", type=int)
    parser.add_argument("--absorber-mua", type=float)
    parser.add_argument("--stages", nargs="+")
    arguments = parser.parse_args()

    root = arguments.project_root.resolve()
    protocol_path = arguments.protocol
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    output_dir = arguments.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"output directory is not empty; version it instead: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    protocol = load_json(protocol_path)
    photon_count = int(arguments.photon_count or protocol["photon_count_per_replicate"])
    replicates = int(arguments.replicates or protocol["replicates"])
    absorber_mua = float(arguments.absorber_mua or protocol["absorber_mua_mm-1"])
    if photon_count < 1 or replicates < 1 or absorber_mua <= 0:
        raise SystemExit("photon count, replicates, and absorber mua must be positive")

    environment_path = root / protocol["environment_path"]
    environment = load_json(environment_path)
    binary = root / protocol["binary_path"]
    if not binary.is_file():
        raise SystemExit(f"MCX-CL binary is missing: {binary}")
    if sha256_file(binary) != environment["executable_sha256"]:
        raise SystemExit("MCX-CL checksum does not match the captured environment")
    identity = probe_mcxcl(binary)
    validate_engine_identity(environment, identity)

    index_path = root / protocol["basis_index_path"]
    index = load_json(index_path)
    configurations, labels = load_aggregate_inputs(root, index_path)
    if len(configurations) != 277:
        raise SystemExit(f"expected 277 source configurations, found {len(configurations)}")
    base = json.loads(json.dumps(configurations[0]))
    optical_properties_path: Path | None = None
    optical_properties: dict[str, Any] | None = None
    optical_overlay_inputs: list[dict[str, Any]] = []
    if protocol.get("optical_properties_path"):
        optical_properties_path = root / protocol["optical_properties_path"]
        optical_properties = load_json(optical_properties_path)
        for relative_overlay_path in protocol.get("optical_overlay_paths", []):
            overlay_path = root / relative_overlay_path
            overlay = load_json(overlay_path)
            optical_properties = apply_tissue_overrides(
                optical_properties, overlay["overrides"]
            )
            optical_properties["scenario_id"] = overlay["scenario_id"]
            optical_overlay_inputs.append(
                {
                    "path": relative_overlay_path,
                    "scenario_id": overlay["scenario_id"],
                    "sha256": sha256_file(overlay_path),
                }
            )
        if protocol.get("optical_overrides"):
            optical_properties = apply_tissue_overrides(
                optical_properties, protocol["optical_overrides"]
            )
        if protocol.get("optical_scenario_id"):
            optical_properties["scenario_id"] = protocol["optical_scenario_id"]
        base = apply_optical_properties(base, optical_properties)
    positions = [row["source"]["position_voxels"] for row in configurations]
    directions = [row["source"]["direction"] for row in configurations]
    if any(row["source"]["type"] != base["source"]["type"] for row in configurations):
        raise SystemExit("aggregate source types are not uniform")

    anatomy_path = root / protocol["anatomy_path"]
    if sha256_file(anatomy_path) != base["volume"]["sha256"]:
        raise ValueError("targeted anatomy differs from the validated basis anatomy")
    selected_stages = protocol["stages"]
    if arguments.stages:
        requested = set(arguments.stages)
        known = {row["name"] for row in selected_stages}
        unknown = requested - known
        if unknown:
            raise SystemExit(f"unknown stages: {sorted(unknown)}")
        selected_stages = [row for row in selected_stages if row["name"] in requested]

    run_rows: list[dict[str, Any]] = []
    stage_summaries: dict[str, dict[str, Any]] = {}
    for stage in selected_stages:
        stage_dir = output_dir / stage["name"]
        volume, media, absorber_map, blocker_map = build_tally_volume(
            labels,
            [int(value) for value in stage["target_labels"]],
            [int(value) for value in stage.get("blocker_labels", [])],
            render_mcxcl_input(base, "media_probe", volume_file="unused.bin")["Domain"]["Media"],
            absorber_mua,
        )
        absorber_labels = sorted(set(absorber_map.values()))
        blocker_absorber_labels = sorted(set(blocker_map.values()))
        stage_runs: list[dict[str, Any]] = []
        for replicate in range(1, replicates + 1):
            if sha256_file(binary) != identity["executable_sha256"]:
                raise ValueError("MCX executable changed during execution")
            run_dir = stage_dir / f"r{replicate:03d}"
            run_dir.mkdir(parents=True, exist_ok=False)
            volume_path = run_dir / "volume.uint8.bin"
            volume_path.write_bytes(volume.tobytes(order="F"))

            run_config = json.loads(json.dumps(base))
            run_config["nphoton"] = photon_count
            run_config["outputtype"] = "energy"
            run_config["seed"] = deterministic_seed(
                protocol["protocol_id"], f"{stage['name']}__n{photon_count}", replicate
            )
            session_id = f"{stage['name']}_r{replicate:03d}"
            document = render_mcxcl_input(run_config, session_id, volume_file=volume_path.name)
            document["Domain"]["Media"] = media
            document["Optode"]["Source"] = {
                "Type": base["source"]["type"],
                "Pos": positions,
                "Dir": directions,
            }
            document["Session"]["OutputType"] = "e"
            input_path = run_dir / "mcx_input.json"
            atomic_json(input_path, document)

            started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            started = time.perf_counter()
            completed = subprocess.run(
                [str(binary), "-f", input_path.name, "-Z", "2", "--srcid", "0", "-G", "1"],
                cwd=run_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            elapsed = time.perf_counter() - started
            log = completed.stdout + completed.stderr
            log_path = run_dir / "mcxcl.log"
            log_path.write_text(log, encoding="utf-8")
            if completed.returncode != 0:
                raise SystemExit(
                    f"MCX-CL failed for {stage['name']} replicate {replicate}: "
                    f"status {completed.returncode}; see {log_path}"
                )
            field_path = run_dir / f"{session_id}.jnii"
            if not field_path.is_file():
                raise SystemExit(f"missing energy field: {field_path}")
            energy = strip_gate(load_jnii_field(field_path))
            target_mask = np.isin(volume, absorber_labels)
            blocker_mask = np.isin(volume, blocker_absorber_labels)
            target_capture = float(energy[target_mask].sum(dtype=np.float64))
            blocker_capture = float(energy[blocker_mask].sum(dtype=np.float64))
            total_deposition = float(energy.sum(dtype=np.float64))
            log_absorbed_percent = float(parse_absorbed_energy_percent(log))
            deposition_percent = 100.0 * total_deposition
            if abs(deposition_percent - log_absorbed_percent) > 0.05:
                raise SystemExit(
                    f"energy-output closure failed for {stage['name']} r{replicate:03d}: "
                    f"field={deposition_percent:.6f}% log={log_absorbed_percent:.6f}%"
                )
            run = {
                "absorber_label_map": {str(k): v for k, v in absorber_map.items()},
                "blocker_absorber_label_map": {str(k): v for k, v in blocker_map.items()},
                "blocker_capture_percent": 100.0 * blocker_capture,
                "completed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "elapsed_seconds": elapsed,
                "energy_field_sha256": sha256_file(field_path),
                "energy_output_total_percent": deposition_percent,
                "escaped_or_unabsorbed_percent": 100.0 - deposition_percent,
                "input_sha256": sha256_file(input_path),
                "log_absorbed_energy_percent": log_absorbed_percent,
                "log_sha256": sha256_file(log_path),
                "photon_count": photon_count,
                "replicate": replicate,
                "seed": run_config["seed"],
                "stage": stage["name"],
                "started_at": started_at,
                "target_capture_percent": 100.0 * target_capture,
                "upstream_native_tissue_absorption_percent": 100.0 * (
                    total_deposition - target_capture - blocker_capture
                ),
                "volume_sha256": sha256_file(volume_path),
            }
            atomic_json(run_dir / "result.json", run)
            stage_runs.append(run)
            run_rows.append(run)
            print(
                json.dumps(
                    {
                        "stage": stage["name"],
                        "replicate": replicate,
                        "target_capture_percent": run["target_capture_percent"],
                        "elapsed_seconds": elapsed,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        summary = summarize_replicates(stage_runs)
        summary.update(
            {
                "description": stage["description"],
                "blocker_labels": stage.get("blocker_labels", []),
                "target_labels": stage["target_labels"],
            }
        )
        stage_summaries[stage["name"]] = summary

    ordered_names = [row["name"] for row in selected_stages]
    retention = []
    for index_number, name in enumerate(ordered_names):
        value = stage_summaries[name]["mean_target_capture_percent"]
        previous = (
            stage_summaries[ordered_names[index_number - 1]]["mean_target_capture_percent"]
            if index_number > 0
            else 100.0
        )
        retention.append(
            {
                "fraction_of_launched_energy_percent": value,
                "fraction_of_preceding_stage_percent": 100.0 * value / previous,
                "stage": name,
            }
        )

    result = {
        "absorber_mua_mm-1": absorber_mua,
        "anatomy_path": protocol["anatomy_path"],
        "anatomy_sha256": sha256_file(anatomy_path),
        "basis_index_path": protocol["basis_index_path"],
        "basis_index_sha256": sha256_file(index_path),
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "engine": identity,
        "method": {
            "interpretation": "first entry into the requested target tissue set",
            "refractive_index_handling": "absorber media preserve each target label's original refractive index",
            "tally": "energy deposited in target absorber voxels divided by normalized launched energy",
        },
        "optical_properties": (
            {
                "path": protocol["optical_properties_path"],
                "base_scenario_id": load_json(optical_properties_path)["scenario_id"],
                "overlay_inputs": optical_overlay_inputs,
                "overrides": protocol.get("optical_overrides", []),
                "scenario_id": optical_properties["scenario_id"],
                "sha256": sha256_file(optical_properties_path),
                "wavelength_nm": optical_properties["wavelength_nm"],
            }
            if optical_properties_path is not None and optical_properties is not None
            else {
                "path": None,
                "scenario_id": "inherited_from_basis_configuration",
                "sha256": None,
                "wavelength_nm": None,
            }
        ),
        "photon_count_per_replicate": photon_count,
        "protocol_id": protocol["protocol_id"],
        "protocol_path": protocol_path.relative_to(root).as_posix(),
        "protocol_sha256": sha256_file(protocol_path),
        "replicates": replicates,
        "retention": retention,
        "runner_path": Path(__file__).resolve().relative_to(root).as_posix(),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "scientific_status": protocol["scientific_status"],
        "stage_summaries": stage_summaries,
    }
    atomic_json(output_dir / "result.json", result)
    print(json.dumps({"status": "complete", "retention": retention}, indent=2))


if __name__ == "__main__":
    main()
