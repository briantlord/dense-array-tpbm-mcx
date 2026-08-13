#!/usr/bin/env python3
"""Run and summarize the frozen bounded Yue north-pole convergence pilot."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw

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
    load_jnii_field,
    probe_mcxcl,
    resolve_mcxcl_binary,
    standalone_field_from_config,
)
from mcx_project.validation import load_json, validate_json


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "configs/yue2015_convergence_acceptance_v1.json"
ENGINE_PATH = ROOT / "configs/yue2015_approx_v1_north_pole_fluence.json"
ANATOMY_PATH = ROOT / "inputs/anatomy/colin27_2008/derived/yue5_1mm_v1/colin27_labels_yue5_1mm_v1.nii"
OUTPUT_DIR = ROOT / "benchmarks/yue2015_approx_v1/convergence_pilot_m4_v1"


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


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _render_profiles(
    depths: np.ndarray,
    summaries: dict[int, dict[str, Any]],
    path: Path,
    *,
    title: str,
) -> None:
    width, height = 1100, 680
    left, right, top, bottom = 95, 45, 55, 90
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((25, 18), title, fill="black")
    plot_w, plot_h = width - left - right, height - top - bottom
    colors = {
        100000: "#3182bd",
        1000000: "#31a354",
        10000000: "#f16913",
        100000000: "#cb181d",
        1000000000: "#6a51a3",
    }
    positive = np.concatenate(
        [np.asarray(summary["profile_statistics"]["mean"])[np.asarray(summary["profile_statistics"]["mean"]) > 0] for summary in summaries.values()]
    )
    ymin = max(float(np.min(positive)), float(np.max(positive)) * 1e-12)
    ymax = float(np.max(positive))
    log_min, log_max = np.log10(ymin), np.log10(ymax)
    draw.rectangle((left, top, left + plot_w, top + plot_h), outline="#555555")
    for depth in range(0, 101, 20):
        x = left + depth / 100 * plot_w
        draw.line((x, top, x, top + plot_h), fill="#e5e5e5")
        draw.text((x - 10, top + plot_h + 8), str(depth), fill="black")
    for exponent in range(int(np.floor(log_min)), int(np.ceil(log_max)) + 1):
        y = top + (log_max - exponent) / (log_max - log_min) * plot_h
        if top <= y <= top + plot_h:
            draw.line((left, y, left + plot_w, y), fill="#e5e5e5")
            draw.text((12, y - 7), f"1e{exponent}", fill="black")
    for photons, summary in summaries.items():
        mean = np.asarray(summary["profile_statistics"]["mean"], dtype=np.float64)
        valid = np.isfinite(mean) & (mean > 0)
        x = left + depths[valid] / 100 * plot_w
        y = top + (log_max - np.log10(mean[valid])) / (log_max - log_min) * plot_h
        points = list(zip(x.tolist(), y.tolist(), strict=True))
        if len(points) > 1:
            draw.line(points, fill=colors[photons], width=3)
    legend_x = left + 15
    for photons in sorted(summaries):
        draw.line((legend_x, top + 18, legend_x + 38, top + 18), fill=colors[photons], width=4)
        draw.text((legend_x + 45, top + 9), f"{photons:,} photons", fill="black")
        legend_x += 175
    draw.text((left + plot_w // 2 - 55, height - 35), "Axis depth (mm)", fill="black")
    draw.text((10, top + plot_h // 2), "fluence", fill="black")
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--collect-100m-root",
        type=Path,
        help="collect rep001..rep003 MCX outputs after persistent external execution",
    )
    parser.add_argument(
        "--include-1b",
        action="store_true",
        help="extend through the paper-scale one-billion-photon representative tier",
    )
    parser.add_argument(
        "--collect-1b-root",
        type=Path,
        help="collect rep001..rep003 one-billion-photon MCX outputs",
    )
    parser.add_argument(
        "--include-100m",
        action="store_true",
        help="extend the bounded pilot through the required 100-million-photon tier",
    )
    arguments = parser.parse_args()
    if arguments.include_1b:
        arguments.include_100m = True
    default_output = OUTPUT_DIR
    if arguments.include_100m:
        default_output = ROOT / "benchmarks/yue2015_approx_v1/convergence_representative_m4_v1"
    if arguments.include_1b:
        default_output = ROOT / "benchmarks/yue2015_approx_v1/convergence_paperscale_m4_v1"
    output_dir = (arguments.output_dir or default_output).resolve()
    validate_json(
        ROOT / "schemas/benchmark_convergence_protocol.schema.json",
        PROTOCOL_PATH,
        require_complete=True,
    )
    protocol = load_json(PROTOCOL_PATH)
    base_config = load_json(ENGINE_PATH)
    image = nib.load(ANATOMY_PATH)
    labels = np.asarray(image.dataobj, dtype=np.uint8)
    affine = np.asarray(image.affine, dtype=np.float64)
    source_voxel = np.asarray(base_config["source"]["position_voxels"], dtype=np.float64)
    source_world = (affine @ np.r_[source_voxel, 1.0])[:3]
    direction = np.asarray(base_config["source"]["direction"], dtype=np.float64)
    direction /= np.linalg.norm(direction)
    axis = protocol["axis_depths_mm"]
    depths = np.arange(axis["start"], axis["stop"] + axis["step"], axis["step"], dtype=np.float64)
    binary = resolve_mcxcl_binary(ROOT)
    engine = probe_mcxcl(binary)
    summaries: dict[int, dict[str, Any]] = {}
    all_runs: list[dict[str, Any]] = []

    counts = list(protocol["pilot_photon_counts"])
    if arguments.include_100m:
        counts.append(protocol["required_final_photon_counts"][0])
    if arguments.include_1b:
        counts.append(protocol["required_final_photon_counts"][1])
    counts_to_run = counts
    collection_root = arguments.collect_100m_root or arguments.collect_1b_root
    if collection_root is not None:
        if not arguments.include_100m:
            raise SystemExit("collection requires --include-100m or --include-1b")
        if arguments.collect_1b_root is not None and not arguments.include_1b:
            raise SystemExit("--collect-1b-root requires --include-1b")
        prior_dir = (
            ROOT / "benchmarks/yue2015_approx_v1/convergence_representative_m4_v1"
            if arguments.collect_1b_root is not None
            else OUTPUT_DIR
        )
        pilot_path = prior_dir / "results.json"
        if not pilot_path.is_file():
            raise SystemExit(f"missing bounded pilot results: {pilot_path}")
        pilot = load_json(pilot_path)
        summaries = {
            int(count): summary
            for count, summary in pilot["summaries_by_photon_count"].items()
        }
        counts_to_run = [
            protocol["required_final_photon_counts"][1]
            if arguments.collect_1b_root is not None
            else protocol["required_final_photon_counts"][0]
        ]
    for photons in counts_to_run:
        profiles: list[np.ndarray] = []
        integral_rows: list[list[float]] = []
        run_rows: list[dict[str, Any]] = []
        for replicate in range(1, protocol["replicates_per_count"] + 1):
            seed = deterministic_seed(
                protocol["protocol_id"], f"{protocol['source_emitter_id']}_{photons}", replicate
            )
            if collection_root is not None:
                run_directory = collection_root.resolve() / f"rep{replicate:03d}"
                engine_input = load_json(run_directory / "mcx_input.json")
                if engine_input["Session"]["Photons"] != photons:
                    raise SystemExit(f"photon-count mismatch in {run_directory}")
                if engine_input["Session"]["RNGSeed"] != seed:
                    raise SystemExit(f"seed mismatch in {run_directory}")
                field_path = run_directory / "mcx_field.jnii"
                field = load_jnii_field(field_path)
                engine_summary = {"absorbed_energy_percent": None}
                elapsed = None
            else:
                config = json.loads(json.dumps(base_config))
                config["nphoton"] = photons
                config["seed"] = seed
                with tempfile.TemporaryDirectory(prefix=f"yue-conv-{photons}-") as temporary:
                    started = time.perf_counter()
                    field, engine_summary = standalone_field_from_config(
                        config,
                        Path(temporary),
                        binary,
                        project_root=ROOT,
                    )
                    elapsed = time.perf_counter() - started
            profile = sample_axis_profile(field, affine, source_world, direction, depths)
            integrals = masked_integrals(
                field,
                labels,
                {"gray_matter": [4], "white_matter": [5], "brain_total": [3, 4, 5]},
            )
            profiles.append(profile)
            integral_rows.append([integrals[name] for name in ("gray_matter", "white_matter", "brain_total")])
            row = {
                "photon_count": photons,
                "replicate": replicate,
                "seed": seed,
                "elapsed_seconds": elapsed,
                "absorbed_energy_percent": engine_summary["absorbed_energy_percent"],
                "integrals": integrals,
                "profile": profile,
            }
            if collection_root is not None:
                row["field_sha256"] = sha256_file(field_path)
                row["engine_input_sha256"] = sha256_file(run_directory / "mcx_input.json")
            run_rows.append(row)
            all_runs.append(row)
        profile_stats = replicate_statistics(profiles)
        integral_stats = replicate_statistics(integral_rows)
        summaries[photons] = {
            "runs": run_rows,
            "profile_statistics": profile_stats,
            "integral_names": ["gray_matter", "white_matter", "brain_total"],
            "integral_statistics": integral_stats,
        }

    comparisons: list[dict[str, Any]] = []
    low_depth, high_depth = protocol["profile_validity"]["depth_range_mm"]
    threshold_fraction = protocol["profile_validity"]["minimum_fraction_of_current_profile_max"]
    pilot_limits = protocol["pilot_thresholds"]
    for previous_count, current_count in zip(counts[:-1], counts[1:], strict=True):
        previous = summaries[previous_count]
        current = summaries[current_count]
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
        passes = {
            "tissue_integral_cv": bool(np.all(integral_cv <= pilot_limits["tissue_integral_cv_max"])),
            "tissue_integral_step_change": bool(np.all(integral_change <= pilot_limits["tissue_integral_step_change_max"])),
            "profile_median_cv": bool(profile["median_current_cv"] <= pilot_limits["profile_median_cv_max"]),
            "profile_median_step_change": bool(profile["median_symmetric_relative_change"] <= pilot_limits["profile_median_step_change_max"]),
        }
        comparisons.append(
            {
                "previous_photon_count": previous_count,
                "current_photon_count": current_count,
                "integral_symmetric_relative_change": integral_change,
                "current_integral_cv": integral_cv,
                "profile": profile,
                "threshold_checks": passes,
                "all_pilot_thresholds_pass": all(passes.values()),
            }
        )

    result = {
        "result_id": (
            "yue2015_north_pole_convergence_paperscale_m4_v1"
            if arguments.include_1b
            else (
                "yue2015_north_pole_convergence_representative_m4_v1"
                if arguments.include_100m
                else "yue2015_north_pole_convergence_pilot_m4_v1"
            )
        ),
        "scientific_status": (
            "benchmark_paperscale_representative_not_full_multisource"
            if arguments.include_1b
            else (
                "benchmark_representative_convergence_not_final"
                if arguments.include_100m
                else "benchmark_pilot_not_final"
            )
        ),
        "protocol_path": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "engine_configuration_path": ENGINE_PATH.relative_to(ROOT).as_posix(),
        "engine_configuration_sha256": sha256_file(ENGINE_PATH),
        "anatomy_path": ANATOMY_PATH.relative_to(ROOT).as_posix(),
        "anatomy_sha256": sha256_file(ANATOMY_PATH),
        "engine": engine,
        "depths_mm": depths,
        "summaries_by_photon_count": summaries,
        "comparisons": comparisons,
        "highest_evaluated_tier_passes": comparisons[-1]["all_pilot_thresholds_pass"],
        "final_photon_count_selected": False,
        "final_selection_blocker": (
            (
                "The 1e9 representative tier failed one or more frozen thresholds; "
                "do not increase photon count or change sampling without a versioned protocol revision."
                if arguments.include_1b and not comparisons[-1]["all_pilot_thresholds_pass"]
                else (
                    "Representative convergence passed, but full multisource convergence and "
                    "benchmark comparisons remain incomplete."
                    if arguments.include_1b
                    else (
                        "The 1e8 representative tier failed one or more frozen thresholds; "
                        "the protocol therefore requires the 1e9 paper-scale tier."
                        if arguments.include_100m and not comparisons[-1]["all_pilot_thresholds_pass"]
                        else "Full multisource convergence and benchmark comparisons remain incomplete."
                    )
                )
            )
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "results.json", result)
    plot_title = (
        "Yue north-pole paper-scale convergence - replicate mean axis profiles"
        if arguments.include_1b
        else (
            "Yue north-pole representative convergence - replicate mean axis profiles"
            if arguments.include_100m
            else "Yue north-pole convergence pilot - replicate mean axis profiles"
        )
    )
    _render_profiles(depths, summaries, output_dir / "axis_profiles.png", title=plot_title)
    highest = comparisons[-1]
    lines = [
        (
            "# Yue north-pole paper-scale representative convergence"
            if arguments.include_1b
            else (
                "# Yue north-pole representative convergence"
                if arguments.include_100m
                else "# Yue north-pole convergence pilot"
            )
        ),
        "",
        "Status: bounded benchmark convergence check; no final photon count selected.",
        "",
        f"- Counts: {', '.join(f'{count:,}' for count in counts)} photons.",
        f"- Replicates per count: {protocol['replicates_per_count']} independent deterministic seeds.",
        f"- Highest evaluated transition passes all frozen thresholds: `{highest['all_pilot_thresholds_pass']}`.",
        f"- Profile valid depths in highest transition: {highest['profile']['n_valid_depths']}.",
        f"- Highest-transition median profile CV: {highest['profile']['median_current_cv']:.4f}.",
        f"- Highest-transition median profile step change: {highest['profile']['median_symmetric_relative_change']:.4f}.",
        "",
        "This run does not reproduce the multisource Yue curves and cannot pass the benchmark gate. "
        + (
            "The one-billion-photon representative tier failed at least one frozen threshold; "
            "a versioned protocol revision is required before changing the sampling definition."
            if arguments.include_1b and not highest["all_pilot_thresholds_pass"]
            else (
                "The representative source passed, but full multisource convergence and benchmark "
                "comparison remain required."
                if arguments.include_1b
                else (
                    "The 100-million-photon tier failed at least one frozen threshold, so the protocol "
                    "requires the one-billion-photon paper-scale tier."
                    if arguments.include_100m and not highest["all_pilot_thresholds_pass"]
                    else "Full multisource convergence and benchmark comparison remain required."
                )
            )
        ),
        "",
    ]
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "complete",
                "output": str(output_dir),
                "highest_tier_pass": highest["all_pilot_thresholds_pass"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
