#!/usr/bin/env python3
"""Derive and QC the native-label 1-mm Colin27 project anatomy."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np
import scipy
from PIL import Image, ImageDraw
from scipy import ndimage

from mcx_project.anatomy import (
    block_center_affine,
    block_mean_downsample,
    block_mode_downsample,
    label_counts,
    rounded_discrete_labels,
)
from mcx_project.hashing import sha256_file


LABEL_NAMES = {
    0: "background_air",
    1: "cerebrospinal_fluid",
    2: "gray_matter",
    3: "white_matter",
    4: "fat",
    5: "muscles",
    6: "skin_and_muscles",
    7: "skull",
    9: "fat_2",
    10: "dura",
    11: "marrow",
    12: "vessels",
}
LABEL_COLORS = {
    0: (0, 0, 0),
    1: (145, 29, 125),
    2: (0, 255, 0),
    3: (0, 70, 255),
    4: (255, 230, 0),
    5: (0, 220, 220),
    6: (255, 0, 255),
    7: (255, 239, 213),
    9: (205, 133, 63),
    10: (0, 210, 38),
    11: (102, 205, 170),
    12: (255, 23, 0),
}
TIE_PRIORITY = [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 0]
ANATOMY_ID = "colin27_2008_native12_1mm_v3"
PROTECTED_LABELS = [1, 2, 3, 7, 10, 11, 12]
SOFT_TISSUE_ENVELOPE_MARGIN_MM = 15.0


def _write_nifti_immutable(image: nib.Nifti1Image, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="colin27-", dir=destination.parent) as tmp:
        temporary = Path(tmp) / destination.name
        nib.save(image, temporary)
        candidate_hash = sha256_file(temporary)
        if destination.exists():
            if sha256_file(destination) != candidate_hash:
                raise RuntimeError(f"refusing to replace changed artifact: {destination}")
        else:
            os.replace(temporary, destination)
    return candidate_hash


def _oriented_slice(volume: np.ndarray, axis: int, index: int) -> np.ndarray:
    plane = np.take(volume, index, axis=axis)
    return np.rot90(plane)


def _label_rgb(labels: np.ndarray) -> np.ndarray:
    rgb = np.zeros(labels.shape + (3,), dtype=np.uint8)
    for label, color in LABEL_COLORS.items():
        rgb[labels == label] = color
    return rgb


def _scaled_t1_rgb(values: np.ndarray, low: float, high: float) -> np.ndarray:
    scaled = np.clip((values - low) / (high - low), 0, 1)
    gray = np.rint(scaled * 255).astype(np.uint8)
    return np.repeat(gray[..., None], 3, axis=-1)


def _panel(image: np.ndarray, title: str, *, size: tuple[int, int] = (420, 420)) -> Image.Image:
    rendered = Image.fromarray(image).resize(size, Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (size[0], size[1] + 34), "white")
    canvas.paste(rendered, (0, 34))
    ImageDraw.Draw(canvas).text((8, 9), title, fill="black")
    return canvas


def _grid(panels: list[Image.Image], columns: int, destination: Path) -> None:
    rows = (len(panels) + columns - 1) // columns
    width = max(panel.width for panel in panels)
    height = max(panel.height for panel in panels)
    canvas = Image.new("RGB", (columns * width, rows * height), "white")
    for index, panel in enumerate(panels):
        canvas.paste(panel, ((index % columns) * width, (index // columns) * height))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def _render_orthogonal(
    labels: np.ndarray, t1: np.ndarray, affine: np.ndarray, destination: Path
) -> None:
    brain = np.isin(labels, [1, 2, 3])
    coordinates = np.argwhere(brain)
    center = np.rint((coordinates.min(axis=0) + coordinates.max(axis=0)) / 2).astype(int)
    nonzero_t1 = t1[t1 > 0]
    low, high = np.percentile(nonzero_t1, [1, 99])
    panels: list[Image.Image] = []
    names = ["Sagittal", "Coronal", "Axial"]
    for axis, name in enumerate(names):
        index = int(center[axis])
        label_slice = _oriented_slice(labels, axis, index)
        t1_slice = _oriented_slice(t1, axis, index)
        label_rgb = _label_rgb(label_slice)
        t1_rgb = _scaled_t1_rgb(t1_slice, float(low), float(high))
        mask = label_slice != 0
        overlay = t1_rgb.copy()
        overlay[mask] = np.rint(
            0.58 * t1_rgb[mask].astype(np.float32)
            + 0.42 * label_rgb[mask].astype(np.float32)
        ).astype(np.uint8)
        world = nib.affines.apply_affine(affine, center)
        title = f"{name}: voxel {index}; center world {world.round(1).tolist()} mm"
        panels.append(_panel(overlay, title))
    _grid(panels, 3, destination)


def _render_multislice(
    labels: np.ndarray, t1: np.ndarray, affine: np.ndarray, destination: Path
) -> None:
    brain_coordinates = np.argwhere(np.isin(labels, [1, 2, 3]))
    lower = brain_coordinates.min(axis=0)
    upper = brain_coordinates.max(axis=0)
    nonzero_t1 = t1[t1 > 0]
    low, high = np.percentile(nonzero_t1, [1, 99])
    panels: list[Image.Image] = []
    names = ["Sagittal", "Coronal", "Axial"]
    for axis, name in enumerate(names):
        indices = np.rint(
            lower[axis] + np.array([0.2, 0.4, 0.6, 0.8]) * (upper[axis] - lower[axis])
        ).astype(int)
        for index in indices:
            label_slice = _oriented_slice(labels, axis, int(index))
            t1_slice = _oriented_slice(t1, axis, int(index))
            label_rgb = _label_rgb(label_slice)
            t1_rgb = _scaled_t1_rgb(t1_slice, float(low), float(high))
            mask = label_slice != 0
            overlay = t1_rgb.copy()
            overlay[mask] = np.rint(
                0.58 * t1_rgb[mask].astype(np.float32)
                + 0.42 * label_rgb[mask].astype(np.float32)
            ).astype(np.uint8)
            voxel = np.rint((lower + upper) / 2).astype(int)
            voxel[axis] = index
            coordinate = nib.affines.apply_affine(affine, voxel)[axis]
            panels.append(
                _panel(
                    overlay,
                    f"{name}: voxel {int(index)}, axis coordinate {coordinate:.1f} mm",
                    size=(330, 330),
                )
            )
    _grid(panels, 4, destination)


def _first_hit_projection(
    labels: np.ndarray, axis: int, reverse: bool, selected_label: int | None
) -> np.ndarray:
    working = np.flip(labels, axis=axis) if reverse else labels
    mask = working != 0 if selected_label is None else working == selected_label
    valid = np.any(mask, axis=axis)
    depth = np.argmax(mask, axis=axis)
    gathered = np.take_along_axis(
        working, np.expand_dims(depth, axis=axis), axis=axis
    ).squeeze(axis=axis)
    gathered[~valid] = 0
    rgb = _label_rgb(gathered)
    if np.any(valid):
        shade = 0.55 + 0.45 * (1 - depth / max(working.shape[axis] - 1, 1))
        rgb = np.rint(rgb.astype(np.float32) * shade[..., None]).astype(np.uint8)
        rgb[~valid] = 255
    return np.rot90(rgb)


def _render_surfaces(labels: np.ndarray, destination: Path) -> None:
    views = [
        (0, False, "Left"),
        (0, True, "Right"),
        (1, False, "Posterior"),
        (1, True, "Anterior"),
        (2, False, "Inferior"),
        (2, True, "Superior"),
    ]
    panels: list[Image.Image] = []
    for selected_label, prefix in [(None, "Outer first-hit"), (2, "Gray-matter first-hit")]:
        for axis, reverse, name in views:
            projection = _first_hit_projection(labels, axis, reverse, selected_label)
            panels.append(_panel(projection, f"{prefix}: {name}", size=(340, 340)))
    _grid(panels, 3, destination)


def _component_statistics(labels: np.ndarray) -> dict[str, dict[str, float | int]]:
    structure = ndimage.generate_binary_structure(3, 1)
    statistics: dict[str, dict[str, float | int]] = {}
    for label in LABEL_NAMES:
        if label == 0:
            continue
        mask = labels == label
        components, count = ndimage.label(mask, structure=structure)
        sizes = np.bincount(components.ravel())[1:]
        largest = int(sizes.max()) if sizes.size else 0
        total = int(mask.sum())
        statistics[str(label)] = {
            "component_count_6_connected": int(count),
            "largest_component_fraction": largest / total if total else 0.0,
        }
    head = labels != 0
    components, count = ndimage.label(head, structure=structure)
    sizes = np.bincount(components.ravel())[1:]
    statistics["head_nonbackground"] = {
        "component_count_6_connected": int(count),
        "largest_component_fraction": float(sizes.max() / head.sum()),
    }
    return statistics


def _retain_main_head_component(labels: np.ndarray) -> tuple[np.ndarray, dict[int, int]]:
    """Remove only nonzero voxels disconnected from the largest head component."""
    structure = ndimage.generate_binary_structure(3, 1)
    components, count = ndimage.label(labels != 0, structure=structure)
    if count < 1:
        raise ValueError("derived label volume contains no head component")
    sizes = np.bincount(components.ravel())
    sizes[0] = 0
    main_component = int(np.argmax(sizes))
    removed_mask = (components != 0) & (components != main_component)
    removed = label_counts(labels[removed_mask]) if np.any(removed_mask) else {}
    cleaned = labels.copy()
    cleaned[removed_mask] = 0
    return cleaned, removed


def _apply_cranial_soft_tissue_envelope(
    labels: np.ndarray, *, margin_voxels: float
) -> tuple[np.ndarray, dict[int, int]]:
    """Remove soft-tissue voxels implausibly far from cranial/protected tissues."""
    protected = np.isin(labels, PROTECTED_LABELS)
    distance = ndimage.distance_transform_edt(~protected)
    removed_mask = (~protected) & (distance > margin_voxels) & (labels != 0)
    removed = label_counts(labels[removed_mask]) if np.any(removed_mask) else {}
    cleaned = labels.copy()
    cleaned[removed_mask] = 0
    return cleaned, removed


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    atlas_root = project_root / "inputs/anatomy/colin27_2008"
    source_manifest = json.loads((atlas_root / "source_manifest.json").read_text())
    source_labels_path = project_root / source_manifest["files"]["classification"]["path"]
    source_t1_path = project_root / source_manifest["files"]["t1"]["path"]
    if sha256_file(source_labels_path) != source_manifest["files"]["classification"]["sha256"]:
        raise RuntimeError("source classification checksum mismatch")
    if sha256_file(source_t1_path) != source_manifest["files"]["t1"]["sha256"]:
        raise RuntimeError("source T1 checksum mismatch")

    source_labels_image = nib.load(source_labels_path)
    source_t1_image = nib.load(source_t1_path)
    source_labels = rounded_discrete_labels(
        np.asanyarray(source_labels_image.dataobj), LABEL_NAMES
    )
    derived_labels, tie_counts = block_mode_downsample(
        source_labels, factor=2, tie_priority=TIE_PRIORITY
    )
    derived_labels, removed_envelope_counts = _apply_cranial_soft_tissue_envelope(
        derived_labels, margin_voxels=SOFT_TISSUE_ENVELOPE_MARGIN_MM
    )
    derived_labels, removed_island_counts = _retain_main_head_component(derived_labels)
    derived_t1 = block_mean_downsample(
        np.asanyarray(source_t1_image.dataobj), factor=2
    )
    derived_affine = block_center_affine(source_labels_image.affine, factor=2)

    derived_root = atlas_root / "derived/native12_1mm_v3"
    labels_path = derived_root / "colin27_labels_native12_1mm_v3.nii"
    t1_path = derived_root / "colin27_t1_1mm_v3.nii"
    labels_image = nib.Nifti1Image(derived_labels, derived_affine)
    labels_image.set_qform(derived_affine, code=1)
    labels_image.set_sform(derived_affine, code=1)
    t1_image = nib.Nifti1Image(derived_t1, derived_affine)
    t1_image.set_qform(derived_affine, code=1)
    t1_image.set_sform(derived_affine, code=1)
    label_hash = _write_nifti_immutable(labels_image, labels_path)
    t1_hash = _write_nifti_immutable(t1_image, t1_path)

    native_counts = label_counts(source_labels)
    derived_counts = label_counts(derived_labels)
    volume_rows = []
    for label, name in LABEL_NAMES.items():
        native_mm3 = native_counts[label] * 0.125
        derived_mm3 = float(derived_counts[label])
        change = (derived_mm3 - native_mm3) / native_mm3 if native_mm3 else 0.0
        volume_rows.append(
            {
                "label": label,
                "name": name,
                "native_voxels": native_counts[label],
                "native_volume_mm3": native_mm3,
                "derived_voxels": derived_counts[label],
                "derived_volume_mm3": derived_mm3,
                "relative_volume_change": change,
            }
        )
    qc_root = derived_root / "qc"
    qc_root.mkdir(parents=True, exist_ok=True)
    with (qc_root / "label_volumes.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(volume_rows[0]))
        writer.writeheader()
        writer.writerows(volume_rows)

    orthogonal_path = qc_root / "orthogonal_t1_labels.png"
    multislice_path = qc_root / "multislice_t1_labels.png"
    surfaces_path = qc_root / "surface_projections.png"
    _render_orthogonal(derived_labels, derived_t1, derived_affine, orthogonal_path)
    _render_multislice(derived_labels, derived_t1, derived_affine, multislice_path)
    _render_surfaces(derived_labels, surfaces_path)
    visual_artifacts = {
        "multislice_t1_labels.png": sha256_file(multislice_path),
        "orthogonal_t1_labels.png": sha256_file(orthogonal_path),
        "surface_projections.png": sha256_file(surfaces_path),
    }

    components = _component_statistics(derived_labels)
    head = derived_labels != 0
    enclosed_air = ndimage.binary_fill_holes(head) & ~head
    tied_voxels = int(np.count_nonzero(tie_counts > 1))
    csf_change = next(
        row["relative_volume_change"] for row in volume_rows if row["label"] == 1
    )
    automated_checks = {
        "all_native_labels_present": sorted(derived_counts) == sorted(LABEL_NAMES),
        "csf_volume_preserved_within_minus10_plus15_percent": -0.10 < csf_change < 0.15,
        "geometry_is_181x217x181_at_1mm": list(derived_labels.shape) == [181, 217, 181]
        and np.allclose(nib.affines.voxel_sizes(derived_affine), [1, 1, 1]),
        "head_is_one_6_connected_component": components["head_nonbackground"][
            "component_count_6_connected"
        ]
        == 1,
        "superior_volume_boundary_is_background": not bool(
            np.any(derived_labels[:, :, -1])
        ),
        "output_labels_are_uint8_without_scaling": derived_labels.dtype == np.uint8,
    }
    automated_status = "passed" if all(automated_checks.values()) else "failed"
    review_path = qc_root / "visual_review.json"
    visual_review_status = "pending"
    if review_path.exists():
        review = json.loads(review_path.read_text(encoding="utf-8"))
        if (
            review.get("status") == "accepted"
            and review.get("reviewed_artifacts") == visual_artifacts
        ):
            visual_review_status = "accepted"
    qc_payload = {
        "anatomy_id": ANATOMY_ID,
        "automated_checks": automated_checks,
        "automated_status": automated_status,
        "component_statistics": components,
        "enclosed_background_air_voxels": int(enclosed_air.sum()),
        "removed_disconnected_nonhead_voxels_by_original_label": {
            str(label): count for label, count in removed_island_counts.items()
        },
        "removed_outside_15mm_cranial_envelope_by_original_label": {
            str(label): count for label, count in removed_envelope_counts.items()
        },
        "resampling_tie_output_voxels": tied_voxels,
        "resampling_tie_output_fraction": tied_voxels / derived_labels.size,
        "visual_artifacts": visual_artifacts,
        "visual_review_status": visual_review_status,
    }
    (qc_root / "anatomy_qc.json").write_text(
        json.dumps(qc_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    relative_labels_path = labels_path.relative_to(project_root).as_posix()
    relative_t1_path = t1_path.relative_to(project_root).as_posix()
    anatomy_metadata = {
        "access_date": "2026-08-13",
        "affine": derived_affine.tolist(),
        "age_category": "adult; exact age not provided by source release",
        "anatomy_id": ANATOMY_ID,
        "coordinate_frame": "colin27_talairach_ras_mm",
        "final_voxel_size_mm": [1.0, 1.0, 1.0],
        "labels": [{"id": label, "name": name} for label, name in LABEL_NAMES.items()],
        "license": "MNI Colin27 license; see inputs/anatomy/colin27_2008/LICENSE.txt",
        "native_voxel_size_mm": [0.5, 0.5, 0.5],
        "orientation": "RAS; right-handed; affine maps voxel centers to millimeters",
        "preprocessing": (
            "scripts/derive_colin27_1mm.py; NIfTI-scaled class values rounded to nearest "
            "documented integer label, then 2x2x2 categorical block mode with declared "
            "tie priority [1,2,3,4,5,6,7,9,10,11,12,0]; soft tissues farther than "
            "15 mm from CSF/GM/WM/skull/dura/marrow/vessels set to background; remaining "
            "nonzero components disconnected from the largest head component set to "
            "background; no tissue-label merging"
        ),
        "qc_status": (
            "accepted"
            if automated_status == "passed" and visual_review_status == "accepted"
            else "pending"
        ),
        "resampling_method": (
            "2x2x2 block mode for labels; ties resolved by declared priority with "
            "background last; 2x2x2 block mean for reference T1"
        ),
        "shape_voxels": list(derived_labels.shape),
        "source_dataset": "MNI Colin27 high-resolution 2008 discrete phantom",
        "source_url_or_doi": source_manifest["source_url"],
        "subject_identity": (
            "average of repeated scans of one normal subject; identity, exact age, and sex "
            "not supplied in release metadata"
        ),
        "synthetic_test_only": False,
        "version": "native12_1mm_v3 derived from official 2008 NIfTI release",
        "volume_representation": relative_labels_path,
    }
    (derived_root / "anatomy_metadata.json").write_text(
        json.dumps(anatomy_metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable"
    derivation_manifest = {
        "anatomy_id": anatomy_metadata["anatomy_id"],
        "code_revision_before_uncommitted_derivation_changes": revision,
        "label_consolidation": "none",
        "removed_disconnected_nonhead_voxels_by_original_label": {
            str(label): count for label, count in removed_island_counts.items()
        },
        "removed_outside_15mm_cranial_envelope_by_original_label": {
            str(label): count for label, count in removed_envelope_counts.items()
        },
        "outputs": {
            "labels": {"path": relative_labels_path, "sha256": label_hash},
            "reference_t1": {"path": relative_t1_path, "sha256": t1_hash},
            "visual_qc": visual_artifacts,
        },
        "software": {
            "nibabel": nib.__version__,
            "numpy": np.__version__,
            "pillow": Image.__version__,
            "scipy": scipy.__version__,
        },
        "source_classification_sha256": source_manifest["files"]["classification"]["sha256"],
        "source_t1_sha256": source_manifest["files"]["t1"]["sha256"],
        "supersedes_rejected_derivation": (
            "native12_1mm_v2; rejected after surface QC revealed a connected soft-tissue "
            "wraparound/field-of-view artifact superior to the cranial tissues"
        ),
        "tie_priority": TIE_PRIORITY,
    }
    (derived_root / "derivation_manifest.json").write_text(
        json.dumps(derivation_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report_lines = [
        "# Colin27 native-label 1-mm anatomy QC",
        "",
        f"- Anatomy ID: `{anatomy_metadata['anatomy_id']}`",
        f"- Automated status: **{automated_status}**",
        f"- Visual review: **{visual_review_status}**",
        f"- Output geometry: `{list(derived_labels.shape)}` at 1-mm isotropic, RAS",
        f"- Label output SHA-256: `{label_hash}`",
        f"- Reference T1 SHA-256: `{t1_hash}`",
        f"- Tied block-mode voxels: `{tied_voxels}` ({tied_voxels / derived_labels.size:.4%})",
        f"- Enclosed background/air voxels: `{int(enclosed_air.sum())}`; these include anatomical air cavities and require visual interpretation, not automatic filling.",
        f"- Removed disconnected non-head voxels: `{sum(removed_island_counts.values())}`; transitions by original label are recorded in `anatomy_qc.json`.",
        f"- Removed outside the 15-mm cranial soft-tissue envelope: `{sum(removed_envelope_counts.values())}` voxels; transitions by original label are recorded in `anatomy_qc.json`.",
        "",
        "## Tissue volumes",
        "",
        "| Label | Tissue | Native mm3 | Derived mm3 | Relative change |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in volume_rows:
        report_lines.append(
            f"| {row['label']} | {row['name']} | {row['native_volume_mm3']:.1f} | "
            f"{row['derived_volume_mm3']:.1f} | {row['relative_volume_change']:.3%} |"
        )
    report_lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "Automated structural checks do not validate optical properties, source registration, cortical ROIs, or clinical dosimetry. The native labels were intentionally not merged. A five-tissue benchmark map, if required, must be a separate versioned derivative.",
            "",
        ]
    )
    (qc_root / "anatomy_qc.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(json.dumps(qc_payload, indent=2, sort_keys=True))
    return 0 if automated_status == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
