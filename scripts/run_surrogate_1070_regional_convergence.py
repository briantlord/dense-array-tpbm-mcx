#!/usr/bin/env python3
"""Run the bounded five-region convergence study for the 1070-nm surrogate."""

from __future__ import annotations

import copy
import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from mcx_project.basis import deterministic_seed
from mcx_project.benchmark import (
    masked_integrals,
    profile_convergence_summary,
    replicate_statistics,
    sample_axis_profile,
    symmetric_relative_change,
)
from mcx_project.hashing import sha256_file
from mcx_project.standalone import (
    probe_mcxcl,
    resolve_mcxcl_binary,
    standalone_field_from_config,
)
from mcx_project.surrogate_1070 import (
    ANATOMY,
    CONVERGENCE,
    CONVERGENCE_EXTENSION,
    ENGINE,
    GEOMETRY,
)
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/surrogate_yue277_1070_v1/regional_convergence_v1"


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _source(emitter: dict[str, Any], anatomy: dict[str, Any]) -> tuple[list[float], list[float], np.ndarray]:
    affine = np.asarray(anatomy["affine"], dtype=np.float64)
    world = np.asarray([*emitter["position_mm"], 1.0], dtype=np.float64)
    voxel = (np.linalg.inv(affine) @ world)[:3]
    direction = np.asarray(emitter["normal"], dtype=np.float64)
    direction /= np.linalg.norm(direction)
    return voxel.tolist(), direction.tolist(), world[:3]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extend-100m", action="store_true")
    arguments = parser.parse_args()
    protocol_path = CONVERGENCE_EXTENSION if arguments.extend_100m else CONVERGENCE
    output = (
        ROOT / "results/surrogate_yue277_1070_v1/regional_convergence_v2"
        if arguments.extend_100m
        else OUTPUT
    )
    protocol = load_json(ROOT / protocol_path)
    base = load_json(ROOT / ENGINE)
    geometry = load_json(ROOT / GEOMETRY)
    anatomy = load_json(ROOT / ANATOMY)
    labels_path = ROOT / anatomy["volume_representation"]
    image = nib.load(labels_path)
    labels = np.asarray(image.dataobj, dtype=np.uint8)
    affine = np.asarray(image.affine, dtype=np.float64)
    emitters = {row["emitter_id"]: row for row in geometry["emitters"]}
    binary = resolve_mcxcl_binary(ROOT)
    engine = probe_mcxcl(binary)
    axis = protocol["axis_depths_mm"]
    depths = np.arange(axis["start"], axis["stop"] + axis["step"], axis["step"], dtype=np.float64)
    summaries: dict[str, dict[int, dict[str, Any]]] = {}
    if arguments.extend_100m:
        prior_path = ROOT / protocol["prior_results_path"]
        prior = load_json(prior_path)
        if prior["protocol_sha256"] != sha256_file(ROOT / CONVERGENCE):
            raise SystemExit("prior result does not match the frozen v1 protocol")
        summaries = {
            region: {int(count): summary for count, summary in region_rows.items()}
            for region, region_rows in prior["summaries_by_region"].items()
        }
    all_runs: list[dict[str, Any]] = []

    for region, emitter_id in protocol["regional_emitter_ids"].items():
        emitter = emitters[emitter_id]
        position, direction_list, source_world = _source(emitter, anatomy)
        direction = np.asarray(direction_list, dtype=np.float64)
        region_summaries = summaries.get(region, {})
        counts_to_run = (
            [protocol["candidate_full_basis_photon_count"]]
            if arguments.extend_100m
            else protocol["photon_counts"]
        )
        for photons in counts_to_run:
            profiles: list[np.ndarray] = []
            integral_rows: list[list[float]] = []
            runs: list[dict[str, Any]] = []
            for replicate in range(1, protocol["replicates_per_count"] + 1):
                seed = deterministic_seed(
                    protocol["protocol_id"], f"{emitter_id}_{photons}", replicate
                )
                config = copy.deepcopy(base)
                config["nphoton"] = photons
                config["seed"] = seed
                config["source"] = {
                    "direction": direction_list,
                    "emitter_id": emitter_id,
                    "position_voxels": position,
                    "type": emitter["source_type"],
                }
                with tempfile.TemporaryDirectory(prefix=f"sur1070-{region}-{photons}-") as temporary:
                    started = time.perf_counter()
                    field, engine_summary = standalone_field_from_config(
                        config, Path(temporary), binary, project_root=ROOT
                    )
                    elapsed = time.perf_counter() - started
                profile = sample_axis_profile(
                    field, affine, source_world, direction, depths
                )
                integrals = masked_integrals(
                    field,
                    labels,
                    {
                        "gray_matter": [2],
                        "white_matter": [3],
                        "brain_total": [2, 3],
                    },
                )
                profiles.append(profile)
                integral_rows.append(
                    [integrals[name] for name in ("gray_matter", "white_matter", "brain_total")]
                )
                run = {
                    "absorbed_energy_percent": engine_summary["absorbed_energy_percent"],
                    "elapsed_seconds": elapsed,
                    "emitter_id": emitter_id,
                    "integrals": integrals,
                    "photon_count": photons,
                    "profile": profile,
                    "region": region,
                    "replicate": replicate,
                    "seed": seed,
                }
                runs.append(run)
                all_runs.append(run)
            region_summaries[photons] = {
                "integral_names": ["gray_matter", "white_matter", "brain_total"],
                "integral_statistics": replicate_statistics(integral_rows),
                "profile_statistics": replicate_statistics(profiles),
                "runs": runs,
            }
        summaries[region] = region_summaries

    comparisons: list[dict[str, Any]] = []
    low_depth, high_depth = protocol["profile_validity"]["depth_range_mm"]
    threshold_fraction = protocol["profile_validity"]["minimum_fraction_of_current_profile_max"]
    limits = protocol["thresholds"]
    counts = protocol["photon_counts"]
    for region, region_summaries in summaries.items():
        for previous_count, current_count in zip(counts[:-1], counts[1:], strict=True):
            previous = region_summaries[previous_count]
            current = region_summaries[current_count]
            current_mean = np.asarray(current["profile_statistics"]["mean"])
            valid = (
                (depths >= low_depth)
                & (depths <= high_depth)
                & (current_mean >= np.nanmax(current_mean) * threshold_fraction)
            )
            profile = profile_convergence_summary(
                previous["profile_statistics"]["mean"],
                current_mean,
                current["profile_statistics"]["cv"],
                valid_mask=valid,
            )
            integral_change = symmetric_relative_change(
                previous["integral_statistics"]["mean"],
                current["integral_statistics"]["mean"],
            )
            integral_cv = np.asarray(current["integral_statistics"]["cv"])
            checks = {
                "profile_median_cv": bool(profile["median_current_cv"] <= limits["profile_median_cv_max"]),
                "profile_median_step_change": bool(profile["median_symmetric_relative_change"] <= limits["profile_median_step_change_max"]),
                "tissue_integral_cv": bool(np.all(integral_cv <= limits["tissue_integral_cv_max"])),
                "tissue_integral_step_change": bool(np.all(integral_change <= limits["tissue_integral_step_change_max"])),
            }
            comparisons.append(
                {
                    "all_thresholds_pass": all(checks.values()),
                    "current_integral_cv": integral_cv,
                    "current_photon_count": current_count,
                    "integral_symmetric_relative_change": integral_change,
                    "previous_photon_count": previous_count,
                    "profile": profile,
                    "region": region,
                    "threshold_checks": checks,
                }
            )

    candidate = protocol["candidate_full_basis_photon_count"]
    final_comparisons = [row for row in comparisons if row["current_photon_count"] == candidate]
    candidate_passes = len(final_comparisons) == 5 and all(
        row["all_thresholds_pass"] for row in final_comparisons
    )
    candidate_elapsed = [
        row["elapsed_seconds"] for row in all_runs if row["photon_count"] == candidate
    ]
    result = {
        "anatomy_path": anatomy["volume_representation"],
        "anatomy_sha256": sha256_file(labels_path),
        "basis_plan_candidate_ready": candidate_passes,
        "candidate_full_basis_photon_count": candidate,
        "comparisons": comparisons,
        "depths_mm": depths,
        "engine": engine,
        "estimated_full_basis_runtime_seconds": float(np.median(candidate_elapsed) * 277),
        "geometry_path": GEOMETRY.as_posix(),
        "geometry_sha256": sha256_file(ROOT / GEOMETRY),
        "protocol_path": protocol_path.as_posix(),
        "protocol_sha256": sha256_file(ROOT / protocol_path),
        "result_id": (
            "surrogate_yue277_1070_regional_convergence_v2"
            if arguments.extend_100m
            else "surrogate_yue277_1070_regional_convergence_v1"
        ),
        "scientific_status": "provisional_surrogate_convergence_not_target_hardware",
        "summaries_by_region": summaries,
    }
    _write_json(output / "results.json", result)
    lines = [
        "# Yue-derived 1070-nm surrogate regional convergence",
        "",
        "This is a five-region convergence study for a provisional spatial surrogate, not target-helmet validation.",
        "",
        f"- Candidate full-basis count: `{candidate:,}` photons per emitter.",
        f"- Candidate passes every frozen regional transition check: `{candidate_passes}`.",
        f"- Estimated 277-source runtime at the candidate count: `{result['estimated_full_basis_runtime_seconds'] / 60:.1f}` minutes on this M4 Pro.",
        "",
        "| Region | Integral CV max | Integral change max | Profile CV median | Profile change median | Pass |",
        "|---|---:|---:|---:|---:|:---:|",
    ]
    for row in final_comparisons:
        lines.append(
            "| {region} | {icv:.3%} | {ichange:.3%} | {pcv:.3%} | {pchange:.3%} | {passed} |".format(
                region=row["region"],
                icv=float(np.max(row["current_integral_cv"])),
                ichange=float(np.max(row["integral_symmetric_relative_change"])),
                pcv=row["profile"]["median_current_cv"],
                pchange=row["profile"]["median_symmetric_relative_change"],
                passed="PASS" if row["all_thresholds_pass"] else "FAIL",
            )
        )
    lines.extend(
        [
            "",
            (
                "The candidate plan may now be prepared, but executing all 277 fields remains a separate explicit compute step."
                if candidate_passes
                else "Do not prepare or execute the full basis yet; extend the regional protocol to 10^8 photons without changing the current results."
            ),
            "",
        ]
    )
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"candidate_passes": candidate_passes, "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
