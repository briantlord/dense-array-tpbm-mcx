#!/usr/bin/env python3
"""Stream and analyze the completed Windows RTX 3080 Ti surrogate basis."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw

from mcx_project.aggregation import (
    StreamingContributionSummary,
    finalize_streaming_metrics,
    stream_contribution_statistics,
)
from mcx_project.hashing import sha256_file
from mcx_project.provenance import capture_code
from mcx_project.optics import validate_optical_table
from mcx_project.standalone import load_jnii_field
from mcx_project.validation import load_json, validate_json


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = Path("runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1/index.json")
INVENTORY_PATH = Path(
    "results/surrogate_yue277_1070_windows_rtx3080ti_opencl_v1/post_run_inventory.json"
)
ANALYSIS_PATH = Path("configs/surrogate_yue277_1070_v1_analysis_v2.json")
ANATOMY_METADATA_PATH = Path(
    "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/anatomy_metadata.json"
)
OPTICAL_PATH = Path("inputs/optical_properties/provisional_1070_v1/central.json")
GEOMETRY_PATH = Path("inputs/emitters/surrogate_yue277_1070_v1/emitter_geometry.json")
CONVERGENCE_PROTOCOL_PATH = Path(
    "configs/surrogate_yue277_1070_v1_regional_convergence_extension_v2.json"
)
OUTPUT_DIR = Path(
    "results/surrogate_yue277_1070_windows_rtx3080ti_opencl_analysis_v1"
)
SOURCE_PREFIX = "SUR1070"
WAVELENGTH_NM = 1070
RESULT_ID = "surrogate_yue277_1070_windows_rtx3080ti_opencl_analysis_v1"
MANIFEST_ID = "surrogate_yue277_1070_windows_rtx3080ti_opencl_analysis_manifest_v1"
REGIONAL_EMITTERS = {
    "anterior": "SUR1070_011",
    "left temporal": "SUR1070_022",
    "posterior": "SUR1070_031",
    "right temporal": "SUR1070_040",
    "superior": "SUR1070_275",
}


DEFAULT_SPEC = {
    "index_path": INDEX_PATH,
    "inventory_path": INVENTORY_PATH,
    "analysis_path": ANALYSIS_PATH,
    "anatomy_metadata_path": ANATOMY_METADATA_PATH,
    "optical_path": OPTICAL_PATH,
    "geometry_path": GEOMETRY_PATH,
    "convergence_protocol_path": CONVERGENCE_PROTOCOL_PATH,
    "output_dir": OUTPUT_DIR,
    "source_prefix": SOURCE_PREFIX,
    "wavelength_nm": WAVELENGTH_NM,
    "result_id": RESULT_ID,
    "manifest_id": MANIFEST_ID,
    "regional_emitters": REGIONAL_EMITTERS,
}


def _write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _write_npy(path: Path, value: np.ndarray) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        np.save(stream, value, allow_pickle=False)
    os.replace(temporary, path)


def _strip_gate(field: np.ndarray) -> np.ndarray:
    while field.ndim > 3 and field.shape[-1] == 1:
        field = field[..., 0]
    return field


def _extract_plane(value: np.ndarray, axis: int, index: int) -> np.ndarray:
    if axis == 0:
        plane = value[index, :, :]
    elif axis == 1:
        plane = value[:, index, :]
    else:
        plane = value[:, :, index]
    return np.rot90(plane)


def _anatomy_rgb(labels: np.ndarray) -> np.ndarray:
    palette = np.array(
        [
            [8, 12, 20], [45, 85, 145], [214, 158, 74], [225, 218, 196],
            [108, 78, 42], [120, 50, 62], [154, 82, 75], [178, 178, 178],
            [8, 12, 20], [108, 78, 42], [130, 145, 165], [190, 155, 90],
            [165, 35, 45],
        ],
        dtype=np.uint8,
    )
    clipped = np.clip(labels.astype(np.int64), 0, len(palette) - 1)
    return palette[clipped]


def _heat_rgb(normalized: np.ndarray) -> np.ndarray:
    x = np.clip(normalized, 0.0, 1.0)
    red = np.clip(3.0 * x - 1.0, 0.0, 1.0)
    green = np.clip(3.0 * x, 0.0, 1.0) - np.clip(3.0 * x - 2.0, 0.0, 1.0)
    blue = np.clip(1.0 - 3.0 * x, 0.0, 1.0) + np.clip(2.0 - 3.0 * x, 0.0, 1.0)
    return np.asarray(np.stack([red, green, blue], axis=-1) * 255.0, dtype=np.uint8)


def _field_overlay(labels: np.ndarray, field: np.ndarray, maximum: float) -> Image.Image:
    base = _anatomy_rgb(labels).astype(np.float64)
    normalized = np.zeros(field.shape, dtype=np.float64)
    positive = field > 0
    if maximum > 0:
        normalized[positive] = np.clip(
            (np.log10(field[positive] / maximum) + 6.0) / 6.0, 0.0, 1.0
        )
    heat = _heat_rgb(normalized).astype(np.float64)
    alpha = np.where(normalized > 0, 0.18 + 0.72 * normalized, 0.0)[..., None]
    output = np.asarray(base * (1.0 - alpha) + heat * alpha, dtype=np.uint8)
    return Image.fromarray(output, mode="RGB")


def _scalar_image(
    labels: np.ndarray,
    values: np.ndarray,
    *,
    low: float,
    high: float,
    mask: np.ndarray | None = None,
) -> Image.Image:
    base = _anatomy_rgb(labels).astype(np.float64) * 0.45
    valid = np.isfinite(values)
    if mask is not None:
        valid &= mask
    normalized = np.zeros(values.shape, dtype=np.float64)
    if high > low:
        normalized[valid] = np.clip((values[valid] - low) / (high - low), 0.0, 1.0)
    heat = _heat_rgb(normalized).astype(np.float64)
    alpha = np.where(valid, 0.86, 0.0)[..., None]
    return Image.fromarray(np.asarray(base * (1 - alpha) + heat * alpha, dtype=np.uint8))


def _panel(image: Image.Image, title: str, *, size: tuple[int, int] = (300, 300)) -> Image.Image:
    rendered = image.resize(size, Image.Resampling.BILINEAR)
    canvas = Image.new("RGB", (size[0], size[1] + 38), "white")
    canvas.paste(rendered, (0, 38))
    ImageDraw.Draw(canvas).text((8, 11), title, fill="black")
    return canvas


def _grid(panels: list[Image.Image], columns: int, path: Path, heading: str) -> None:
    width = max(panel.width for panel in panels)
    height = max(panel.height for panel in panels)
    rows = (len(panels) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * width, rows * height + 44), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 14), heading, fill="black")
    for number, panel in enumerate(panels):
        canvas.paste(panel, ((number % columns) * width, 44 + (number // columns) * height))
    canvas.save(path)


def _representative_row(
    labels: np.ndarray,
    field: np.ndarray,
    position: list[float],
    region: str,
    emitter_id: str,
) -> list[Image.Image]:
    indices = [int(np.clip(round(position[i]), 0, field.shape[i] - 1)) for i in range(3)]
    names = ("sagittal", "coronal", "axial")
    maximum = float(np.max(field))
    panels: list[Image.Image] = []
    for axis, name in enumerate(names):
        label_plane = _extract_plane(labels, axis, indices[axis])
        field_plane = _extract_plane(field, axis, indices[axis])
        image = _field_overlay(label_plane, field_plane, maximum)
        if axis == 0:
            marker = np.zeros((field.shape[1], field.shape[2]), dtype=np.uint8)
            marker[indices[1], indices[2]] = 1
        elif axis == 1:
            marker = np.zeros((field.shape[0], field.shape[2]), dtype=np.uint8)
            marker[indices[0], indices[2]] = 1
        else:
            marker = np.zeros((field.shape[0], field.shape[1]), dtype=np.uint8)
            marker[indices[0], indices[1]] = 1
        marker = np.rot90(marker)
        y, x = np.unravel_index(np.argmax(marker), marker.shape)
        draw = ImageDraw.Draw(image)
        draw.line((x - 5, y, x + 5, y), fill=(255, 40, 40), width=2)
        draw.line((x, y - 5, x, y + 5), fill=(255, 40, 40), width=2)
        panels.append(_panel(image, f"{region} | {emitter_id} | {name}"))
    return panels


def _metric_distribution_image(
    metrics: dict[str, np.ndarray], masks: dict[str, np.ndarray], path: Path, reference_emitter: str
) -> None:
    keys = [
        ("ef_dom", "EF_dom"),
        ("non_dominant_contribution_fraction", "NCF"),
        ("n_eff", "N_eff"),
        ("ef_ref", f"EF_ref ({reference_emitter})"),
    ]
    canvas = Image.new("RGB", (1120, 820), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 16), "Gray- and white-matter overlap distributions", fill="black")
    colors = {"gray_matter": (205, 125, 25), "white_matter": (55, 105, 190)}
    for panel_number, (key, title) in enumerate(keys):
        x0 = 60 + (panel_number % 2) * 540
        y0 = 70 + (panel_number // 2) * 370
        x1, y1 = x0 + 460, y0 + 285
        plot_values = metrics[key]
        if key == "ef_ref":
            plot_values = np.where(plot_values > 0, np.log10(plot_values), np.nan)
            title = f"log10 EF_ref ({reference_emitter})"
        draw.rectangle((x0, y0, x1, y1), outline="black")
        draw.text((x0, y0 - 24), title, fill="black")
        pooled = np.concatenate(
            [plot_values[mask & np.isfinite(plot_values)] for mask in masks.values()]
        )
        upper = float(np.quantile(pooled, 0.99)) if pooled.size else 1.0
        lower = 0.0 if key == "non_dominant_contribution_fraction" else 1.0
        upper = max(upper, lower + 1e-12)
        for roi_name, mask in masks.items():
            values = plot_values[mask & np.isfinite(plot_values)]
            clipped = values[(values >= lower) & (values <= upper)]
            counts, _ = np.histogram(clipped, bins=50, range=(lower, upper))
            if np.max(counts, initial=0) == 0:
                continue
            points = []
            for index, count in enumerate(counts):
                px = x0 + index * (x1 - x0) / (len(counts) - 1)
                py = y1 - count * (y1 - y0) / np.max(counts)
                points.append((px, py))
            draw.line(points, fill=colors[roi_name], width=3)
        draw.text((x0, y1 + 8), f"range {lower:.3g} to p99 {upper:.3g}", fill="black")
    draw.line((760, 35, 795, 35), fill=colors["gray_matter"], width=4)
    draw.text((802, 27), "gray matter", fill="black")
    draw.line((920, 35, 955, 35), fill=colors["white_matter"], width=4)
    draw.text((962, 27), "white matter", fill="black")
    canvas.save(path)


def _top_contributor_image(
    source_ids: tuple[str, ...], roi_integrals: dict[str, np.ndarray], path: Path
) -> None:
    canvas = Image.new("RGB", (1160, 820), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 16), "Top integrated fluence contributors by ROI", fill="black")
    for panel_number, roi_name in enumerate(("gray_matter", "white_matter", "brain_total")):
        values = roi_integrals[roi_name]
        order = np.argsort(values)[::-1][:10]
        total = float(np.sum(values, dtype=np.float64))
        x0, y0 = 70, 80 + panel_number * 240
        draw.text((x0, y0 - 26), roi_name.replace("_", " "), fill="black")
        maximum = float(values[order[0]])
        for rank, source_index in enumerate(order):
            y = y0 + rank * 20
            width = int(570 * values[source_index] / maximum) if maximum else 0
            draw.rectangle((x0 + 155, y, x0 + 155 + width, y + 13), fill=(55, 115, 185))
            draw.text((x0, y), source_ids[source_index], fill="black")
            fraction = values[source_index] / total if total else float("nan")
            draw.text((x0 + 740, y), f"{fraction:.3%}", fill="black")
    canvas.save(path)


def _array_summary(values: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    selected = values[mask & np.isfinite(values)]
    if not selected.size:
        return {"valid_voxel_count": 0}
    return {
        "valid_voxel_count": int(selected.size),
        "mean": float(np.mean(selected)),
        "median": float(np.median(selected)),
        "p05": float(np.quantile(selected, 0.05)),
        "p95": float(np.quantile(selected, 0.95)),
    }


def _field_first(values: np.ndarray, source_ids: tuple[str, ...], reference_id: str) -> dict[str, Any]:
    total = float(np.sum(values, dtype=np.float64))
    dominant_index = int(np.argmax(values))
    dominant = float(values[dominant_index])
    squared_sum = float(np.sum(np.square(values), dtype=np.float64))
    reference = float(values[source_ids.index(reference_id)])
    order = np.argsort(values)[::-1][:10]
    return {
        "total_integrated_fluence": total,
        "dominant_emitter_id": source_ids[dominant_index],
        "dominant_integrated_fluence": dominant,
        "ef_dom": total / dominant if dominant > 0 else None,
        "non_dominant_contribution_fraction": (total - dominant) / total if total > 0 else None,
        "n_eff": total * total / squared_sum if squared_sum > 0 else None,
        "ef_ref": total / reference if reference > 0 else None,
        "reference_emitter_id": reference_id,
        "top_contributors": [
            {
                "rank": rank + 1,
                "emitter_id": source_ids[index],
                "integrated_fluence": float(values[index]),
                "fraction": float(values[index] / total) if total > 0 else None,
            }
            for rank, index in enumerate(order)
        ],
    }


def _output_record(root: Path, path: Path, kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def main(spec: dict | None = None, *, entrypoint: Path | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--spec", type=Path)
    arguments = parser.parse_args()
    settings = dict(DEFAULT_SPEC)
    if spec is not None:
        settings.update(spec)
    if arguments.spec:
        settings.update(load_json(arguments.spec))
    unknown = set(settings) - set(DEFAULT_SPEC)
    if unknown:
        raise ValueError(f"unknown analysis settings: {sorted(unknown)}")
    index_path = Path(settings["index_path"])
    inventory_path = Path(settings["inventory_path"])
    analysis_path = Path(settings["analysis_path"])
    anatomy_metadata_path = Path(settings["anatomy_metadata_path"])
    optical_path = Path(settings["optical_path"])
    geometry_path = Path(settings["geometry_path"])
    convergence_protocol_path = Path(settings["convergence_protocol_path"])
    output_dir = Path(settings["output_dir"])
    source_prefix = settings["source_prefix"]
    wavelength_nm = settings["wavelength_nm"]
    result_id = settings["result_id"]
    manifest_id = settings["manifest_id"]
    regional_emitters = settings["regional_emitters"]
    root = arguments.project_root.resolve()
    output_dir = arguments.output_dir or output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"output directory is not empty; version rather than overwrite: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    validate_json(
        root / "schemas/analysis_configuration.schema.json",
        root / analysis_path,
        require_complete=True,
    )
    analysis = load_json(root / analysis_path)
    index = load_json(root / index_path)
    inventory = load_json(root / inventory_path)
    if inventory["index_sha256"] != sha256_file(root / index_path):
        raise ValueError("inventory does not describe the selected basis index")
    anatomy_metadata = load_json(root / anatomy_metadata_path)
    optical = load_json(root / optical_path)
    validate_optical_table(optical)
    geometry = load_json(root / geometry_path)
    convergence = load_json(root / convergence_protocol_path)
    if inventory["manifest_status_counts"] != {"complete": 277}:
        raise SystemExit("post-run inventory is not a complete 277-source basis")
    if inventory["failure_record_count"] != 0 or not inventory["backend_equivalence_passed"]:
        raise SystemExit("post-run inventory failed its completion/equivalence gate")
    if len(index["runs"]) != 277:
        raise SystemExit("basis index must contain exactly 277 runs")
    if convergence["regional_emitter_ids"] != {
        key.replace(" ", "_"): value for key, value in regional_emitters.items()
    }:
        raise SystemExit("representative emitter map diverges from the frozen convergence protocol")

    anatomy_path = root / anatomy_metadata["volume_representation"]
    image = nib.load(anatomy_path)
    labels = np.asarray(image.dataobj, dtype=np.uint8)
    shape = tuple(int(value) for value in anatomy_metadata["shape_voxels"])
    if labels.shape != shape:
        raise SystemExit(f"anatomy shape {labels.shape} does not match metadata {shape}")
    masks = {
        "gray_matter": labels == 2,
        "white_matter": labels == 3,
    }
    geometry_by_id = {row["emitter_id"]: row for row in geometry["emitters"]}
    runs = {row["emitter_id"]: row for row in index["runs"]}
    source_ids = tuple(sorted(runs))
    if source_ids != tuple(f"{source_prefix}_{number:03d}" for number in range(1, 278)):
        raise SystemExit(
            f"basis source IDs are not the complete frozen {source_prefix} sequence"
        )

    representative_panels: list[Image.Image] = []
    region_by_source = {value: key for key, value in regional_emitters.items()}

    def field_stream() -> Any:
        for number, source_id in enumerate(source_ids, start=1):
            run = runs[source_id]
            manifest_path = root / run["manifest_path"]
            manifest = load_json(manifest_path)
            if manifest["status"] != "complete" or manifest["source"]["emitter_id"] != source_id:
                raise RuntimeError(f"incomplete or mismatched manifest: {source_id}")
            if sha256_file(root / run["configuration_path"]) != run["configuration_sha256"]:
                raise RuntimeError(f"source configuration checksum mismatch: {source_id}")
            if manifest["inputs"]["optical_properties"]["sha256"] != sha256_file(root / optical_path):
                raise RuntimeError(f"analysis optical scenario does not match source: {source_id}")
            fluence_outputs = [row for row in manifest["outputs"] if row["kind"] == "fluence"]
            if len(fluence_outputs) != 1:
                raise RuntimeError(f"manifest does not have one fluence output: {source_id}")
            record = fluence_outputs[0]
            field_path = root / record["path"]
            actual_hash = sha256_file(field_path)
            if actual_hash != record["sha256"]:
                raise RuntimeError(f"fluence checksum mismatch: {source_id}")
            field = _strip_gate(load_jnii_field(field_path))
            if source_id in region_by_source:
                representative_panels.extend(
                    _representative_row(
                        labels,
                        field,
                        load_json(root / run["configuration_path"])["source"]["position_voxels"],
                        region_by_source[source_id],
                        source_id,
                    )
                )
            if number == 1 or number % 25 == 0 or number == len(source_ids):
                print(f"verified and streamed {number}/{len(source_ids)} fields", flush=True)
            yield source_id, field

    reference_id = analysis["reference_protocol"]["reference_emitter_id"]
    summary: StreamingContributionSummary = stream_contribution_statistics(
        field_stream(),
        expected_shape=shape,
        roi_masks=masks,
        reference_source_id=reference_id,
        voxel_volume_mm3=float(np.prod(image.header.get_zooms()[:3])),
    )
    metrics = finalize_streaming_metrics(
        summary, threshold=float(analysis["ratio_absolute_threshold"])
    )
    roi_integrals = dict(summary.roi_integrals)
    roi_integrals["brain_total"] = roi_integrals["gray_matter"] + roi_integrals["white_matter"]
    full_masks = dict(masks)
    full_masks["brain_total"] = masks["gray_matter"] | masks["white_matter"]

    mua = {int(row["tissue_id"]): float(row["mua_mm-1"]) for row in optical["tissues"]}
    mua_volume = np.zeros(shape, dtype=np.float64)
    for label, value in mua.items():
        mua_volume[labels == label] = value
    absorbed = summary.total * mua_volume
    voxel_volume_mm3 = float(np.prod(image.header.get_zooms()[:3]))
    tissue_names = {
        int(row["tissue_id"]): row["tissue_name"] for row in optical["tissues"]
    }
    tissue_absorption: list[dict[str, Any]] = []
    for tissue_id in sorted(mua):
        tissue_mask = labels == tissue_id
        constant_per_emitter = float(
            np.sum(absorbed[tissue_mask], dtype=np.float64) * voxel_volume_mm3
        )
        constant_total = constant_per_emitter / len(source_ids)
        tissue_absorption.append(
            {
                "tissue_id": tissue_id,
                "tissue_name": tissue_names[tissue_id],
                "voxel_count": int(np.count_nonzero(tissue_mask)),
                "mua_mm-1": mua[tissue_id],
                "absorbed_fraction_constant_per_emitter": constant_per_emitter,
                "absorbed_fraction_constant_total": constant_total,
                "absorbed_percent_constant_total": 100.0 * constant_total,
            }
        )

    arrays = {
        "total_fluence_constant_per_emitter.npy": summary.total,
        "total_fluence_constant_total.npy": summary.total / len(source_ids),
        "absorbed_energy_density_constant_per_emitter.npy": absorbed,
        "absorbed_energy_density_constant_total.npy": absorbed / len(source_ids),
        "dominant_contribution.npy": summary.dominant,
        "dominant_source_index.npy": summary.dominant_source_index,
        "ef_dom.npy": np.asarray(metrics["ef_dom"]),
        f"ef_ref_{source_prefix.lower()}_275.npy": np.asarray(metrics["ef_ref"]),
        "ncf.npy": np.asarray(metrics["non_dominant_contribution_fraction"]),
        "n_eff.npy": np.asarray(metrics["n_eff"]),
    }
    output_paths: list[tuple[Path, str]] = []
    for filename, array in arrays.items():
        path = output_dir / filename
        _write_npy(path, array)
        output_paths.append((path, "array"))

    representative_path = output_dir / "representative_five_region_field_qc.png"
    _grid(
        representative_panels,
        3,
        representative_path,
        "Five-region visual QC | log fluence overlay, red cross = source voxel",
    )
    output_paths.append((representative_path, "figure"))

    centroid = [int(round(value)) for value in np.argwhere(full_masks["brain_total"]).mean(axis=0)]
    total_panels: list[Image.Image] = []
    for values, title in ((summary.total, "total fluence"), (absorbed, "absorbed-energy density")):
        maximum = float(np.max(values))
        for axis, name in enumerate(("sagittal", "coronal", "axial")):
            total_panels.append(
                _panel(
                    _field_overlay(
                        _extract_plane(labels, axis, centroid[axis]),
                        _extract_plane(values, axis, centroid[axis]),
                        maximum,
                    ),
                    f"{title} | {name}",
                )
            )
    total_path = output_dir / "total_fluence_absorbed_energy_slices.png"
    _grid(total_panels, 3, total_path, "Constant-per-emitter unit-relative aggregate | log overlays")
    output_paths.append((total_path, "figure"))

    metric_panels: list[Image.Image] = []
    intracranial = full_masks["brain_total"]
    metric_specs = [
        ("ef_dom", "EF_dom", 1.0, False),
        ("non_dominant_contribution_fraction", "NCF", 0.0, False),
        ("n_eff", "N_eff", 1.0, False),
        ("ef_ref", "log10 EF_ref", 0.0, True),
    ]
    for key, title, low, use_log10 in metric_specs:
        values = np.asarray(metrics[key])
        if use_log10:
            values = np.where(values > 0, np.log10(values), np.nan)
        valid = values[intracranial & np.isfinite(values)]
        high = float(np.quantile(valid, 0.99))
        for axis, name in enumerate(("sagittal", "coronal", "axial")):
            metric_panels.append(
                _panel(
                    _scalar_image(
                        _extract_plane(labels, axis, centroid[axis]),
                        _extract_plane(values, axis, centroid[axis]),
                        low=low,
                        high=high,
                        mask=_extract_plane(intracranial, axis, centroid[axis]),
                    ),
                    f"{title} | {name} | p99={high:.3g}",
                )
            )
    metric_path = output_dir / "gray_white_matter_overlap_slices.png"
    _grid(metric_panels, 3, metric_path, "Overlap metrics in gray + white matter")
    output_paths.append((metric_path, "figure"))

    distributions_path = output_dir / "gray_white_matter_metric_distributions.png"
    _metric_distribution_image(
        {key: np.asarray(value) for key, value in metrics.items() if isinstance(value, np.ndarray)},
        masks,
        distributions_path,
        reference_id,
    )
    output_paths.append((distributions_path, "figure"))
    contributors_path = output_dir / "roi_top_contributors.png"
    _top_contributor_image(summary.source_ids, roi_integrals, contributors_path)
    output_paths.append((contributors_path, "figure"))

    source_rows: list[dict[str, Any]] = []
    for source_index, source_id in enumerate(summary.source_ids):
        gm = float(roi_integrals["gray_matter"][source_index])
        wm = float(roi_integrals["white_matter"][source_index])
        source_rows.append(
            {
                "emitter_id": source_id,
                "gray_matter_integrated_fluence": gm,
                "white_matter_integrated_fluence": wm,
                "brain_total_integrated_fluence": gm + wm,
                "gray_matter_integrated_absorbed_energy": gm * mua[2],
                "white_matter_integrated_absorbed_energy": wm * mua[3],
                "brain_total_integrated_absorbed_energy": gm * mua[2] + wm * mua[3],
            }
        )
    source_csv = output_dir / "source_roi_contributions.csv"
    _write_csv(source_csv, source_rows)
    output_paths.append((source_csv, "table"))

    tissue_csv = output_dir / "tissue_absorption.csv"
    _write_csv(tissue_csv, tissue_absorption)
    output_paths.append((tissue_csv, "table"))

    roi_results: dict[str, Any] = {}
    roi_rows: list[dict[str, Any]] = []
    for roi_name, mask in full_masks.items():
        field_first = _field_first(roi_integrals[roi_name], summary.source_ids, reference_id)
        metric_first = {
            key: _array_summary(np.asarray(metrics[key]), mask)
            for key in (
                "ef_dom",
                "non_dominant_contribution_fraction",
                "n_eff",
                "ef_ref",
            )
        }
        dominant_indices = summary.dominant_source_index[mask]
        counts = np.bincount(dominant_indices[dominant_indices >= 0], minlength=len(source_ids))
        top_voxel_dominators = np.argsort(counts)[::-1][:10]
        roi_results[roi_name] = {
            "voxel_count": int(np.count_nonzero(mask)),
            "field_first": field_first,
            "metric_first": metric_first,
            "top_dominant_by_voxel_count": [
                {
                    "rank": rank + 1,
                    "emitter_id": source_ids[index],
                    "voxel_count": int(counts[index]),
                    "fraction": float(counts[index] / np.count_nonzero(mask)),
                }
                for rank, index in enumerate(top_voxel_dominators)
            ],
        }
        for metric_name, values in metric_first.items():
            roi_rows.append({"roi": roi_name, "method": "metric_first", "metric": metric_name, **values})
        roi_rows.extend(
            {
                "roi": roi_name,
                "method": "field_first",
                "metric": key,
                "valid_voxel_count": "",
                "mean": value,
                "median": "",
                "p05": "",
                "p95": "",
            }
            for key, value in field_first.items()
            if key in {"ef_dom", "non_dominant_contribution_fraction", "n_eff", "ef_ref"}
        )
    roi_csv = output_dir / "roi_metric_summary.csv"
    _write_csv(roi_csv, roi_rows)
    output_paths.append((roi_csv, "table"))

    weighting_results = []
    gm_total = float(np.sum(roi_integrals["gray_matter"]))
    wm_total = float(np.sum(roi_integrals["white_matter"]))
    for weighting in analysis["source_weighting"]:
        scale = float(weighting["per_emitter_weight"])
        weighting_results.append(
            {
                **weighting,
                "gray_matter_integrated_fluence": gm_total * scale,
                "white_matter_integrated_fluence": wm_total * scale,
                "brain_total_integrated_fluence": (gm_total + wm_total) * scale,
                "gray_matter_integrated_absorbed_energy": gm_total * mua[2] * scale,
                "white_matter_integrated_absorbed_energy": wm_total * mua[3] * scale,
                "brain_total_integrated_absorbed_energy": (gm_total * mua[2] + wm_total * mua[3]) * scale,
            }
        )

    result = {
        "result_id": result_id,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "scientific_status": "provisional_yue_derived_spatial_surrogate_not_target_helmet_not_measured_dose_not_biological_efficacy",
        "source_count": len(source_ids),
        "aggregation": {
            "method": "one-source-at-a-time streaming sufficient statistics",
            "sum_dtype": "float64",
            "source_stack_materialized": False,
            "field_checksum_verified_before_use": True,
        },
        "units": {
            "fluence": "MCX normalized fluence (mm^-2 per unit launched energy under each declared relative weighting)",
            "absorbed_energy_density": "fluence times mua (mm^-3 per unit launched energy under each declared relative weighting)",
            "integrated_fluence": "MCX normalized fluence times mm^3 voxel volume",
            "integrated_absorbed_energy": "relative absorbed energy per unit launched energy",
            "interpretation": "Modeled relative transport quantities; not measured dose.",
        },
        "ratio_absolute_threshold": analysis["ratio_absolute_threshold"],
        "reference_protocol": analysis["reference_protocol"],
        "representative_visual_qc": regional_emitters,
        "weighting_results": weighting_results,
        "tissue_absorption": tissue_absorption,
        "total_absorbed_fraction_constant_total": float(
            sum(row["absorbed_fraction_constant_total"] for row in tissue_absorption)
        ),
        "roi_results": roi_results,
    }
    result_path = output_dir / "result_summary.json"
    _write_json(result_path, result)
    output_paths.append((result_path, "summary"))

    qc_path = output_dir / "analysis_qc.md"
    qc_path.write_text(
        f"# Surrogate {wavelength_nm}-nm Windows basis analysis QC\n\n"
        "Status: **complete**. All 277 manifest-recorded native fluence fields were checksum-verified before streaming.\n\n"
        "The aggregator held one source field at a time and retained only float64 sufficient statistics, ROI integrals, and the documented reference field. Five convergence-region source overlays, aggregate fluence/absorbed-energy slices, intracranial overlap slices, distributions, and ROI contributor bars were generated.\n\n"
        "Scientific boundary: this is a provisional Yue-derived spatial surrogate. It is not target-helmet geometry or radiometry, measured intracranial dose, thermal modeling, or evidence of biological efficacy.\n",
        encoding="utf-8",
    )
    output_paths.append((qc_path, "report"))

    script_path = Path(__file__).resolve()
    code_record = capture_code(root, entrypoint or script_path, sys.argv[1:], shared=(script_path,))
    code_record["analysis_settings"] = {key: value.as_posix() if isinstance(value, Path) else value for key, value in settings.items()}
    code_record["analysis_settings"]["output_dir"] = output_dir.relative_to(root).as_posix()
    inputs = [
        (index_path, "basis_index"),
        (inventory_path, "post_run_inventory"),
        (analysis_path, "analysis_configuration"),
        (anatomy_metadata_path, "anatomy_metadata"),
        (Path(anatomy_metadata["volume_representation"]), "anatomy_volume"),
        (optical_path, "optical_properties"),
        (geometry_path, "emitter_geometry"),
        (convergence_protocol_path, "convergence_protocol"),
    ]
    manifest = {
        "manifest_id": manifest_id,
        "created_at": result["created_at"],
        "scientific_status": result["scientific_status"],
        "code": {
            "path": script_path.relative_to(root).as_posix(),
            "sha256": sha256_file(script_path),
        },
        "provenance": code_record,
        "inputs": [
            {
                "kind": kind,
                "path": path.as_posix(),
                "sha256": sha256_file(root / path),
            }
            for path, kind in inputs
        ],
        "outputs": [_output_record(root, path, kind) for path, kind in output_paths],
    }
    _write_json(output_dir / "result_manifest.json", manifest)
    print(json.dumps({"status": "complete", "output_dir": str(output_dir)}, indent=2))


if __name__ == "__main__":
    main()
