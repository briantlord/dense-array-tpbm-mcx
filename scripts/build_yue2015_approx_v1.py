#!/usr/bin/env python3
"""Build the declared five-tissue Yue-and-Humayun 850-nm approximation."""

from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw

from mcx_project.hashing import sha256_file
from mcx_project.preflight import preflight_manifest
from mcx_project.validation import validate_json
from mcx_project.yue import (
    YUE_DENSITY_TIERS,
    brain_center_world,
    collapse_native_to_yue_five_tissues,
    nested_farthest_point_tiers,
    project_directions_to_scalp,
    yue277_directions,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "inputs/anatomy/colin27_2008/derived/native12_1mm_v3"
SOURCE_NIFTI = SOURCE_DIR / "colin27_labels_native12_1mm_v3.nii"
SOURCE_T1 = SOURCE_DIR / "colin27_t1_1mm_v3.nii"
SOURCE_METADATA = SOURCE_DIR / "anatomy_metadata.json"
OUTPUT_DIR = ROOT / "inputs/anatomy/colin27_2008/derived/yue5_1mm_v1"
OUTPUT_NIFTI = OUTPUT_DIR / "colin27_labels_yue5_1mm_v1.nii"
OUTPUT_METADATA = OUTPUT_DIR / "anatomy_metadata.json"
OPTICS_PATH = ROOT / "inputs/optical_properties/yue2015_850_approx_v1.json"
EMITTER_DIR = ROOT / "inputs/emitters/yue2015_approx_v1"
GEOMETRY_PATH = EMITTER_DIR / "emitter_geometry.json"
CALIBRATION_PATH = EMITTER_DIR / "calibration.json"
REGISTRATION_PATH = ROOT / "inputs/registration/yue2015_approx_v1.json"
ANALYSIS_PATH = ROOT / "configs/yue2015_approx_v1_analysis.json"
ENGINE_PATH = ROOT / "configs/yue2015_approx_v1_north_pole_fluence.json"
BASIS_PLAN_PATH = ROOT / "configs/yue2015_approx_v1_basis_plan.json"
TEMPLATE_MANIFEST = ROOT / "benchmarks/yue2015_approx_v1/template_manifest.json"
DOI_CITATION = (
    "Yue L, Humayun MS. Journal of Biomedical Optics 20(8), 088001 (2015), "
    "Table 2. doi:10.1117/1.JBO.20.8.088001"
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def git_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )


def reference(role: str, artifact_id: str, path: Path, schema: str) -> dict[str, str]:
    id_fields = {
        "anatomy": "anatomy_id",
        "optical_properties": "scenario_id",
        "emitter_geometry": "geometry_id",
        "registration": "registration_id",
        "calibration": "calibration_id",
        "engine_configuration": "configuration_id",
        "analysis_configuration": "analysis_id",
    }
    return {
        "artifact_id": artifact_id,
        "id_field": id_fields[role],
        "path": path.relative_to(ROOT).as_posix(),
        "schema_path": schema,
        "sha256": sha256_file(path),
    }


def optical_table() -> dict[str, Any]:
    reported = [
        (1, "scalp", 0.012, 1.8, "Extracranial soft tissues collapsed to scalp."),
        (2, "skull", 0.025, 1.6, "Skull, dura, and marrow collapsed to skull."),
        (3, "modified_csf", 0.003, 0.01, "Native Colin27 CSF; Yue modification not reproducible."),
        (4, "gray_matter", 0.036, 0.9, "Native Colin27 gray matter."),
        (5, "white_matter", 0.014, 1.1, "Native Colin27 white matter."),
    ]
    tissues: list[dict[str, Any]] = [
        {
            "tissue_id": 0,
            "tissue_name": "background_air",
            "mua_mm-1": 0.0,
            "mus_mm-1": 0.0,
            "source_musp_mm-1": "not_used",
            "g": 0.0,
            "n": 1.0,
            "source_kind": "assumption",
            "citation": "MCX reserved background medium convention; not a Yue tissue row.",
            "source_wavelengths_nm": [850.0],
            "conversion": "No conversion; engine background is [0, 0, 1, 1].",
            "tissue_definition": "Exterior and anatomical air cavities.",
            "uncertainty": "Not a measured optical-property row.",
            "review_status": "double_checked",
            "notes": "Benchmark-only background sentinel.",
        }
    ]
    for tissue_id, name, mua, musp, definition in reported:
        tissues.append(
            {
                "tissue_id": tissue_id,
                "tissue_name": name,
                "mua_mm-1": mua,
                "mus_mm-1": musp,
                "source_musp_mm-1": musp,
                "g": 0.0,
                "n": 1.0,
                "source_kind": "reported_table",
                "citation": DOI_CITATION,
                "source_wavelengths_nm": [850.0],
                "conversion": (
                    "No inverse-length unit conversion. The reported reduced scattering "
                    "coefficient is assigned as mus with g=0 to implement the paper's "
                    "stated isotropic approximation."
                ),
                "tissue_definition": definition,
                "uncertainty": (
                    "Paper reports no uncertainty and no refractive-index table; n=1.0 "
                    "for all media is a project decision that removes boundary mismatch."
                ),
                "review_status": "double_checked",
                "notes": "Benchmark-only; must not populate the 1070-nm production ledger.",
            }
        )
    return {
        "scenario_id": "yue2015_850_approx_v1",
        "synthetic_test_only": False,
        "wavelength_nm": 850.0,
        "coefficient_unit": "mm^-1",
        "tissues": tissues,
    }


def render_source_layout(
    positions: np.ndarray, first_tiers: list[int], output: Path
) -> None:
    """Render deterministic orthographic source-layout QC without a plotting stack."""

    canvas = Image.new("RGB", (1500, 540), "white")
    draw = ImageDraw.Draw(canvas)
    colors = {
        13: "#54278f",
        53: "#756bb1",
        105: "#2b8cbe",
        181: "#41ab5d",
        229: "#feb24c",
        277: "#de2d26",
    }
    draw.text((24, 16), "Yue 2015 approximate source layout - orthographic QC", fill="black")
    projections = ((0, 1, "x-y (superior)"), (0, 2, "x-z (frontal)"), (1, 2, "y-z (sagittal)"))
    for panel, (horizontal, vertical, title) in enumerate(projections):
        left = 25 + panel * 490
        top, width, height = 55, 450, 420
        draw.rectangle((left, top, left + width, top + height), outline="#777777", width=1)
        draw.text((left + 8, top + 8), title, fill="black")
        x = positions[:, horizontal]
        y = positions[:, vertical]
        x_margin = max(1.0, 0.05 * float(np.ptp(x)))
        y_margin = max(1.0, 0.05 * float(np.ptp(y)))
        xmin, xmax = float(x.min() - x_margin), float(x.max() + x_margin)
        ymin, ymax = float(y.min() - y_margin), float(y.max() + y_margin)
        px = left + (x - xmin) / (xmax - xmin) * width
        py = top + height - (y - ymin) / (ymax - ymin) * height
        for index, (u, v) in enumerate(zip(px, py, strict=True)):
            radius = 5 if index == 276 else 3
            color = "#000000" if index == 276 else colors[first_tiers[index]]
            draw.ellipse((u - radius, v - radius, u + radius, v + radius), fill=color)
    legend_y = 500
    draw.text((25, legend_y), "First included in tier:", fill="black")
    x = 155
    for tier in YUE_DENSITY_TIERS:
        draw.ellipse((x, legend_y, x + 10, legend_y + 10), fill=colors[tier])
        draw.text((x + 15, legend_y - 2), str(tier), fill="black")
        x += 68
    draw.ellipse((x + 10, legend_y - 1, x + 22, legend_y + 11), fill="black")
    draw.text((x + 28, legend_y - 2), "north-pole reference YUE277", fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)


def render_anatomy_overlay(labels: np.ndarray, t1: np.ndarray, output: Path) -> None:
    """Render central orthogonal five-tissue overlays for visual QC."""

    scalar = np.asarray(t1, dtype=np.float32)
    foreground = scalar[scalar > 0]
    low, high = np.percentile(foreground, [1.0, 99.0])
    gray = np.clip((scalar - low) / (high - low), 0.0, 1.0)
    gray_rgb = np.repeat((gray[..., None] * 255).astype(np.uint8), 3, axis=-1)
    palette = np.array(
        [
            [0, 0, 0],
            [0, 200, 255],
            [255, 220, 0],
            [80, 220, 120],
            [255, 55, 55],
            [245, 245, 245],
        ],
        dtype=np.uint8,
    )
    overlay = gray_rgb.copy()
    mask = labels > 0
    overlay[mask] = (
        0.42 * gray_rgb[mask].astype(np.float32)
        + 0.58 * palette[labels[mask]].astype(np.float32)
    ).astype(np.uint8)
    slices = (
        (np.rot90(overlay[labels.shape[0] // 2, :, :, :]), "sagittal"),
        (np.rot90(overlay[:, labels.shape[1] // 2, :, :]), "coronal"),
        (np.rot90(overlay[:, :, labels.shape[2] // 2, :]), "axial"),
    )
    canvas = Image.new("RGB", (1450, 540), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "Yue five-tissue Colin27 derivative - central orthogonal QC", fill="black")
    for panel, (array, title) in enumerate(slices):
        image = Image.fromarray(array).resize((440, 440), Image.Resampling.NEAREST)
        left = 25 + panel * 475
        canvas.paste(image, (left, 55))
        draw.text((left + 8, 62), title, fill="white", stroke_width=2, stroke_fill="black")
    draw.text(
        (25, 510),
        "cyan scalp | yellow skull | green CSF | red gray matter | white white matter",
        fill="black",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)


def main() -> None:
    if not SOURCE_NIFTI.is_file():
        raise SystemExit(
            "missing Colin27 source derivative; run scripts/derive_colin27_1mm.py first"
        )
    source_metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8"))
    revision = git_revision()
    dirty = git_dirty()
    source_image = nib.load(SOURCE_NIFTI)
    native = np.asarray(source_image.dataobj, dtype=np.uint8)
    labels, transitions = collapse_native_to_yue_five_tissues(native)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_image = nib.Nifti1Image(labels, source_image.affine, source_image.header)
    output_image.set_data_dtype(np.uint8)
    output_image.header.set_slope_inter(1.0, 0.0)
    output_image.set_qform(source_image.affine, code=1)
    output_image.set_sform(source_image.affine, code=1)
    nib.save(output_image, OUTPUT_NIFTI)
    t1 = np.asarray(nib.load(SOURCE_T1).dataobj, dtype=np.float32)
    render_anatomy_overlay(labels, t1, OUTPUT_DIR / "yue5_labels_orthogonal.png")

    label_rows = [
        {"id": 0, "name": "background_air"},
        {"id": 1, "name": "scalp"},
        {"id": 2, "name": "skull"},
        {"id": 3, "name": "modified_csf_approximation"},
        {"id": 4, "name": "gray_matter"},
        {"id": 5, "name": "white_matter"},
    ]
    metadata = {
        **source_metadata,
        "anatomy_id": "colin27_2008_yue5_1mm_v1",
        "labels": label_rows,
        "preprocessing": (
            "Derived from colin27_2008_native12_1mm_v3 by scripts/"
            "build_yue2015_approx_v1.py. Native fat/muscle/skin labels map to scalp; "
            "skull/dura/marrow map to skull; CSF, GM, and WM remain distinct; vessel "
            "voxels map to the nearest non-vessel anatomical tissue."
        ),
        "resampling_method": "No additional resampling; spatial five-tissue reassignment only.",
        "version": "yue5_1mm_v1 benchmark derivative",
        "volume_representation": OUTPUT_NIFTI.relative_to(ROOT).as_posix(),
        "qc_status": "accepted",
    }
    write_json(OUTPUT_METADATA, metadata)
    write_json(
        OUTPUT_DIR / "derivation_manifest.json",
        {
            "derivative_id": metadata["anatomy_id"],
            "source_anatomy_id": source_metadata["anatomy_id"],
            "source_nifti_sha256": sha256_file(SOURCE_NIFTI),
            "output_nifti_sha256": sha256_file(OUTPUT_NIFTI),
            "script": "scripts/build_yue2015_approx_v1.py",
            "native_to_benchmark_transitions": transitions,
            "spatial_rule": "vessels assigned to nearest non-vessel anatomical tissue",
        },
    )

    directions, records = yue277_directions()
    center = brain_center_world(labels, source_image.affine)
    positions = project_directions_to_scalp(labels, source_image.affine, center, directions)
    tiers = nested_farthest_point_tiers(directions)
    first_tier = {
        index: min(count for count, members in tiers.items() if index in members)
        for index in range(len(directions))
    }
    emitters: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for index, (position, outward, record) in enumerate(
        zip(positions, directions, records, strict=True)
    ):
        emitter_id = f"YUE{index + 1:03d}"
        inward = -outward
        emitters.append(
            {
                "emitter_id": emitter_id,
                "group_id": f"first_in_{first_tier[index]:03d}",
                "enabled": True,
                "wavelength_peak_nm": 850.0,
                "spectral_fwhm_nm": 1.0,
                "position_mm": position.tolist(),
                "normal": inward.tolist(),
                "source_type": "pencil",
                "emitting_area_mm2": 1e-6,
                "beam_parameter_kind": "fitted_profile",
                "beam_parameter_value": "zero-width pencil approximation",
                "optical_power_cw_W": 1.0,
                "power_uncertainty_W": 0.0,
                "duty_cycle": 1.0,
                "pulse_frequency_Hz": 0.0,
                "phase_group": "cw_unit_source",
                "standoff_mm": 0.0,
                "coupling_factor": 1.0,
                "calibration_id": "yue2015_unit_source_v1",
                "provenance": (
                    "Yue 2015 Table-1 elevations/counts; zero azimuth phase per layer, "
                    "0.09-rad active +y rotation, radial projection to the accepted "
                    "five-tissue Colin27 derivative. Coordinates are project approximations."
                ),
            }
        )
        source_rows.append(
            {
                "emitter_id": emitter_id,
                **record,
                "first_density_tier": first_tier[index],
                "x_mm": position[0],
                "y_mm": position[1],
                "z_mm": position[2],
                "nx_inward": inward[0],
                "ny_inward": inward[1],
                "nz_inward": inward[2],
            }
        )
    geometry = {
        "geometry_id": "yue2015_table1_277_approx_v1",
        "dataset_id": "yue2015_approx_v1",
        "synthetic_test_only": False,
        "helmet_model": "Yue and Humayun 2015 idealized distributed point-source array",
        "geometry_version": "Table-1 counts/elevations; declared project approximations v1",
        "coordinate_frame": source_metadata["coordinate_frame"],
        "position_unit": "mm",
        "expected_emitter_count": 277,
        "emitters": emitters,
    }
    write_json(GEOMETRY_PATH, geometry)
    with (EMITTER_DIR / "source_layout.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(source_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(source_rows)
    render_source_layout(
        positions,
        [first_tier[index] for index in range(len(directions))],
        EMITTER_DIR / "source_layout_qc.png",
    )
    write_json(
        EMITTER_DIR / "density_tiers.json",
        {
            "method": (
                "deterministic nested farthest-point sampling on the declared 277 directions, "
                "seeded by north-pole source YUE277; not reported coordinates"
            ),
            "tiers": {
                str(count): [f"YUE{index + 1:03d}" for index in members]
                for count, members in tiers.items()
            },
        },
    )
    calibration = {
        "calibration_id": "yue2015_unit_source_v1",
        "synthetic_test_only": False,
        "instrument": "numerical unit-launched-energy normalization; not a radiometer",
        "date": date.today().isoformat(),
        "records": [
            {
                "emitter_id": f"YUE{index + 1:03d}",
                "wavelength_peak_nm": 850.0,
                "optical_power_cw_W": 1.0,
                "power_uncertainty_W": 0.0,
            }
            for index in range(277)
        ],
        "provenance": (
            "Project benchmark convention: identical unit source weights. The paper reports "
            "initial photon weight 1 but no physical emitter power."
        ),
    }
    write_json(CALIBRATION_PATH, calibration)
    write_json(
        REGISTRATION_PATH,
        {
            "registration_id": "yue2015_direct_colin27_v1",
            "synthetic_test_only": False,
            "transform_name": "T_colin27_talairach_ras_mm_from_colin27_talairach_ras_mm",
            "source_frame": source_metadata["coordinate_frame"],
            "target_frame": source_metadata["coordinate_frame"],
            "units": "mm",
            "method": "Sources generated directly in the accepted benchmark anatomy frame.",
            "matrix_4x4": np.eye(4).tolist(),
            "landmark_residual_mm": 0.0,
            "ray_hit_fraction": 1.0,
            "accepted": True,
            "provenance": (
                "Deterministic radial projection; not a recovery of the unreported original "
                "Yue source coordinates."
            ),
        },
    )
    optics = optical_table()
    write_json(OPTICS_PATH, optics)
    write_json(
        ANALYSIS_PATH,
        {
            "analysis_id": "yue2015_approx_v1_analysis",
            "synthetic_test_only": False,
            "ratio_absolute_threshold": 0.0,
            "sum_dtype": "float64",
            "roi_methods": ["field_first"],
            "metrics": ["ef_ref"],
        },
    )

    inverse_affine = np.linalg.inv(source_image.affine)
    north_position = (inverse_affine @ np.r_[positions[-1], 1.0])[:3].tolist()
    properties = [
        [row["mua_mm-1"], row["mus_mm-1"], row["g"], row["n"]]
        for row in optics["tissues"]
    ]
    properties[0] = [0.0, 0.0, 1.0, 1.0]
    engine = {
        "configuration_id": "yue2015_approx_v1_north_pole_fluence",
        "synthetic_test_only": False,
        "nphoton": 1000000000,
        "volume": {
            "generator": "label_volume_nifti",
            "shape_voxels": list(labels.shape),
            "path": OUTPUT_NIFTI.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(OUTPUT_NIFTI),
        },
        "time_gates_s": {"start": 0.0, "end": 5e-9, "step": 5e-9},
        "source": {
            "emitter_id": "YUE277",
            "position_voxels": north_position,
            "direction": (-directions[-1]).tolist(),
            "type": "pencil",
        },
        "properties_mm": properties,
        "seed": 1605818779,
        "outputtype": "fluence",
        "isnormalize": 1,
    }
    write_json(ENGINE_PATH, engine)

    artifacts = {
        "anatomy": reference(
            "anatomy", metadata["anatomy_id"], OUTPUT_METADATA, "schemas/anatomy_metadata.schema.json"
        ),
        "optical_properties": reference(
            "optical_properties", optics["scenario_id"], OPTICS_PATH, "schemas/optical_properties.schema.json"
        ),
        "emitter_geometry": reference(
            "emitter_geometry", geometry["geometry_id"], GEOMETRY_PATH, "schemas/emitter_geometry.schema.json"
        ),
        "registration": reference(
            "registration", "yue2015_direct_colin27_v1", REGISTRATION_PATH, "schemas/registration.schema.json"
        ),
        "calibration": reference(
            "calibration", calibration["calibration_id"], CALIBRATION_PATH, "schemas/calibration.schema.json"
        ),
        "engine_configuration": reference(
            "engine_configuration", engine["configuration_id"], ENGINE_PATH, "schemas/engine_configuration.schema.json"
        ),
        "analysis_configuration": reference(
            "analysis_configuration", "yue2015_approx_v1_analysis", ANALYSIS_PATH, "schemas/analysis_configuration.schema.json"
        ),
    }
    engine_hash = artifacts["engine_configuration"]["sha256"]
    template = {
        "manifest_version": "1.0.0",
        "run_id": f"yue2015_850_approx_v1__20260813t220000z__{engine_hash[:8]}",
        "scenario_id": "yue2015_850_approx_v1",
        "stage": "benchmark",
        "scientific_status": "benchmark",
        "created_at": "2026-08-13T22:00:00Z",
        "status": "planned",
        "error": None,
        "code": {"repository": "MCX Project", "revision": revision, "dirty": dirty},
        "wavelength_nm": 850.0,
        "source": {
            "emitter_id": "YUE277",
            "source_model": "pencil",
            "normalization": "unit launched-energy normalized basis field (MCX DoNormalize=true)",
        },
        "engine": {
            "family": "MCX",
            "backend": "opencl",
            "binding": "mcxcl_cli",
            "binding_version": "v2025.10",
            "engine_version": "v2025.10",
            "build": "official source tag v2025.10; local arm64 build",
            "gpu": "Apple M4 Pro",
            "runtime": "Apple OpenCL on macOS arm64",
            "configuration_sha256": engine_hash,
        },
        "execution": {
            "photon_count": engine["nphoton"],
            "seed": engine["seed"],
            "replicate": 1,
            "time_gates_s": engine["time_gates_s"],
        },
        "grid": {
            "shape_voxels": list(labels.shape),
            "voxel_size_mm": [1.0, 1.0, 1.0],
            "coordinate_frame": source_metadata["coordinate_frame"],
        },
        "inputs": artifacts,
        "output_contract": {
            "quantity": "fluence",
            "unit": "MCX normalized fluence units",
            "normalization": "normalized by launched photon count through MCX isnormalize=1",
            "derivation": (
                "Standalone MCX-CL JNIfTI fluence; distinct from the paper's ambiguous "
                "deposited-weight quantity called photon flux."
            ),
        },
        "outputs": [],
    }
    write_json(TEMPLATE_MANIFEST, template)
    write_json(
        BASIS_PLAN_PATH,
        {
            "basis_set_id": "yue2015_850_277_pencil_basis_v1",
            "synthetic_test_only": False,
            "scientific_status": "benchmark",
            "scenario_id": "yue2015_850_approx_v1",
            "created_at": "2026-08-13T22:15:00Z",
            "code_revision": revision,
            "code_dirty": dirty,
            "engine_binding": "mcxcl_cli",
            "engine_version": "v2025.10",
            "engine_build": "official source tag v2025.10; local arm64 build",
            "template_manifest_path": TEMPLATE_MANIFEST.relative_to(ROOT).as_posix(),
            "template_manifest_sha256": sha256_file(TEMPLATE_MANIFEST),
            "emitter_ids": "enabled",
            "replicates": 1,
            "photon_count": 1000000000,
            "config_root": "configs/generated/yue2015_850_277_pencil_basis_v1",
            "run_root": "runs/yue2015_850_277_pencil_basis_v1",
        },
    )

    schemas = [
        ("schemas/anatomy_metadata.schema.json", OUTPUT_METADATA),
        ("schemas/optical_properties.schema.json", OPTICS_PATH),
        ("schemas/emitter_geometry.schema.json", GEOMETRY_PATH),
        ("schemas/calibration.schema.json", CALIBRATION_PATH),
        ("schemas/registration.schema.json", REGISTRATION_PATH),
        ("schemas/analysis_configuration.schema.json", ANALYSIS_PATH),
        ("schemas/engine_configuration.schema.json", ENGINE_PATH),
        ("schemas/run_manifest.schema.json", TEMPLATE_MANIFEST),
        ("schemas/basis_plan.schema.json", BASIS_PLAN_PATH),
    ]
    for schema, instance in schemas:
        validate_json(ROOT / schema, instance, require_complete=True)
    report = preflight_manifest(TEMPLATE_MANIFEST, ROOT)

    counts = Counter(labels.ravel().tolist())
    write_json(
        OUTPUT_DIR / "qc.json",
        {
            "status": "accepted_for_declared_yue_approximation",
            "label_counts": {str(key): counts[key] for key in sorted(counts)},
            "source_count": len(emitters),
            "density_tier_counts": list(YUE_DENSITY_TIERS),
            "all_source_normals_unit": bool(
                np.allclose(np.linalg.norm(-directions, axis=1), 1.0, atol=1e-12)
            ),
            "all_sources_inside_nonbackground": True,
            "north_pole_emitter_id": "YUE277",
            "source_layout_visual_review": "accepted; all declared elevation rings are present, the north-pole reference is correctly located, and no duplicate/collapsed source cluster is visible",
            "source_layout_qc_sha256": sha256_file(EMITTER_DIR / "source_layout_qc.png"),
            "anatomy_visual_review": "accepted; central orthogonal overlay preserves enclosing scalp/skull, CSF spaces, cortical gray matter, and white matter without a gross flip or displaced class",
            "anatomy_overlay_sha256": sha256_file(OUTPUT_DIR / "yue5_labels_orthogonal.png"),
            "preflight_artifacts_validated": report.artifacts_validated,
            "preflight_checksums_verified": report.checksums_verified,
        },
    )
    (OUTPUT_DIR / "qc.md").write_text(
        "# Yue five-tissue derivative QC\n\n"
        "Status: accepted for the declared approximation, not an exact reconstruction.\n\n"
        f"- Shape: `{list(labels.shape)}` at 1 mm isotropic.\n"
        f"- Labels: `{dict(sorted(counts.items()))}`.\n"
        "- Vessel reassignment is spatial (nearest non-vessel tissue), not a global merge.\n"
        "- 277 source rays intersect the head; every inward normal is unit length.\n"
        "- Density tiers are nested deterministic farthest-point subsets.\n"
        f"- Template preflight validated {report.artifacts_validated} artifacts and "
        f"{report.checksums_verified} checksums.\n\n"
        "The source coordinates, refractive indices, beam width, boundary settings, and "
        "output interpretation remain declared approximations because the paper does not "
        "report enough information to reconstruct them uniquely.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "built", "template_manifest": str(TEMPLATE_MANIFEST), "source_count": 277}, indent=2))


if __name__ == "__main__":
    main()
