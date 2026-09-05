#!/usr/bin/env python3
"""Aggregate the completed Yue 850-nm source basis into benchmark curves."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, stats

from mcx_project.benchmark import sample_axis_profile
from mcx_project.hashing import sha256_file
from mcx_project.standalone import load_jnii_field
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = Path("runs/yue2015_850_277_pencil_basis_v2/index.json")
GEOMETRY_PATH = Path("inputs/emitters/yue2015_approx_v1/emitter_geometry.json")
TIERS_PATH = Path("inputs/emitters/yue2015_approx_v1/density_tiers.json")
ANATOMY_PATH = Path(
    "inputs/anatomy/colin27_2008/derived/yue5_1mm_v1/"
    "colin27_labels_yue5_1mm_v1.nii"
)
DIGITIZED_PATH = Path("literature/yue2015_figure_digitization_v1.csv")
OUTPUT_DIR = Path("benchmarks/yue2015_approx_v1/multisource_1e8_v2")

REGIONS = {
    # The paper says these four sites were random but supplies no coordinates.
    # These deterministic directional surrogates are therefore approximation inputs.
    "frontal": "YUE011",       # nearest +anterior direction
    "occipital": "YUE031",     # nearest -posterior direction
    "temporal": "YUE041",      # nearest +right-lateral direction
    "parietal": "YUE206",      # nearest posterior-superior 45-degree direction
    "north_pole": "YUE277",    # declared reference source
}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty CSV")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _normalized(values: np.ndarray) -> np.ndarray:
    result = np.full(values.shape, np.nan, dtype=np.float64)
    if values.size and np.isfinite(values[0]) and values[0] > 0:
        np.divide(values, values[0], out=result)
    return result


def _relative_sd(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if not finite.size or float(np.mean(finite)) <= 0:
        return float("nan")
    return float(np.std(finite, ddof=0) / np.mean(finite))


def _write_discrepancy_report(
    path: Path,
    direct_rows: list[dict[str, Any]],
    density_rows: list[dict[str, Any]],
    single_rows: list[dict[str, Any]],
    uniformity_rows: list[dict[str, Any]],
    acceptance: dict[str, Any],
) -> None:
    lines = [
        "# Yue 2015 850-nm multisource discrepancy report",
        "",
        "This is an approximate reconstruction, not an exact rerun of the unpublished MCXLAB configuration. The field basis uses the accepted project Colin27 derivative, the paper's Table-2 optical coefficients, deterministic project source coordinates, pencil sources, and `10^8` photons per source.",
        "",
        "## North-pole reference-source enhancement",
        "",
        "| Depth (mm) | Modeled EF_ref | Digitized Yue | Modeled/paper | Within digitization interval |",
        "|---:|---:|---:|---:|:---:|",
    ]
    for row in direct_rows:
        lines.append(
            f"| {row['depth_mm']:.0f} | {row['modeled_value']:.4g} | "
            f"{row['digitized_value']:.4g} | {row['modeled_over_digitized']:.3f} | "
            f"{'yes' if row['inside_digitization_interval'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            f"Frozen 40/60-mm 25% error gate: **{'pass' if acceptance['headline_relative_error_pass'] else 'fail'}**.",
            f"Frozen profile Spearman gate: **{'pass' if acceptance['profile_spearman_pass'] else 'fail'}**.",
            "",
            "## Density tiers at 60 mm",
            "",
            "| Sources | Modeled EF_ref | Digitized Yue | Modeled/paper |",
            "|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(density_rows, key=lambda item: item["source_count"]):
        lines.append(
            f"| {row['source_count']} | {row['modeled_value']:.4g} | "
            f"{row['digitized_value']:.4g} | {row['modeled_over_digitized']:.3f} |"
        )
    lines.extend(
        [
            "",
            f"Frozen increasing-density ordering gate: **{'pass' if acceptance['density_order_pass'] else 'fail'}**.",
            "",
            "## Regional single-source profiles at 60 mm",
            "",
            "| Region surrogate | Modeled normalized fluence | Digitized Yue | Modeled/paper |",
            "|:---|---:|---:|---:|",
        ]
    )
    for row in single_rows:
        lines.append(
            f"| {row['series']} | {row['modeled_value']:.4g} | "
            f"{row['digitized_value']:.4g} | {row['modeled_over_digitized']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The four non-north regional coordinates were not reported by Yue; these values assess qualitative regional behavior using frozen directional surrogates and are not exact-coordinate acceptance tests.",
            "",
            "## Uniformity boundary",
            "",
            "Yue defines uniformity as spatial SD/mean but does not report the sampled spatial mask. Exact scalar reproduction is therefore not identifiable. The project reports four explicit alternatives and uses their direction with density as trend-only evidence.",
            "",
            "| Sources | Intracranial raw | Whole-head raw | 40-mm shell | Five-axis median (20-60 mm) |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in uniformity_rows:
        lines.append(
            f"| {row['source_count']} | {row['intracranial_raw_field_sd_over_mean']:.4g} | "
            f"{row['whole_head_raw_field_sd_over_mean']:.4g} | "
            f"{row['depth40_shell_sd_over_mean']:.4g} | "
            f"{row['median_five_axis_sd_over_mean_depth20_60']:.4g} |"
        )
    lines.extend(
        [
            "",
            "## Known sources of discrepancy",
            "",
            "- The paper's SPM12 five-tissue segmentation and preprocessing parameters are unavailable; the project uses a separately documented Colin27 derivative.",
            "- Per-ring azimuth phases and lower-density coordinates are unreported; the project uses frozen deterministic approximations.",
            "- The paper omits refractive indices; the project uses `n=1.0` for all media in this version.",
            "- The paper calls deposited weight photon flux, whereas this implementation records MCX normalized fluence.",
            "- Regional source coordinates and the uniformity mask are unreported and cannot be exactly reconstructed.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _plot_lines(
    x: np.ndarray,
    series: list[tuple[str, np.ndarray]],
    path: Path,
    *,
    title: str,
    y_label: str,
    log_y: bool = False,
    points: list[tuple[float, float]] | None = None,
) -> None:
    width, height = 1100, 700
    left, right, top, bottom = 105, 45, 60, 85
    plot_w, plot_h = width - left - right, height - top - bottom
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((25, 20), title, fill="black")
    draw.rectangle((left, top, left + plot_w, top + plot_h), outline="#555555")
    transformed: list[np.ndarray] = []
    for _, values in series:
        values = np.asarray(values, dtype=np.float64)
        if log_y:
            values = np.where(values > 0, np.log10(values), np.nan)
        transformed.append(values)
    point_values = np.asarray([p[1] for p in points or []], dtype=np.float64)
    if log_y and point_values.size:
        point_values = np.where(point_values > 0, np.log10(point_values), np.nan)
    finite_values = [v[np.isfinite(v)] for v in transformed if np.any(np.isfinite(v))]
    if point_values.size and np.any(np.isfinite(point_values)):
        finite_values.append(point_values[np.isfinite(point_values)])
    y_all = np.concatenate(finite_values)
    ymin, ymax = float(np.min(y_all)), float(np.max(y_all))
    if np.isclose(ymin, ymax):
        ymin, ymax = ymin - 0.5, ymax + 0.5
    pad = 0.04 * (ymax - ymin)
    ymin, ymax = ymin - pad, ymax + pad
    xmin, xmax = float(np.min(x)), float(np.max(x))
    for fraction in np.linspace(0, 1, 6):
        px = left + fraction * plot_w
        py = top + fraction * plot_h
        draw.line((px, top, px, top + plot_h), fill="#e5e5e5")
        draw.line((left, py, left + plot_w, py), fill="#e5e5e5")
        draw.text((px - 12, top + plot_h + 8), f"{xmin + fraction * (xmax - xmin):.0f}", fill="black")
        y_tick = ymax - fraction * (ymax - ymin)
        label = f"1e{y_tick:.0f}" if log_y else f"{y_tick:.2g}"
        draw.text((18, py - 7), label, fill="black")
    colors = ["#2166ac", "#b2182b", "#1b7837", "#762a83", "#e08214", "#555555"]
    for index, ((label, _), values) in enumerate(zip(series, transformed, strict=True)):
        valid = np.isfinite(values)
        px = left + (x[valid] - xmin) / (xmax - xmin) * plot_w
        py = top + (ymax - values[valid]) / (ymax - ymin) * plot_h
        line = list(zip(px.tolist(), py.tolist(), strict=True))
        if len(line) > 1:
            draw.line(line, fill=colors[index % len(colors)], width=3)
        ly = top + 12 + index * 20
        draw.line((left + 12, ly + 6, left + 42, ly + 6), fill=colors[index % len(colors)], width=3)
        draw.text((left + 48, ly), label, fill="black")
    for point_x, point_y in points or []:
        py_value = np.log10(point_y) if log_y and point_y > 0 else point_y
        if not np.isfinite(py_value):
            continue
        px = left + (point_x - xmin) / (xmax - xmin) * plot_w
        py = top + (ymax - py_value) / (ymax - ymin) * plot_h
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill="black")
    draw.text((left + plot_w // 2 - 45, height - 30), "Depth (mm)", fill="black")
    draw.text((12, top + plot_h // 2), y_label, fill="black")
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    output_dir = arguments.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    index = load_json(root / INDEX_PATH)
    geometry = load_json(root / GEOMETRY_PATH)
    tier_document = load_json(root / TIERS_PATH)
    emitters = {row["emitter_id"]: row for row in geometry["emitters"]}
    runs = {row["emitter_id"]: row for row in index["runs"]}
    tier_counts = sorted(int(value) for value in tier_document["tiers"])
    tier_sets = {
        count: set(tier_document["tiers"][str(count)]) for count in tier_counts
    }
    if tier_counts != [13, 53, 105, 181, 229, 277]:
        raise SystemExit(f"unexpected Yue density tiers: {tier_counts}")
    if not all(tier_sets[a] < tier_sets[b] for a, b in zip(tier_counts, tier_counts[1:])):
        raise SystemExit("density tiers must be strictly nested")
    if any(source not in runs for source in tier_sets[277]):
        raise SystemExit("basis index does not cover every density-tier source")

    for emitter_id, run in runs.items():
        manifest = load_json(root / run["manifest_path"])
        field_path = root / Path(run["manifest_path"]).parent / "mcx_field.jnii"
        if manifest["status"] != "complete" or not field_path.is_file():
            raise SystemExit(f"basis is incomplete at {emitter_id}: {field_path}")

    anatomy = nib.load(root / ANATOMY_PATH)
    labels = np.asarray(anatomy.dataobj, dtype=np.uint8)
    affine = np.asarray(anatomy.affine, dtype=np.float64)
    depths = np.arange(0.0, 101.0, 1.0, dtype=np.float64)
    region_names = list(REGIONS)
    source_ids = sorted(runs)
    source_index = {source_id: number for number, source_id in enumerate(source_ids)}
    profiles = np.empty((len(source_ids), len(region_names), len(depths)), dtype=np.float64)

    # Each source is assigned to the smallest nested tier that contains it. The
    # six delta volumes let us reconstruct all tiers while adding each 3-D field once.
    delta_counts = [13, 53, 105, 181, 229, 277]
    delta_volumes = {
        count: np.zeros(labels.shape, dtype=np.float64) for count in delta_counts
    }
    prior: set[str] = set()
    delta_members: dict[int, set[str]] = {}
    for count in delta_counts:
        delta_members[count] = tier_sets[count] - prior
        prior = tier_sets[count]

    for source_id in source_ids:
        run = runs[source_id]
        field_path = root / Path(run["manifest_path"]).parent / "mcx_field.jnii"
        field = load_jnii_field(field_path)
        if field.ndim == 4 and field.shape[-1] == 1:
            field = field[..., 0]
        for region_number, region in enumerate(region_names):
            target = emitters[REGIONS[region]]
            profiles[source_index[source_id], region_number] = sample_axis_profile(
                field,
                affine,
                target["position_mm"],
                target["normal"],
                depths,
            )
        for count, members in delta_members.items():
            if source_id in members:
                delta_volumes[count] += field
                break

    single_rows: list[dict[str, Any]] = []
    total_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    uniformity_rows: list[dict[str, Any]] = []
    tier_profiles: dict[int, np.ndarray] = {}
    for region_number, region in enumerate(region_names):
        emitter_id = REGIONS[region]
        single = profiles[source_index[emitter_id], region_number]
        normalized = _normalized(single)
        for depth, raw, norm in zip(depths, single, normalized, strict=True):
            single_rows.append(
                {
                    "region": region,
                    "emitter_id": emitter_id,
                    "depth_mm": depth,
                    "fluence_raw": raw,
                    "fluence_normalized_to_depth0": norm,
                }
            )

    cumulative_volume = np.zeros(labels.shape, dtype=np.float64)
    inside_head = labels > 0
    intracranial = np.isin(labels, [3, 4, 5])
    shell_depth = ndimage.distance_transform_edt(inside_head)
    shell_40 = inside_head & (shell_depth >= 39.5) & (shell_depth < 40.5)
    for count in tier_counts:
        indices = [source_index[source] for source in sorted(tier_sets[count])]
        tier_profile = np.sum(profiles[indices], axis=0, dtype=np.float64)
        tier_profiles[count] = tier_profile
        cumulative_volume += delta_volumes[count]
        regional_depth_mask = (depths >= 20) & (depths <= 60)
        regional_cvs = [
            _relative_sd(tier_profile[:, depth_index])
            for depth_index in np.flatnonzero(regional_depth_mask)
        ]
        uniformity_rows.append(
            {
                "source_count": count,
                "intracranial_raw_field_sd_over_mean": _relative_sd(cumulative_volume[intracranial]),
                "whole_head_raw_field_sd_over_mean": _relative_sd(cumulative_volume[inside_head]),
                "depth40_shell_sd_over_mean": _relative_sd(cumulative_volume[shell_40]),
                "median_five_axis_sd_over_mean_depth20_60": float(np.nanmedian(regional_cvs)),
                "paper_mask_status": "not_reported_trend_comparison_only",
            }
        )
        for region_number, region in enumerate(region_names):
            reference_id = REGIONS[region]
            reference = profiles[source_index[reference_id], region_number]
            total = tier_profile[region_number]
            enhancement = np.full(total.shape, np.nan, dtype=np.float64)
            np.divide(total, reference, out=enhancement, where=reference > 0)
            normalized = _normalized(total)
            for depth, raw, norm, ref, gain in zip(
                depths, total, normalized, reference, enhancement, strict=True
            ):
                total_rows.append(
                    {
                        "source_count": count,
                        "region": region,
                        "reference_emitter_id": reference_id,
                        "depth_mm": depth,
                        "total_fluence_raw": raw,
                        "total_fluence_normalized_to_depth0": norm,
                        "reference_source_fluence_raw": ref,
                        "ef_ref": gain,
                    }
                )

    with (root / DIGITIZED_PATH).open(newline="", encoding="utf-8") as stream:
        digitized = list(csv.DictReader(stream))
    fig2_series = {
        "frontal": "frontal_open_square",
        "occipital": "occipital_open_circle",
        "temporal": "temporal_open_triangle",
        "parietal": "parietal_filled_circle",
        "north_pole": "north_pole_filled_square",
    }
    for region_number, region in enumerate(region_names):
        target = next(row for row in digitized if row["figure_panel"] == "fig2b" and row["series"] == fig2_series[region])
        modeled = _normalized(profiles[source_index[REGIONS[region]], region_number])[60]
        comparison_rows.append(
            {
                "paper_panel": "fig2b",
                "series": fig2_series[region],
                "source_count": 1,
                "depth_mm": 60.0,
                "modeled_value": modeled,
                "digitized_value": float(target["y_value"]),
                "digitized_lower": float(target["y_lower"]),
                "digitized_upper": float(target["y_upper"]),
                "comparison_status": "coordinate_approximation",
            }
        )
    north_number = region_names.index("north_pole")
    north_reference = profiles[source_index["YUE277"], north_number]
    for target in (row for row in digitized if row["figure_panel"] == "fig4"):
        depth_index = int(round(float(target["x_value"])))
        modeled = tier_profiles[277][north_number, depth_index] / north_reference[depth_index]
        comparison_rows.append(
            {
                "paper_panel": "fig4",
                "series": target["series"],
                "source_count": 277,
                "depth_mm": float(target["x_value"]),
                "modeled_value": modeled,
                "digitized_value": float(target["y_value"]),
                "digitized_lower": float(target["y_lower"]),
                "digitized_upper": float(target["y_upper"]),
                "comparison_status": "direct_pencil_ef_ref",
            }
        )
    for target in (row for row in digitized if row["figure_panel"] == "fig5a"):
        count = int(target["series"].split("_", 1)[0])
        modeled = tier_profiles[count][north_number, 60] / north_reference[60]
        comparison_rows.append(
            {
                "paper_panel": "fig5a",
                "series": target["series"],
                "source_count": count,
                "depth_mm": 60.0,
                "modeled_value": modeled,
                "digitized_value": float(target["y_value"]),
                "digitized_lower": float(target["y_lower"]),
                "digitized_upper": float(target["y_upper"]),
                "comparison_status": "approximate_nested_layout",
            }
        )
    for row in comparison_rows:
        row["modeled_minus_digitized"] = row["modeled_value"] - row["digitized_value"]
        row["modeled_over_digitized"] = row["modeled_value"] / row["digitized_value"]
        row["inside_digitization_interval"] = row["digitized_lower"] <= row["modeled_value"] <= row["digitized_upper"]

    _write_csv(output_dir / "single_source_depth_curves.csv", single_rows)
    _write_csv(output_dir / "total_field_depth_curves.csv", total_rows)
    _write_csv(output_dir / "paper_comparison.csv", comparison_rows)
    _write_csv(output_dir / "uniformity_metrics.csv", uniformity_rows)

    single_series = []
    full_total_series = []
    for region_number, region in enumerate(region_names):
        single_series.append((region, _normalized(profiles[source_index[REGIONS[region]], region_number])))
        full_total_series.append((region, _normalized(tier_profiles[277][region_number])))
    density_series = [
        (f"{count} sources", _normalized(tier_profiles[count][north_number]))
        for count in tier_counts
    ]
    gain_series = []
    for count in tier_counts:
        gain = np.full(depths.shape, np.nan, dtype=np.float64)
        np.divide(tier_profiles[count][north_number], north_reference, out=gain, where=north_reference > 0)
        gain_series.append((f"{count} sources", gain))
    fig4_points = [
        (float(row["x_value"]), float(row["y_value"]))
        for row in digitized if row["figure_panel"] == "fig4"
    ]
    _plot_lines(depths, single_series, output_dir / "single_source_depth_curves.png", title="Yue approximation: regional single-source profiles", y_label="Normalized fluence", log_y=True)
    _plot_lines(depths, full_total_series, output_dir / "regional_total_field_depth_curves.png", title="Yue approximation: 277-source total field by regional axis", y_label="Normalized fluence", log_y=True)
    _plot_lines(depths, density_series, output_dir / "north_total_field_depth_curves.png", title="Yue approximation: total field on the north-pole axis", y_label="Normalized fluence", log_y=True)
    _plot_lines(
        depths,
        [
            ("north-pole single source", _normalized(north_reference)),
            ("277-source total field", _normalized(tier_profiles[277][north_number])),
        ],
        output_dir / "north_single_vs_total_depth_curves.png",
        title="Yue approximation: north-pole single source versus total field",
        y_label="Normalized fluence",
        log_y=True,
    )
    _plot_lines(depths, gain_series, output_dir / "north_reference_source_enhancement.png", title="Yue approximation: total/reference-source enhancement", y_label="EF_ref", points=fig4_points)

    direct_rows = [row for row in comparison_rows if row["paper_panel"] == "fig4"]
    density_rows = [row for row in comparison_rows if row["paper_panel"] == "fig5a"]
    headline_rows = [row for row in direct_rows if row["depth_mm"] in (40.0, 60.0)]
    fig4_spearman = float(
        stats.spearmanr(
            [row["digitized_value"] for row in direct_rows],
            [row["modeled_value"] for row in direct_rows],
        ).statistic
    )
    density_order_pass = [row["modeled_value"] for row in sorted(density_rows, key=lambda row: row["source_count"])] == sorted(
        row["modeled_value"] for row in density_rows
    )
    uniformity_order = {}
    for metric in (
        "intracranial_raw_field_sd_over_mean",
        "whole_head_raw_field_sd_over_mean",
        "depth40_shell_sd_over_mean",
        "median_five_axis_sd_over_mean_depth20_60",
    ):
        values = [row[metric] for row in uniformity_rows]
        uniformity_order[metric] = values == sorted(values, reverse=True)
    acceptance_evaluation = {
        "headline_relative_error_max": 0.25,
        "headline_relative_error_pass": all(
            abs(row["modeled_over_digitized"] - 1.0) <= 0.25
            for row in headline_rows
        ),
        "profile_spearman_min": 0.95,
        "profile_spearman_pass": fig4_spearman >= 0.95,
        "density_order_required": True,
        "density_order_pass": density_order_pass,
        "uniformity_order_required": True,
        "uniformity_order_by_declared_metric": uniformity_order,
        "uniformity_exact_scalar_gate_applicable": False,
        "uniformity_exact_scalar_gate_reason": "paper_spatial_mask_not_reported",
    }
    _write_discrepancy_report(
        output_dir / "discrepancy_report.md",
        direct_rows,
        density_rows,
        [row for row in comparison_rows if row["paper_panel"] == "fig2b"],
        uniformity_rows,
        acceptance_evaluation,
    )
    summary = {
        "analysis_id": "yue2015_850_multisource_1e8_v2",
        "basis_index": INDEX_PATH.as_posix(),
        "basis_index_sha256": sha256_file(root / INDEX_PATH),
        "generation_script": "scripts/analyze_yue_basis.py",
        "generation_script_sha256": sha256_file(Path(__file__)),
        "input_sha256": {
            ANATOMY_PATH.as_posix(): sha256_file(root / ANATOMY_PATH),
            DIGITIZED_PATH.as_posix(): sha256_file(root / DIGITIZED_PATH),
            GEOMETRY_PATH.as_posix(): sha256_file(root / GEOMETRY_PATH),
            TIERS_PATH.as_posix(): sha256_file(root / TIERS_PATH),
        },
        "depth_grid_mm": {"start": 0, "stop": 100, "step": 1},
        "density_tiers": tier_counts,
        "photon_count_per_source": 100000000,
        "reference_source": "YUE277",
        "regional_coordinate_status": "deterministic_directional_surrogates_paper_coordinates_unreported",
        "regional_sources": REGIONS,
        "uniformity_status": "trend_only_paper_spatial_mask_unreported",
        "fig4_direct_comparison": {
            "median_absolute_relative_error": float(np.median([abs(row["modeled_over_digitized"] - 1.0) for row in direct_rows])),
            "maximum_headline_relative_error_depth40_60": max(
                abs(row["modeled_over_digitized"] - 1.0) for row in headline_rows
            ),
            "inside_digitization_interval_count": sum(bool(row["inside_digitization_interval"]) for row in direct_rows),
            "point_count": len(direct_rows),
            "spearman_r": fig4_spearman,
        },
        "frozen_acceptance_evaluation": acceptance_evaluation,
        "outputs": {},
    }
    for path in sorted(output_dir.iterdir()):
        if path.name != "summary.json" and path.is_file():
            summary["outputs"][path.name] = sha256_file(path)
    _write_json(output_dir / "summary.json", summary)


if __name__ == "__main__":
    main()
