#!/usr/bin/env python3
"""Run controlled Yue north-pole output and segmentation sensitivities."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from scipy import ndimage

from mcx_project.benchmark import sample_axis_profile
from mcx_project.hashing import sha256_file
from mcx_project.standalone import (
    load_jnii_field,
    parse_absorbed_energy_percent,
    resolve_mcxcl_binary,
)
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path("configs/yue2015_single_source_segmentation_sensitivity_v1.json")
RUN_ROOT = Path("runs/yue2015_850_single_source_segmentation_sensitivity_v1")
OUTPUT_DIR = Path("benchmarks/yue2015_approx_v1/single_source_segmentation_sensitivity_v1")
TISSUE_NAMES = {
    0: "air",
    1: "scalp",
    2: "skull",
    3: "CSF",
    4: "gray_matter",
    5: "white_matter",
    6: "transparent_tissue_control",
}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _axis_labels(
    labels: np.ndarray,
    affine: np.ndarray,
    source_world: np.ndarray,
    direction: np.ndarray,
    depths: np.ndarray,
) -> np.ndarray:
    world = source_world[None, :] + depths[:, None] * direction[None, :]
    homogeneous = np.c_[world, np.ones(len(world), dtype=np.float64)]
    voxel = (np.linalg.inv(affine) @ homogeneous.T)[:3]
    return ndimage.map_coordinates(
        labels,
        voxel,
        order=0,
        mode="constant",
        cval=0,
        prefilter=False,
    ).astype(np.uint8)


def _axis_transitions(depths: np.ndarray, labels: np.ndarray) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []
    start = 0
    for index in range(1, len(labels) + 1):
        if index == len(labels) or labels[index] != labels[start]:
            stop = float(depths[index - 1])
            if index < len(depths):
                stop = float((depths[index - 1] + depths[index]) / 2.0)
            transitions.append(
                {
                    "depth_start_mm": float(depths[start]),
                    "depth_stop_mm": stop,
                    "label": int(labels[start]),
                    "tissue": TISSUE_NAMES[int(labels[start])],
                }
            )
            start = index
    return transitions


def _exterior_air(labels: np.ndarray) -> np.ndarray:
    components, _ = ndimage.label(labels == 0)
    boundary = np.concatenate(
        [
            components[0, :, :].ravel(),
            components[-1, :, :].ravel(),
            components[:, 0, :].ravel(),
            components[:, -1, :].ravel(),
            components[:, :, 0].ravel(),
            components[:, :, -1].ravel(),
        ]
    )
    exterior_ids = np.unique(boundary[boundary > 0])
    if exterior_ids.size == 0:
        raise RuntimeError("the anatomy has no exterior air component")
    return np.isin(components, exterior_ids)


def _deep_axis_mask(
    shape: tuple[int, int, int],
    affine: np.ndarray,
    source_world: np.ndarray,
    direction: np.ndarray,
    depth_range: tuple[float, float],
    radius_mm: float,
) -> np.ndarray:
    x = affine[0, 0] * np.arange(shape[0]) + affine[0, 3] - source_world[0]
    y = affine[1, 1] * np.arange(shape[1]) + affine[1, 3] - source_world[1]
    z = affine[2, 2] * np.arange(shape[2]) + affine[2, 3] - source_world[2]
    projection = (
        x[:, None, None] * direction[0]
        + y[None, :, None] * direction[1]
        + z[None, None, :] * direction[2]
    )
    squared_distance = (
        x[:, None, None] ** 2
        + y[None, :, None] ** 2
        + z[None, None, :] ** 2
        - projection**2
    )
    return (
        (projection >= depth_range[0])
        & (projection <= depth_range[1])
        & (squared_distance <= radius_mm**2)
    )


def _apply_operation(
    labels: np.ndarray,
    operation: dict[str, Any],
    *,
    affine: np.ndarray,
    source_world: np.ndarray,
    direction: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    output = labels.copy()
    name = operation["operation"]
    if name == "identity":
        changed = np.zeros(labels.shape, dtype=bool)
    elif name == "inner_scalp_to_transparent":
        distance = ndimage.distance_transform_edt(labels != 2)
        changed = (labels == 1) & (distance <= float(operation["thickness_mm"]))
        output[changed] = 6
    elif name == "inner_skull_to_csf":
        distance = ndimage.distance_transform_edt(labels != 3)
        changed = (labels == 2) & (distance <= float(operation["thickness_mm"]))
        output[changed] = 3
    elif name == "csf_into_gm":
        distance = ndimage.distance_transform_edt(labels != 3)
        changed = (labels == 4) & (distance <= float(operation["thickness_mm"]))
        output[changed] = 3
    elif name == "csf_into_gm_local":
        distance = ndimage.distance_transform_edt(labels != 3)
        cylinder = _deep_axis_mask(
            labels.shape,
            affine,
            source_world,
            direction,
            tuple(float(item) for item in operation["depth_range_mm"]),
            float(operation["radius_mm"]),
        )
        changed = (
            (labels == 4)
            & (distance <= float(operation["thickness_mm"]))
            & cylinder
        )
        output[changed] = 3
    elif name == "deep_axis_gm_to_wm":
        cylinder = _deep_axis_mask(
            labels.shape,
            affine,
            source_world,
            direction,
            tuple(float(item) for item in operation["depth_range_mm"]),
            float(operation["radius_mm"]),
        )
        changed = (labels == 4) & cylinder
        output[changed] = 5
    else:
        raise ValueError(f"unsupported sensitivity operation: {name}")
    return output, {
        "operation": name,
        "changed_voxel_count": int(np.count_nonzero(changed)),
        "from_label_counts": {
            TISSUE_NAMES[int(label)]: int(np.count_nonzero(labels[changed] == label))
            for label in np.unique(labels[changed])
        },
        "to_label_counts": {
            TISSUE_NAMES[int(label)]: int(np.count_nonzero(output[changed] == label))
            for label in np.unique(output[changed])
        },
    }


def _make_variants(
    baseline: np.ndarray,
    specifications: list[dict[str, Any]],
    *,
    affine: np.ndarray,
    source_world: np.ndarray,
    direction: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    by_id = {row["id"]: row for row in specifications}
    volumes: dict[str, np.ndarray] = {}
    provenance: dict[str, Any] = {}
    for specification in specifications:
        variant_id = specification["id"]
        operations = specification.get("components", [variant_id])
        current = baseline.copy()
        records = []
        for component_id in operations:
            current, record = _apply_operation(
                current,
                by_id[component_id],
                affine=affine,
                source_world=source_world,
                direction=direction,
            )
            records.append(record)
        if current.shape != baseline.shape or not set(np.unique(current)).issubset(set(range(7))):
            raise RuntimeError(f"invalid label volume generated for {variant_id}")
        volumes[variant_id] = current
        provenance[variant_id] = {
            "description": specification["description"],
            "operations": records,
            "total_changed_voxel_count": int(np.count_nonzero(current != baseline)),
            "label_counts": {
                TISSUE_NAMES[label]: int(np.count_nonzero(current == label))
                for label in range(7)
            },
        }
    return volumes, provenance


def _run_mcx(
    binary: Path,
    base_document: dict[str, Any],
    labels: np.ndarray,
    run_directory: Path,
    *,
    photons: int,
    seed: int,
    output_type: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    run_directory.mkdir(parents=True, exist_ok=False)
    volume_path = run_directory / "volume.uint8.bin"
    volume_path.write_bytes(np.asarray(labels, dtype=np.uint8).tobytes(order="F"))
    document = deepcopy(base_document)
    session_id = output_type
    document["Domain"]["VolumeFile"] = volume_path.name
    document["Session"]["ID"] = session_id
    document["Session"]["Photons"] = photons
    document["Session"]["RNGSeed"] = seed
    document["Session"]["OutputType"] = {"fluence": "f", "energy": "e"}[output_type]
    input_path = run_directory / "mcx_input.json"
    _write_json(input_path, document)
    started = time.perf_counter()
    completed = subprocess.run(
        [str(binary), "-f", input_path.name, "-Z", "2"],
        cwd=run_directory,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - started
    log = completed.stdout + completed.stderr
    log_path = run_directory / "mcxcl.log"
    log_path.write_text(log, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(
            f"MCX-CL failed in {run_directory} with status {completed.returncode}"
        )
    field_path = run_directory / f"{session_id}.jnii"
    field = load_jnii_field(field_path)
    if field.ndim == 4 and field.shape[-1] == 1:
        field = field[..., 0]
    return field, {
        "elapsed_seconds": elapsed,
        "absorbed_energy_percent": parse_absorbed_energy_percent(log),
        "input_sha256": sha256_file(input_path),
        "field_sha256": sha256_file(field_path),
        "volume_sha256": sha256_file(volume_path),
    }


def _normalize(values: np.ndarray, denominator: float) -> np.ndarray:
    if not np.isfinite(denominator) or denominator <= 0:
        return np.full(values.shape, np.nan, dtype=np.float64)
    return values / denominator


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty CSV")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument(
        "--resume-analysis",
        action="store_true",
        help="Reuse a complete set of existing MCX fields after postprocessing failed.",
    )
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    config = load_json(root / CONFIG_PATH)
    output_dir = root / OUTPUT_DIR
    run_root = root / RUN_ROOT
    if (output_dir.exists() or run_root.exists()) and not arguments.resume_analysis:
        raise SystemExit("sensitivity output already exists; version rather than overwrite it")
    output_dir.mkdir(parents=True, exist_ok=arguments.resume_analysis)
    run_root.mkdir(parents=True, exist_ok=arguments.resume_analysis)

    baseline_config = load_json(root / config["baseline_configuration"])
    baseline_field_path = root / config["baseline_field"]
    baseline_image = nib.load(root / config["baseline_volume"])
    baseline_labels = np.asarray(baseline_image.dataobj, dtype=np.uint8)
    affine = np.asarray(baseline_image.affine, dtype=np.float64)
    source_voxel = np.asarray(baseline_config["source"]["position_voxels"], dtype=np.float64)
    source_world = (affine @ np.r_[source_voxel, 1.0])[:3]
    direction = np.asarray(baseline_config["source"]["direction"], dtype=np.float64)
    if not np.isclose(np.linalg.norm(direction), 1.0, atol=1e-8):
        raise RuntimeError("reference source direction is not a unit vector")
    base_document = load_json(
        root / "runs/yue2015_850_277_pencil_basis_v2/yue277/r001/mcx_input.json"
    )
    if len(base_document["Domain"]["Media"]) == 6:
        base_document["Domain"]["Media"].append(
            {"g": 0.0, "mua": 0.0, "mus": 0.0, "n": 1.0}
        )
    depths_spec = config["depth_grid_mm"]
    depths = np.arange(
        float(depths_spec["start"]),
        float(depths_spec["stop"]) + float(depths_spec["step"]),
        float(depths_spec["step"]),
    )
    fine_depths = np.arange(0.0, 100.01, 0.1)
    mua = np.asarray(
        [row[0] for row in baseline_config["properties_mm"]] + [0.0],
        dtype=np.float64,
    )

    volumes, provenance = _make_variants(
        baseline_labels,
        config["variants"],
        affine=affine,
        source_world=source_world,
        direction=direction,
    )
    for variant_id, labels in volumes.items():
        variant_dir = run_root / variant_id
        variant_dir.mkdir(exist_ok=arguments.resume_analysis)
        variant_image_path = variant_dir / "labels.nii.gz"
        if not variant_image_path.is_file():
            nib.save(
                nib.Nifti1Image(labels, affine, baseline_image.header),
                variant_image_path,
            )
        fine_labels = _axis_labels(labels, affine, source_world, direction, fine_depths)
        provenance[variant_id]["axis_transitions"] = _axis_transitions(
            fine_depths, fine_labels
        )
        provenance[variant_id]["label_volume_sha256"] = sha256_file(variant_image_path)
    _write_json(output_dir / "variant_manifest.json", provenance)

    binary = resolve_mcxcl_binary(root)
    observations: list[dict[str, Any]] = []
    profiles: dict[str, list[np.ndarray]] = {variant_id: [] for variant_id in volumes}
    execution: dict[str, Any] = {}
    total_runs = len(volumes) * len(config["common_random_seeds"])
    run_number = 0
    for variant_id, labels in volumes.items():
        label_profile = _axis_labels(labels, affine, source_world, direction, depths)
        for replicate, seed in enumerate(config["common_random_seeds"], start=1):
            run_number += 1
            print(
                f"[{run_number}/{total_runs}] {variant_id} replicate {replicate}",
                flush=True,
            )
            run_directory = run_root / variant_id / f"r{replicate:03d}"
            if arguments.resume_analysis and run_directory.exists():
                field_path = run_directory / "fluence.jnii"
                log_path = run_directory / "mcxcl.log"
                input_path = run_directory / "mcx_input.json"
                volume_path = run_directory / "volume.uint8.bin"
                required = [field_path, log_path, input_path, volume_path]
                if not all(path.is_file() for path in required):
                    raise RuntimeError(f"resume is incomplete at {run_directory}")
                field = load_jnii_field(field_path)
                if field.ndim == 4 and field.shape[-1] == 1:
                    field = field[..., 0]
                log = log_path.read_text(encoding="utf-8")
                run_metadata = {
                    "elapsed_seconds": None,
                    "absorbed_energy_percent": parse_absorbed_energy_percent(log),
                    "input_sha256": sha256_file(input_path),
                    "field_sha256": sha256_file(field_path),
                    "volume_sha256": sha256_file(volume_path),
                    "resumed_after_postprocessing_failure": True,
                }
            else:
                field, run_metadata = _run_mcx(
                    binary,
                    base_document,
                    labels,
                    run_directory,
                    photons=int(config["photon_count_per_run"]),
                    seed=int(seed),
                    output_type="fluence",
                )
            execution[f"{variant_id}/r{replicate:03d}"] = run_metadata
            profile = sample_axis_profile(
                field, affine, source_world, direction, depths
            )
            profiles[variant_id].append(profile)
            absorbed_proxy = profile * mua[label_profile]
            peak_mask = depths <= 20.0
            for index, depth in enumerate(depths):
                observations.append(
                    {
                        "variant_id": variant_id,
                        "replicate": replicate,
                        "seed": seed,
                        "depth_mm": depth,
                        "tissue_label": int(label_profile[index]),
                        "tissue": TISSUE_NAMES[int(label_profile[index])],
                        "fluence_raw": profile[index],
                        "fluence_normalized_depth0": _normalize(profile, profile[0])[index],
                        "fluence_normalized_peak_0_20": _normalize(
                            profile, float(np.nanmax(profile[peak_mask]))
                        )[index],
                        "absorbed_proxy_raw": absorbed_proxy[index],
                        "absorbed_proxy_normalized_depth0": _normalize(
                            absorbed_proxy, absorbed_proxy[0]
                        )[index],
                        "absorbed_proxy_normalized_peak_0_20": _normalize(
                            absorbed_proxy, float(np.nanmax(absorbed_proxy[peak_mask]))
                        )[index],
                    }
                )

    print("[observable-check] baseline energy output", flush=True)
    energy_dir = run_root / "baseline_energy_r001"
    if arguments.resume_analysis:
        energy_path = energy_dir / "energy.jnii"
        energy_log_path = energy_dir / "mcxcl.log"
        energy_input_path = energy_dir / "mcx_input.json"
        energy_volume_path = energy_dir / "volume.uint8.bin"
        required = [
            energy_path,
            energy_log_path,
            energy_input_path,
            energy_volume_path,
        ]
        if not all(path.is_file() for path in required):
            raise RuntimeError("resume is missing the baseline energy-output run")
        baseline_energy = load_jnii_field(energy_path)
        if baseline_energy.ndim == 4 and baseline_energy.shape[-1] == 1:
            baseline_energy = baseline_energy[..., 0]
        energy_log = energy_log_path.read_text(encoding="utf-8")
        energy_metadata = {
            "elapsed_seconds": None,
            "absorbed_energy_percent": parse_absorbed_energy_percent(energy_log),
            "input_sha256": sha256_file(energy_input_path),
            "field_sha256": sha256_file(energy_path),
            "volume_sha256": sha256_file(energy_volume_path),
            "resumed_after_postprocessing_failure": True,
        }
    else:
        baseline_energy, energy_metadata = _run_mcx(
            binary,
            base_document,
            baseline_labels,
            energy_dir,
            photons=int(config["photon_count_per_run"]),
            seed=int(config["common_random_seeds"][0]),
            output_type="energy",
        )
    execution["baseline_energy_r001"] = energy_metadata
    baseline_first_field = load_jnii_field(
        run_root / "baseline" / "r001" / "fluence.jnii"
    )
    if baseline_first_field.ndim == 4 and baseline_first_field.shape[-1] == 1:
        baseline_first_field = baseline_first_field[..., 0]
    proxy_volume = baseline_first_field * mua[baseline_labels]
    valid = proxy_volume > float(np.max(proxy_volume)) * 1e-10
    scale = float(np.median(baseline_energy[valid] / proxy_volume[valid]))
    scaled_proxy = proxy_volume * scale
    observable_error = np.abs(baseline_energy[valid] - scaled_proxy[valid])
    observable_error /= np.maximum(baseline_energy[valid], np.finfo(float).tiny)

    _write_csv(output_dir / "observations.csv", observations)
    _write_json(output_dir / "execution_manifest.json", execution)

    baseline_mean = np.mean(np.stack(profiles["baseline"]), axis=0)
    yue_value = float(
        config["yue_figure2b_north_pole_60mm"]["digitized_normalized_photon_flux"]
    )
    aggregate_rows: list[dict[str, Any]] = []
    for variant_id, replicate_profiles in profiles.items():
        stack = np.stack(replicate_profiles)
        label_profile = _axis_labels(
            volumes[variant_id], affine, source_world, direction, depths
        )
        absorbed_stack = stack * mua[label_profile][None, :]
        peak_mask = depths <= 20.0
        for depth in config["comparison_depths_mm"]:
            index = int(round((depth - depths[0]) / (depths[1] - depths[0])))
            values = stack[:, index]
            fluence_depth0 = values / stack[:, 0]
            fluence_peak = values / np.max(stack[:, peak_mask], axis=1)
            absorbed_values = absorbed_stack[:, index]
            absorbed_depth0 = absorbed_values / absorbed_stack[:, 0]
            absorbed_peak = absorbed_values / np.max(
                absorbed_stack[:, peak_mask], axis=1
            )
            aggregate_rows.append(
                {
                    "variant_id": variant_id,
                    "depth_mm": depth,
                    "mean_fluence_raw": float(np.mean(values)),
                    "sd_fluence_raw": float(np.std(values, ddof=1)),
                    "cv_fluence_raw": float(np.std(values, ddof=1) / np.mean(values)),
                    "ratio_to_baseline_mean": float(np.mean(values) / baseline_mean[index]),
                    "mean_fluence_normalized_depth0": float(np.mean(fluence_depth0)),
                    "mean_fluence_normalized_peak_0_20": float(np.mean(fluence_peak)),
                    "mean_absorbed_proxy_normalized_depth0": float(
                        np.mean(absorbed_depth0)
                    ),
                    "mean_absorbed_proxy_normalized_peak_0_20": float(
                        np.mean(absorbed_peak)
                    ),
                    "absorbed_proxy_depth0_over_yue_60mm": (
                        float(np.mean(absorbed_depth0) / yue_value)
                        if float(depth) == 60.0
                        else ""
                    ),
                }
            )
    _write_csv(output_dir / "aggregate_depth_comparison.csv", aggregate_rows)

    existing_field = load_jnii_field(baseline_field_path)
    if existing_field.ndim == 4 and existing_field.shape[-1] == 1:
        existing_field = existing_field[..., 0]
    existing_profile = sample_axis_profile(
        existing_field, affine, source_world, direction, depths
    )
    existing_labels = _axis_labels(
        baseline_labels, affine, source_world, direction, depths
    )
    existing_absorbed = existing_profile * mua[existing_labels]
    peak_mask = depths <= 20.0
    target_index = int(np.flatnonzero(depths == 60.0)[0])
    observable_comparison = {
        "depth_mm": 60.0,
        "digitized_yue_value": yue_value,
        "existing_baseline": {
            "fluence_normalized_depth0": float(existing_profile[target_index] / existing_profile[0]),
            "fluence_normalized_peak_0_20": float(
                existing_profile[target_index] / np.max(existing_profile[peak_mask])
            ),
            "absorbed_proxy_normalized_depth0": float(
                existing_absorbed[target_index] / existing_absorbed[0]
            ),
            "absorbed_proxy_normalized_peak_0_20": float(
                existing_absorbed[target_index] / np.max(existing_absorbed[peak_mask])
            ),
        },
        "energy_vs_mua_times_fluence": {
            "scale_factor": scale,
            "median_relative_error_after_scaling": float(np.median(observable_error)),
            "p95_relative_error_after_scaling": float(np.quantile(observable_error, 0.95)),
        },
    }
    for key, value in list(observable_comparison["existing_baseline"].items()):
        observable_comparison["existing_baseline"][f"{key}_over_yue"] = value / yue_value
    _write_json(output_dir / "observable_comparison.json", observable_comparison)

    comparison_60 = {
        row["variant_id"]: row
        for row in aggregate_rows
        if float(row["depth_mm"]) == 60.0
    }
    report_lines = [
        "# Yue north-pole single-source segmentation sensitivity",
        "",
        "This controlled study holds the Yue Table-2 optical coefficients, source coordinate and direction, MCX-CL build, photon count, and three common random seeds fixed. The variants are causal sensitivity operations, not reconstructions of Yue's unavailable SPM12 segmentation.",
        "",
        "## Observable and normalization check",
        "",
        "| Observable at 60 mm | Model value | Model / digitized Yue |",
        "|:---|---:|---:|",
    ]
    for key, value in observable_comparison["existing_baseline"].items():
        if key.endswith("_over_yue"):
            continue
        report_lines.append(
            f"| {key} | {value:.4e} | {value / yue_value:.3f} |"
        )
    report_lines.extend(
        [
            "",
            "The absorbed-energy proxy is independently checked against MCX's energy output after one fitted global unit scale. This tests the identity `energy proportional to mua times fluence`; it does not identify Yue's unpublished plot normalization.",
            "",
            "## Segmentation effects on raw normalized MCX fluence",
            "",
            "| Variant | Raw fluence / baseline | Absorbed proxy / Yue | Replicate CV |",
            "|:---|---:|---:|---:|",
        ]
    )
    for variant_id in volumes:
        row = comparison_60[variant_id]
        report_lines.append(
            f"| {variant_id} | {float(row['ratio_to_baseline_mean']):.3f} | "
            f"{float(row['absorbed_proxy_depth0_over_yue_60mm']):.3f} | "
            f"{float(row['cv_fluence_raw']):.3%} |"
        )
    report_lines.extend(
        [
            "",
            "Interpret the combined scenario only as an explanatory sensitivity. It stacks localized scalp, skull, superior-CSF, and deep gray/white changes and is not evidence that Yue used those exact tissue boundaries. The global CSF dilation is a separate aggressive upper bound.",
            "",
        ]
    )
    (output_dir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    summary = {
        "analysis_id": config["analysis_id"],
        "config_path": CONFIG_PATH.as_posix(),
        "config_sha256": sha256_file(root / CONFIG_PATH),
        "script_path": Path(__file__).resolve().relative_to(root).as_posix(),
        "script_sha256": sha256_file(Path(__file__)),
        "photon_count_per_run": config["photon_count_per_run"],
        "replicate_count": len(config["common_random_seeds"]),
        "observable_comparison": observable_comparison,
        "comparison_at_60mm": comparison_60,
        "run_root": RUN_ROOT.as_posix(),
    }
    _write_json(output_dir / "summary.json", summary)
    print(f"complete: {output_dir}", flush=True)


if __name__ == "__main__":
    main()
