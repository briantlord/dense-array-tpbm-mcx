#!/usr/bin/env python3
"""Compare 810- and corrected-1070 absorbed energy by tissue and head depth."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
import json
import sys
from mcx_project.provenance import capture_code
import os
from pathlib import Path
import tempfile
from typing import Any

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
ANATOMY = Path(
    "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/"
    "colin27_labels_native12_1mm_v3.nii"
)
OPTICAL_810 = Path(
    "inputs/optical_properties/provisional_810_v2/central_refined_primary.json"
)
OPTICAL_1070 = Path("inputs/fat_absorption_bracket_v1/fat_abs_010.json")
FLUENCE_810 = Path(
    "results/surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_v2/"
    "total_fluence_constant_total.npy"
)
ABSORBED_810 = Path(
    "results/surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_v2/"
    "absorbed_energy_density_constant_total.npy"
)
FLUENCE_1070 = Path(
    "results/surrogate_yue277_1070_fat_absorption_bracket_v1/fat_abs_010/"
    "total_fluence_constant_total.npy"
)
OUTPUT = Path("results/surrogate_yue277_810_vs_1070_regional_absorbed_energy_v2")
AUDIT = Path("results/two_wavelength_mc_audit_20260904_v1/result_summary.json")
AUDIT_PROTOCOL = Path("results/two_wavelength_mc_audit_20260904_v1/protocol.json")

DEPTH_BINS_MM = (
    (0.0, 10.0, "<10 mm"),
    (10.0, 20.0, "10-20 mm"),
    (20.0, 30.0, "20-30 mm"),
    (30.0, 40.0, "30-40 mm"),
    (40.0, 50.0, "40-50 mm"),
    (50.0, float("inf"), ">=50 mm"),
)
TISSUES = ((2, "gray_matter"), (3, "white_matter"))


def load_json(relative: Path) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
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


def atomic_npy(path: Path, value: np.ndarray) -> None:
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


def mua_volume(labels: np.ndarray, optical: dict[str, Any]) -> np.ndarray:
    output = np.zeros(labels.shape, dtype=np.float64)
    for row in optical["tissues"]:
        output[labels == int(row["tissue_id"])] = float(row["mua_mm-1"])
    return output


def external_head_depth(labels: np.ndarray, spacing: tuple[float, float, float]) -> np.ndarray:
    """Distance inside the head envelope from exterior-connected background."""

    background = labels == 0
    border_seed = np.zeros(labels.shape, dtype=bool)
    border_seed[[0, -1], :, :] = background[[0, -1], :, :]
    border_seed[:, [0, -1], :] = background[:, [0, -1], :]
    border_seed[:, :, [0, -1]] = background[:, :, [0, -1]]
    exterior = ndimage.binary_propagation(border_seed, mask=background)
    envelope = ~exterior
    return ndimage.distance_transform_edt(envelope, sampling=spacing).astype(np.float32)


def summarize_roi(
    absorbed: np.ndarray,
    mask: np.ndarray,
    voxel_volume_mm3: float,
) -> dict[str, Any]:
    values = np.asarray(absorbed[mask], dtype=np.float64)
    count = int(values.size)
    if count == 0:
        return {
            "voxel_count": 0,
            "volume_cm3": 0.0,
            "absorbed_fraction_per_joule_launched": 0.0,
            "absorbed_percent_of_launched": 0.0,
            "absorbed_j_per_100j_launched": 0.0,
            "mean_mj_cm3_per_100j_launched": None,
            "median_mj_cm3_per_100j_launched": None,
            "p95_mj_cm3_per_100j_launched": None,
            "p99_mj_cm3_per_100j_launched": None,
        }
    integrated = float(np.sum(values, dtype=np.float64) * voxel_volume_mm3)
    scale_100j_mj_cm3 = 1.0e8
    return {
        "voxel_count": count,
        "volume_cm3": count * voxel_volume_mm3 / 1000.0,
        "absorbed_fraction_per_joule_launched": integrated,
        "absorbed_percent_of_launched": integrated * 100.0,
        "absorbed_j_per_100j_launched": integrated * 100.0,
        "mean_mj_cm3_per_100j_launched": float(np.mean(values) * scale_100j_mj_cm3),
        "median_mj_cm3_per_100j_launched": float(np.median(values) * scale_100j_mj_cm3),
        "p95_mj_cm3_per_100j_launched": float(np.quantile(values, 0.95) * scale_100j_mj_cm3),
        "p99_mj_cm3_per_100j_launched": float(np.quantile(values, 0.99) * scale_100j_mj_cm3),
    }


def extract_plane(value: np.ndarray, axis: int, index: int) -> np.ndarray:
    if axis == 0:
        plane = value[index, :, :]
    elif axis == 1:
        plane = value[:, index, :]
    else:
        plane = value[:, :, index]
    return np.rot90(plane)


def anatomy_rgb(labels: np.ndarray) -> np.ndarray:
    palette = np.array(
        [
            [5, 8, 14], [45, 85, 145], [190, 140, 65], [220, 215, 195],
            [95, 65, 35], [115, 45, 60], [145, 75, 70], [175, 175, 175],
            [5, 8, 14], [95, 65, 35], [125, 140, 160], [185, 150, 85],
            [160, 30, 40],
        ],
        dtype=np.uint8,
    )
    return palette[np.clip(labels.astype(np.int64), 0, len(palette) - 1)]


def magma_rgb(normalized: np.ndarray) -> np.ndarray:
    x = np.clip(normalized, 0.0, 1.0)
    anchors = np.array(
        [[5, 5, 18], [70, 18, 92], [170, 45, 93], [245, 110, 45], [252, 245, 165]],
        dtype=np.float64,
    )
    position = x * (len(anchors) - 1)
    lower = np.floor(position).astype(int)
    upper = np.minimum(lower + 1, len(anchors) - 1)
    weight = (position - lower)[..., None]
    return np.asarray(anchors[lower] * (1.0 - weight) + anchors[upper] * weight, dtype=np.uint8)


def diverging_rgb(normalized: np.ndarray) -> np.ndarray:
    x = np.clip(normalized, -1.0, 1.0)
    output = np.empty(x.shape + (3,), dtype=np.float64)
    negative = x < 0
    positive = ~negative
    t = np.abs(x)
    white = np.array([245.0, 245.0, 245.0])
    blue = np.array([42.0, 92.0, 170.0])
    red = np.array([190.0, 45.0, 45.0])
    output[negative] = white * (1.0 - t[negative, None]) + blue * t[negative, None]
    output[positive] = white * (1.0 - t[positive, None]) + red * t[positive, None]
    return np.asarray(output, dtype=np.uint8)


def labeled_panel(image: Image.Image, title: str, caption: str = "") -> Image.Image:
    target = image.resize((420, 420), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (420, 474), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), title, fill="black")
    if caption:
        draw.text((10, 30), caption, fill=(60, 60, 60))
    canvas.paste(target, (0, 54))
    return canvas


def plot_slices(
    output: Path,
    labels: np.ndarray,
    absorbed_by_nm: dict[int, np.ndarray],
    brain_mask: np.ndarray,
) -> None:
    center = np.rint(np.argwhere(brain_mask).mean(axis=0)).astype(int)
    planes = (
        ("Sagittal", 0, int(center[0])),
        ("Coronal", 1, int(center[1])),
        ("Axial", 2, int(center[2])),
    )
    positive = np.concatenate(
        [values[brain_mask & (values > 0)] for values in absorbed_by_nm.values()]
    ) * 1.0e8
    lower = float(np.quantile(positive, 0.01))
    upper = float(np.quantile(positive, 0.995))
    panels: list[Image.Image] = []
    for row_index, wavelength in enumerate((810, 1070)):
        volume = absorbed_by_nm[wavelength] * 1.0e8
        for column, (name, axis, index) in enumerate(planes):
            values = extract_plane(volume, axis, index)
            label_plane = extract_plane(labels, axis, index)
            mask_plane = extract_plane(brain_mask, axis, index)
            normalized = np.zeros(values.shape, dtype=np.float64)
            valid = mask_plane & (values > 0)
            normalized[valid] = np.clip(
                (np.log10(values[valid]) - np.log10(lower))
                / (np.log10(upper) - np.log10(lower)),
                0.0,
                1.0,
            )
            base = anatomy_rgb(label_plane).astype(np.float64) * 0.32
            heat = magma_rgb(normalized).astype(np.float64)
            alpha = np.where(valid, 0.94, 0.0)[..., None]
            rendered = np.asarray(base * (1.0 - alpha) + heat * alpha, dtype=np.uint8)
            panels.append(
                labeled_panel(
                    Image.fromarray(rendered),
                    f"{wavelength} nm — {name}",
                    f"log scale {lower:.3g} to {upper:.3g} mJ/cm³ per 100 J",
                )
            )
    canvas = Image.new("RGB", (1260, 1010), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 14), "Brain absorbed-energy density | equal-total 277-emitter weighting", fill="black")
    draw.text((20, 34), "Same logarithmic scale for both wavelengths", fill=(70, 70, 70))
    for number, panel in enumerate(panels):
        canvas.paste(panel, ((number % 3) * 420, 62 + (number // 3) * 474))
    canvas.save(output)


def plot_ratio_slices(
    output: Path,
    absorbed_810: np.ndarray,
    absorbed_1070: np.ndarray,
    brain_mask: np.ndarray,
) -> None:
    center = np.rint(np.argwhere(brain_mask).mean(axis=0)).astype(int)
    planes = (
        ("Sagittal", 0, int(center[0])),
        ("Coronal", 1, int(center[1])),
        ("Axial", 2, int(center[2])),
    )
    ratio = np.full(brain_mask.shape, np.nan, dtype=np.float64)
    valid = brain_mask & (absorbed_810 > 0) & (absorbed_1070 > 0)
    ratio[valid] = np.log2(absorbed_810[valid] / absorbed_1070[valid])
    limit = 4.0
    panels: list[Image.Image] = []
    for column, (name, axis, index) in enumerate(planes):
        values = extract_plane(ratio, axis, index)
        valid = np.isfinite(values)
        rendered = np.full(values.shape + (3,), 18, dtype=np.uint8)
        rendered[valid] = diverging_rgb(values[valid] / limit)
        panels.append(
            labeled_panel(
                Image.fromarray(rendered),
                name,
                f"blue = 1070; red = 810; ±{limit:.2f} log₂ ratio",
            )
        )
    canvas = Image.new("RGB", (1260, 560), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 14), "Relative absorbed-energy density: 810 nm versus 1070 nm", fill="black")
    draw.text((20, 34), "White = equal; one log₂ unit = a factor of two", fill=(70, 70, 70))
    for number, panel in enumerate(panels):
        canvas.paste(panel, (number * 420, 62))
    canvas.save(output)


def plot_depth_profiles(output: Path, rows: list[dict[str, Any]]) -> None:
    shell_rows = [row for row in rows if row["depth_bin"] != "all depths"]
    labels_order = [label for _, _, label in DEPTH_BINS_MM]
    colors = {810: (35, 105, 180), 1070: (215, 95, 25)}
    canvas = Image.new("RGB", (1600, 760), "white")
    draw = ImageDraw.Draw(canvas)
    draw.font = ImageFont.load_default(size=17)
    draw.text((20, 14), "Absorption versus geometric depth below the external head surface", fill="black")
    plot_boxes = ((80, 95, 760, 620), (880, 95, 1560, 620))
    series: dict[tuple[int, str], tuple[list[float], list[float]]] = {}

    def dashed_line(points: list[tuple[float, float]], color: tuple[int, int, int], width: int = 4) -> None:
        for start, end in zip(points[:-1], points[1:]):
            dx, dy = end[0] - start[0], end[1] - start[1]
            length = float(np.hypot(dx, dy))
            if length <= 0:
                continue
            position = 0.0
            while position < length:
                segment_end = min(position + 10.0, length)
                p0 = (start[0] + dx * position / length, start[1] + dy * position / length)
                p1 = (start[0] + dx * segment_end / length, start[1] + dy * segment_end / length)
                draw.line((p0, p1), fill=color, width=width)
                position += 17.0
    for wavelength in (810, 1070):
        for tissue in ("gray_matter", "white_matter"):
            selected = {
                row["depth_bin"]: row
                for row in shell_rows
                if row["wavelength_nm"] == wavelength and row["tissue"] == tissue
            }
            integrated = [selected[label]["absorbed_j_per_100j_launched"] for label in labels_order]
            density = [selected[label]["mean_mj_cm3_per_100j_launched"] for label in labels_order]
            series[(wavelength, tissue)] = (integrated, density)

    def draw_panel(box: tuple[int, int, int, int], value_index: int, log_y: bool, title: str, y_label: str) -> None:
        x0, y0, x1, y1 = box
        draw.rectangle(box, outline="black", width=2)
        draw.text((x0, y0 - 28), title, fill="black")
        pooled = [value for pair in series.values() for value in pair[value_index] if value > 0]
        if log_y:
            low = min(pooled)
            high = max(pooled)
            transform = lambda value: np.log10(max(value, low))
            low_t, high_t = np.log10(low), np.log10(high)
        else:
            low_t, high_t = 0.0, max(pooled)
            transform = lambda value: value
        for tick in np.linspace(low_t, high_t, 5):
            py = y1 - 25 - (tick - low_t) / max(high_t - low_t, 1e-15) * (y1 - y0 - 50)
            draw.line((x0, py, x1, py), fill=(225, 225, 225), width=1)
            value = 10 ** tick if log_y else tick
            draw.text((x0 - 8, py), f"{value:.1e}" if log_y else f"{value:.2f}", anchor="rm", fill="black")
        for wavelength in (810, 1070):
            for tissue in ("gray_matter", "white_matter"):
                values = series[(wavelength, tissue)][value_index]
                points = []
                for index, value in enumerate(values):
                    px = x0 + 25 + index * (x1 - x0 - 50) / (len(values) - 1)
                    py = y1 - 25 - (transform(value) - low_t) / max(high_t - low_t, 1e-15) * (y1 - y0 - 50)
                    points.append((px, py))
                if tissue == "white_matter":
                    dashed_line(points, colors[wavelength])
                else:
                    draw.line(points, fill=colors[wavelength], width=4)
                for point in points:
                    draw.ellipse((point[0] - 4, point[1] - 4, point[0] + 4, point[1] + 4), fill=colors[wavelength])
        for index, label in enumerate(labels_order):
            px = x0 + 25 + index * (x1 - x0 - 50) / (len(labels_order) - 1)
            draw.text((px - 30, y1 + 10), label, fill="black")
        draw.text((x0, y1 + 42), y_label, fill=(50, 50, 50))

    draw_panel(plot_boxes[0], 0, False, "Integrated absorbed energy", "J per shell per 100 J total launched")
    draw_panel(plot_boxes[1], 1, True, "Mean local absorbed-energy density", "mJ/cm^3 per 100 J total launched")
    legend_y = 700
    for number, (wavelength, tissue) in enumerate(((810, "gray_matter"), (810, "white_matter"), (1070, "gray_matter"), (1070, "white_matter"))):
        x = 80 + number * 340
        if tissue == "white_matter":
            dashed_line([(x, legend_y), (x + 45, legend_y)], colors[wavelength])
        else:
            draw.line((x, legend_y, x + 45, legend_y), fill=colors[wavelength], width=4)
        draw.text((x + 55, legend_y - 8), f"{wavelength} nm {tissue.replace('_', ' ')}", fill="black")
    canvas.save(output)


def write_report(
    output: Path,
    rows: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    checks: dict[str, Any],
) -> None:
    ratio_text = lambda row: f"{row['ratio_810_to_1070']:.3g}x" if row["ratio_qualified"] else "not qualified"
    comparison_by_key = {(row["tissue"], row["depth_bin"]): row for row in comparisons}
    overall = {
        (row["wavelength_nm"], row["tissue"]): row
        for row in rows
        if row["depth_bin"] == "all depths"
    }
    lines = [
        "# Regional absorbed-energy-density comparison",
        "",
        "This analysis uses the saved equal-total 277-emitter fields. Values scale linearly with total launched optical energy or power; the project calibration is numerical and is not a measured device output.",
        "",
        "Ratios failing the independent aggregate Monte Carlo or minimum-signal gates are suppressed. Passing ratios remain conditional on these optical/anatomical scenarios. No voxelwise ratio map is generated because no voxelwise convergence evidence has been established.",
        "",
        "## Whole tissue classes",
        "",
        "| Tissue | 810 absorbed per 100 J | 1070 absorbed per 100 J | 810/1070 |",
        "|---|---:|---:|---:|",
    ]
    for tissue in ("gray_matter", "white_matter"):
        a = overall[(810, tissue)]["absorbed_j_per_100j_launched"]
        b = overall[(1070, tissue)]["absorbed_j_per_100j_launched"]
        lines.append(f"| {tissue.replace('_', ' ').title()} | {a:.6f} J | {b:.6f} J | {ratio_text(comparison_by_key[(tissue, 'all depths')])} |")
    a_total = sum(overall[(810, tissue)]["absorbed_j_per_100j_launched"] for tissue in ("gray_matter", "white_matter"))
    b_total = sum(overall[(1070, tissue)]["absorbed_j_per_100j_launched"] for tissue in ("gray_matter", "white_matter"))
    lines.extend(
        [
            f"| **Total brain** | **{a_total:.6f} J** | **{b_total:.6f} J** | **{ratio_text(comparison_by_key[('brain_total', 'all depths')])}** |",
            "",
            "## Depth-resolved absorption",
            "",
            "Depth is the shortest Euclidean distance from each voxel to exterior-connected background through the filled head envelope. It is a geometric depth measure, not a named anatomical parcellation or an optical path length.",
            "",
            "### Gray and white matter combined",
            "",
            "| Depth | 810 J/100 J | 1070 J/100 J | 810/1070 |",
            "|---:|---:|---:|---:|",
        ]
    )
    comparison_by_key = {(row["tissue"], row["depth_bin"]): row for row in comparisons}
    for _, _, label in DEPTH_BINS_MM:
        row = comparison_by_key[("brain_total", label)]
        lines.append(
            f"| {label} | {row['absorbed_j_per_100j_810']:.4e} | "
            f"{row['absorbed_j_per_100j_1070']:.4e} | {ratio_text(row)} |"
        )
    lines.extend(
        [
            "",
            "### Tissue-specific detail",
            "",
            "| Tissue | Depth | 810 J/100 J | 1070 J/100 J | 810/1070 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for tissue in ("gray_matter", "white_matter"):
        for _, _, label in DEPTH_BINS_MM:
            row = comparison_by_key[(tissue, label)]
            lines.append(
                f"| {tissue.replace('_', ' ').title()} | {label} | "
                f"{row['absorbed_j_per_100j_810']:.4e} | {row['absorbed_j_per_100j_1070']:.4e} | "
                f"{ratio_text(row)} |"
            )
    lines.extend(
        [
            "",
            "## Scaling",
            "",
            "For a real total launched energy `E` joules, multiply every `J per 100 J` value by `E/100`. For continuous total optical power `P` watts, each reported mean `mJ/cm³ per 100 J` becomes `mW/cm³` after multiplying by `P/100`. This assumes the real emitter weighting matches the equal-total uniform model.",
            "",
            "Absorbed-energy density is an optical deposition metric. It does not by itself predict temperature, photochemistry, or biological efficacy.",
            "",
            "## Verification",
            "",
            f"- 810 stored absorbed field consistency: maximum absolute error `{checks['stored_810_absorbed_max_abs_error']:.3e}`.",
            f"- 810 whole-brain absorbed fraction: `{checks['brain_absorbed_fraction_810']:.12f}`.",
            f"- 1070 whole-brain absorbed fraction: `{checks['brain_absorbed_fraction_1070']:.12f}`.",
            "- All declared input and output files are SHA-256 recorded in `manifest.json`.",
            "",
        ]
    )
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    output = ROOT / OUTPUT
    output.mkdir(parents=True, exist_ok=False)

    image = nib.load(ROOT / ANATOMY)
    labels = np.asarray(image.dataobj, dtype=np.uint8)
    spacing = tuple(float(value) for value in image.header.get_zooms()[:3])
    voxel_volume = float(np.prod(spacing))
    brain_mask = np.isin(labels, [2, 3])

    fluence_810 = np.asarray(np.load(ROOT / FLUENCE_810), dtype=np.float64)
    stored_absorbed_810 = np.asarray(np.load(ROOT / ABSORBED_810), dtype=np.float64)
    fluence_1070 = np.asarray(np.load(ROOT / FLUENCE_1070), dtype=np.float64)
    if fluence_810.shape != labels.shape or fluence_1070.shape != labels.shape:
        raise RuntimeError("aggregate field and anatomy shapes do not match")

    absorbed_810 = fluence_810 * mua_volume(labels, load_json(OPTICAL_810))
    absorbed_1070 = fluence_1070 * mua_volume(labels, load_json(OPTICAL_1070))
    stored_error = float(np.max(np.abs(absorbed_810 - stored_absorbed_810)))
    if stored_error > 1e-12:
        raise RuntimeError(f"stored 810 absorbed field is inconsistent: {stored_error}")

    depth = external_head_depth(labels, spacing)
    atomic_npy(output / "depth_below_external_head_surface_mm.npy", depth)
    atomic_npy(output / "absorbed_energy_density_1070_constant_total.npy", absorbed_1070)

    rows: list[dict[str, Any]] = []
    absorbed_by_nm = {810: absorbed_810, 1070: absorbed_1070}
    for wavelength, absorbed in absorbed_by_nm.items():
        rows.append(
            {
                "wavelength_nm": wavelength,
                "tissue_id": -1,
                "tissue": "brain_total",
                "depth_min_mm": 0.0,
                "depth_max_mm": None,
                "depth_bin": "all depths",
                **summarize_roi(absorbed, brain_mask, voxel_volume),
            }
        )
        for lower, upper, name in DEPTH_BINS_MM:
            shell = brain_mask & (depth >= lower) & (depth < upper)
            rows.append(
                {
                    "wavelength_nm": wavelength,
                    "tissue_id": -1,
                    "tissue": "brain_total",
                    "depth_min_mm": lower,
                    "depth_max_mm": None if np.isinf(upper) else upper,
                    "depth_bin": name,
                    **summarize_roi(absorbed, shell, voxel_volume),
                }
            )
        for tissue_id, tissue_name in TISSUES:
            tissue_mask = labels == tissue_id
            rows.append(
                {
                    "wavelength_nm": wavelength,
                    "tissue_id": tissue_id,
                    "tissue": tissue_name,
                    "depth_min_mm": 0.0,
                    "depth_max_mm": None,
                    "depth_bin": "all depths",
                    **summarize_roi(absorbed, tissue_mask, voxel_volume),
                }
            )
            for lower, upper, name in DEPTH_BINS_MM:
                shell = tissue_mask & (depth >= lower) & (depth < upper)
                rows.append(
                    {
                        "wavelength_nm": wavelength,
                        "tissue_id": tissue_id,
                        "tissue": tissue_name,
                        "depth_min_mm": lower,
                        "depth_max_mm": None if np.isinf(upper) else upper,
                        "depth_bin": name,
                        **summarize_roi(absorbed, shell, voxel_volume),
                    }
                )

    by_key = {(row["wavelength_nm"], row["tissue"], row["depth_bin"]): row for row in rows}
    audit = load_json(AUDIT)
    audit_protocol = load_json(AUDIT_PROTOCOL)
    expected_baselines = {810: FLUENCE_810, 1070: FLUENCE_1070}
    for scenario in audit_protocol["scenarios"]:
        if sha256_file(ROOT / expected_baselines[scenario["wavelength_nm"]]) != scenario["baseline_fluence_sha256"]:
            raise ValueError("Monte Carlo audit does not qualify these baseline fields")
    comparisons: list[dict[str, Any]] = []
    for tissue_id, tissue_name in ((-1, "brain_total"), *TISSUES):
        for depth_name in ("all depths", *(name for _, _, name in DEPTH_BINS_MM)):
            a = by_key[(810, tissue_name, depth_name)]
            b = by_key[(1070, tissue_name, depth_name)]
            audit_tissue = "brain" if tissue_name == "brain_total" else tissue_name
            if depth_name == "all depths":
                endpoint = audit_tissue
            else:
                lo, hi, _ = next(item for item in DEPTH_BINS_MM if item[2] == depth_name)
                endpoint = f"{audit_tissue}__depth_{int(lo)}_{int(hi) if np.isfinite(hi) else 'inf'}_mm"
            qualified = audit["ratios_810_over_1070"][endpoint]["qualified"]
            comparisons.append(
                {
                    "tissue_id": tissue_id,
                    "tissue": tissue_name,
                    "depth_bin": depth_name,
                    "voxel_count": a["voxel_count"],
                    "volume_cm3": a["volume_cm3"],
                    "absorbed_j_per_100j_810": a["absorbed_j_per_100j_launched"],
                    "absorbed_j_per_100j_1070": b["absorbed_j_per_100j_launched"],
                    "ratio_qualified": qualified,
                    "ratio_status": "conditional_MC_screen_pass" if qualified else "suppressed_failed_MC_or_signal_gate",
                    "ratio_810_to_1070": (
                        a["absorbed_j_per_100j_launched"] / b["absorbed_j_per_100j_launched"]
                        if qualified and b["absorbed_j_per_100j_launched"] > 0
                        else None
                    ),
                    "mean_mj_cm3_per_100j_810": a["mean_mj_cm3_per_100j_launched"],
                    "mean_mj_cm3_per_100j_1070": b["mean_mj_cm3_per_100j_launched"],
                    "p95_mj_cm3_per_100j_810": a["p95_mj_cm3_per_100j_launched"],
                    "p95_mj_cm3_per_100j_1070": b["p95_mj_cm3_per_100j_launched"],
                }
            )

    with (output / "regional_absorption_long.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (output / "regional_absorption_comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)

    plot_slices(output / "absorbed_energy_density_slices.png", labels, absorbed_by_nm, brain_mask)
    # Voxelwise ratios require voxelwise uncertainty; ROI gates do not qualify them.
    plot_depth_profiles(output / "depth_profiles.png", rows)

    checks = {
        "stored_810_absorbed_max_abs_error": stored_error,
        "brain_absorbed_fraction_810": float(np.sum(absorbed_810[brain_mask]) * voxel_volume),
        "brain_absorbed_fraction_1070": float(np.sum(absorbed_1070[brain_mask]) * voxel_volume),
    }
    result = {
        "result_id": "surrogate_yue277_810_vs_1070_regional_absorbed_energy_v2",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "scientific_status": "provisional_normalized_transport_not_measured_device_power_not_biological_efficacy",
        "normalization": "unit total launched energy divided uniformly across 277 emitters",
        "depth_definition": "Euclidean distance from exterior-connected background through the filled non-exterior head envelope",
        "units": {
            "absorbed_field": "absorbed fraction per mm^3 per unit total launched energy",
            "integrated": "absorbed energy fraction per unit total launched energy",
            "reported_density": "mJ/cm^3 per 100 J total launched energy",
        },
        "checks": checks,
        "regional_rows": rows,
        "comparisons": comparisons,
        "voxel_ratio_status": "suppressed_no_voxelwise_uncertainty",
    }
    atomic_json(output / "result.json", result)
    write_report(output, rows, comparisons, checks)

    input_paths = (AUDIT, AUDIT_PROTOCOL, ANATOMY, OPTICAL_810, OPTICAL_1070, FLUENCE_810, ABSORBED_810, FLUENCE_1070)
    manifest = {
        "provenance": capture_code(ROOT, Path(__file__), sys.argv[1:]),
        "result_id": result["result_id"],
        "created_at": result["created_at"],
        "inputs": [
            {"path": path.as_posix(), "sha256": sha256_file(ROOT / path)} for path in input_paths
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
    atomic_json(output / "manifest.json", manifest)
    print(json.dumps({"status": "complete", "output": OUTPUT.as_posix(), "checks": checks}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
