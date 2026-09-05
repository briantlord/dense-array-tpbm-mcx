"""Build a non-production Colin27 pilot scaffold for provisional 1070-nm runs."""

from __future__ import annotations

import copy
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np

from .basis import deterministic_seed
from .hashing import sha256_file
from .preflight import preflight_manifest
from .validation import InputValidationError, load_json, validate_json


PILOT_ID = "provisional_1070_representative_pilot_v1"
CREATED_AT = "2026-08-14T00:00:00Z"
CODE_REVISION = "39d58f606315707a7b8a4b4a672c0b9ff22a17c7"

DONOR_GEOMETRY_PATH = Path("inputs/emitters/yue2015_approx_v1/emitter_geometry.json")
ANATOMY_PATH = Path(
    "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/anatomy_metadata.json"
)
OPTICAL_PATH = Path("inputs/optical_properties/provisional_1070_v1/central.json")

OUTPUT_GEOMETRY_PATH = Path(
    "inputs/emitters/provisional_1070_layout_v1/emitter_geometry.json"
)
OUTPUT_CALIBRATION_PATH = Path(
    "inputs/emitters/provisional_1070_layout_v1/calibration.json"
)
OUTPUT_REGISTRATION_PATH = Path("inputs/registration/provisional_1070_layout_v1.json")
OUTPUT_ANALYSIS_PATH = Path("configs/provisional_1070_pilot_analysis_v1.json")
OUTPUT_ENGINE_PATH = Path("configs/provisional_1070_pilot_engine_template_v1.json")
OUTPUT_TEMPLATE_PATH = Path(f"runs/{PILOT_ID}/template_manifest.json")
OUTPUT_PLAN_PATH = Path("configs/provisional_1070_pilot_basis_plan_v1.json")

PHOTON_COUNT = 100_000
REGION_SPECS = (
    ("superior", 2, "max", "P1070_SUPERIOR"),
    ("anterior", 1, "max", "P1070_ANTERIOR"),
    ("posterior", 1, "min", "P1070_POSTERIOR"),
    ("left_temporal", 0, "min", "P1070_LEFT_TEMPORAL"),
    ("right_temporal", 0, "max", "P1070_RIGHT_TEMPORAL"),
)


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _payload_sha(value: Any) -> str:
    return sha256(_json_text(value).encode("utf-8")).hexdigest()


def select_representative_emitters(
    donor_geometry: dict[str, Any],
) -> list[tuple[str, str, dict[str, Any]]]:
    """Select stable frontal, occipital, bilateral temporal, and superior donors."""

    emitters = [row for row in donor_geometry["emitters"] if row["enabled"]]
    selected: list[tuple[str, str, dict[str, Any]]] = []
    donor_ids: set[str] = set()
    for region, axis, operation, output_id in REGION_SPECS:
        key = lambda row: (float(row["position_mm"][axis]), row["emitter_id"])
        donor = (max if operation == "max" else min)(emitters, key=key)
        if donor["emitter_id"] in donor_ids:
            raise InputValidationError(
                "representative-region extrema selected the same donor more than once"
            )
        donor_ids.add(donor["emitter_id"])
        selected.append((region, output_id, donor))
    return selected


def _representative_geometry(
    donor_geometry: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    emitters: list[dict[str, Any]] = []
    selection: list[dict[str, str]] = []
    for region, output_id, donor in select_representative_emitters(donor_geometry):
        row = copy.deepcopy(donor)
        row.update(
            {
                "beam_parameter_value": (
                    "zero-width pencil software scaffold; target 1070-nm beam "
                    "profile has not been supplied"
                ),
                "calibration_id": "provisional_1070_unit_source_v1",
                "emitter_id": output_id,
                "group_id": f"representative_{region}",
                "phase_group": "cw_unit_basis",
                "provenance": (
                    f"Software-only spatial donor {donor['emitter_id']} from "
                    "yue2015_table1_277_approx_v1, selected by a deterministic "
                    f"{region} coordinate extremum. Position and inward normal are "
                    "retained only to exercise Colin27 transport. This is not target "
                    "helmet geometry, hardware registration, or radiometry."
                ),
                "wavelength_peak_nm": 1070.0,
            }
        )
        emitters.append(row)
        selection.append(
            {
                "donor_emitter_id": donor["emitter_id"],
                "pilot_emitter_id": output_id,
                "region": region,
            }
        )
    return (
        {
            "coordinate_frame": donor_geometry["coordinate_frame"],
            "dataset_id": "provisional_1070_layout_v1",
            "emitters": emitters,
            "expected_emitter_count": len(emitters),
            "geometry_id": "provisional_1070_representative_layout_v1",
            "geometry_version": "v1",
            "helmet_model": (
                "software-only representative Colin27 scaffold; target helmet unknown"
            ),
            "position_unit": "mm",
            "synthetic_test_only": False,
        },
        selection,
    )


def _calibration(geometry: dict[str, Any]) -> dict[str, Any]:
    return {
        "calibration_id": "provisional_1070_unit_source_v1",
        "date": "2026-08-14",
        "instrument": "numerical unit-launched-energy normalization; not a radiometer",
        "provenance": (
            "Software-pilot convention only: every representative emitter has unit "
            "weight so normalized basis fields can be tested. No physical optical "
            "power, spectrum, uncertainty, duty cycle, or coupling has been measured."
        ),
        "records": [
            {
                "emitter_id": emitter["emitter_id"],
                "optical_power_cw_W": emitter["optical_power_cw_W"],
                "power_uncertainty_W": emitter["power_uncertainty_W"],
                "wavelength_peak_nm": emitter["wavelength_peak_nm"],
            }
            for emitter in geometry["emitters"]
        ],
        "synthetic_test_only": False,
    }


def _registration(coordinate_frame: str) -> dict[str, Any]:
    return {
        "accepted": True,
        "landmark_residual_mm": 0.0,
        "matrix_4x4": np.eye(4, dtype=float).tolist(),
        "method": (
            "Identity transform because the software-only donor coordinates were "
            "already generated directly in the accepted Colin27 frame."
        ),
        "provenance": (
            "Accepted only for this numerical scaffold. It does not register, fit, "
            "or validate the target 1070-nm helmet and must not cross the hardware gate."
        ),
        "ray_hit_fraction": 1.0,
        "registration_id": "provisional_1070_direct_colin27_v1",
        "source_frame": coordinate_frame,
        "synthetic_test_only": False,
        "target_frame": coordinate_frame,
        "transform_name": (
            "T_colin27_talairach_ras_mm_from_colin27_talairach_ras_mm"
        ),
        "units": "mm",
    }


def _engine_properties(optical: dict[str, Any]) -> list[list[float]]:
    """Render MCX media rows by label index, including gaps in sparse atlases."""

    maximum = max(int(row["tissue_id"]) for row in optical["tissues"])
    properties = [[0.0, 0.0, 1.0, 1.0] for _ in range(maximum + 1)]
    for row in optical["tissues"]:
        tissue_id = int(row["tissue_id"])
        if tissue_id == 0:
            continue
        properties[tissue_id] = [
            float(row["mua_mm-1"]),
            float(row["mus_mm-1"]),
            float(row["g"]),
            float(row["n"]),
        ]
    return properties


def _source_in_voxels(
    emitter: dict[str, Any], anatomy: dict[str, Any]
) -> tuple[list[float], list[float]]:
    affine = np.asarray(anatomy["affine"], dtype=np.float64)
    world = np.asarray([*emitter["position_mm"], 1.0], dtype=np.float64)
    position = (np.linalg.inv(affine) @ world)[:3]
    direction = np.asarray(emitter["normal"], dtype=np.float64)
    direction /= np.linalg.norm(direction)
    return position.tolist(), direction.tolist()


def _reference(
    role: str,
    artifact_id: str,
    path: Path,
    digest: str,
) -> dict[str, str]:
    fields = {
        "anatomy": ("anatomy_id", "schemas/anatomy_metadata.schema.json"),
        "optical_properties": (
            "scenario_id",
            "schemas/optical_properties.schema.json",
        ),
        "emitter_geometry": ("geometry_id", "schemas/emitter_geometry.schema.json"),
        "registration": ("registration_id", "schemas/registration.schema.json"),
        "calibration": ("calibration_id", "schemas/calibration.schema.json"),
        "engine_configuration": (
            "configuration_id",
            "schemas/engine_configuration.schema.json",
        ),
        "analysis_configuration": (
            "analysis_id",
            "schemas/analysis_configuration.schema.json",
        ),
    }
    id_field, schema_path = fields[role]
    return {
        "artifact_id": artifact_id,
        "id_field": id_field,
        "path": path.as_posix(),
        "schema_path": schema_path,
        "sha256": digest,
    }


def generate_provisional_pilot(project_root: Path) -> dict[Path, dict[str, Any]]:
    """Generate every small, versioned JSON artifact for the pilot scaffold."""

    root = project_root.resolve()
    donor = load_json(root / DONOR_GEOMETRY_PATH)
    anatomy = load_json(root / ANATOMY_PATH)
    optical = load_json(root / OPTICAL_PATH)
    if optical.get("scientific_status") != "provisional":
        raise InputValidationError("pilot requires a provisional optical scenario")
    if float(optical["wavelength_nm"]) != 1070.0:
        raise InputValidationError("pilot optical scenario must be exactly 1070 nm")

    geometry, selection = _representative_geometry(donor)
    calibration = _calibration(geometry)
    registration = _registration(geometry["coordinate_frame"])
    analysis = {
        "analysis_id": "provisional_1070_pilot_analysis_v1",
        "metrics": ["ef_dom", "ef_ref", "ncf", "n_eff"],
        "ratio_absolute_threshold": 1e-12,
        "roi_methods": ["field_first", "metric_first"],
        "sum_dtype": "float64",
        "synthetic_test_only": False,
    }

    superior = geometry["emitters"][0]
    source_position, source_direction = _source_in_voxels(superior, anatomy)
    volume_path = Path(anatomy["volume_representation"])
    volume_hash = sha256_file(root / volume_path)
    seed = deterministic_seed(PILOT_ID, superior["emitter_id"], 1)
    engine = {
        "configuration_id": "provisional_1070_pilot_engine_template_v1",
        "isnormalize": 1,
        "nphoton": PHOTON_COUNT,
        "outputtype": "fluence",
        "properties_mm": _engine_properties(optical),
        "seed": seed,
        "source": {
            "direction": source_direction,
            "emitter_id": superior["emitter_id"],
            "position_voxels": source_position,
            "type": superior["source_type"],
        },
        "synthetic_test_only": False,
        "time_gates_s": {"end": 5e-9, "start": 0.0, "step": 5e-9},
        "volume": {
            "generator": "label_volume_nifti",
            "path": volume_path.as_posix(),
            "sha256": volume_hash,
            "shape_voxels": anatomy["shape_voxels"],
        },
    }

    generated = {
        OUTPUT_GEOMETRY_PATH: geometry,
        OUTPUT_CALIBRATION_PATH: calibration,
        OUTPUT_REGISTRATION_PATH: registration,
        OUTPUT_ANALYSIS_PATH: analysis,
        OUTPUT_ENGINE_PATH: engine,
    }
    engine_hash = _payload_sha(engine)
    timestamp = CREATED_AT.replace("-", "").replace(":", "")
    timestamp = timestamp.replace("T", "t").replace("Z", "z")
    manifest = {
        "code": {
            "dirty": True,
            "repository": "MCX Project",
            "revision": CODE_REVISION,
        },
        "created_at": CREATED_AT,
        "engine": {
            "backend": "opencl",
            "binding": "mcxcl_cli",
            "binding_version": "v2025.10",
            "build": "official source tag v2025.10; local arm64 build",
            "configuration_sha256": engine_hash,
            "engine_version": "v2025.10",
            "family": "MCX",
            "gpu": "Apple M4 Pro",
            "runtime": "Apple OpenCL on macOS arm64",
        },
        "error": None,
        "execution": {
            "photon_count": PHOTON_COUNT,
            "replicate": 1,
            "seed": seed,
            "time_gates_s": engine["time_gates_s"],
        },
        "grid": {
            "coordinate_frame": anatomy["coordinate_frame"],
            "shape_voxels": anatomy["shape_voxels"],
            "voxel_size_mm": anatomy["final_voxel_size_mm"],
        },
        "inputs": {
            "analysis_configuration": _reference(
                "analysis_configuration",
                analysis["analysis_id"],
                OUTPUT_ANALYSIS_PATH,
                _payload_sha(analysis),
            ),
            "anatomy": _reference(
                "anatomy",
                anatomy["anatomy_id"],
                ANATOMY_PATH,
                sha256_file(root / ANATOMY_PATH),
            ),
            "calibration": _reference(
                "calibration",
                calibration["calibration_id"],
                OUTPUT_CALIBRATION_PATH,
                _payload_sha(calibration),
            ),
            "emitter_geometry": _reference(
                "emitter_geometry",
                geometry["geometry_id"],
                OUTPUT_GEOMETRY_PATH,
                _payload_sha(geometry),
            ),
            "engine_configuration": _reference(
                "engine_configuration",
                engine["configuration_id"],
                OUTPUT_ENGINE_PATH,
                engine_hash,
            ),
            "optical_properties": _reference(
                "optical_properties",
                optical["scenario_id"],
                OPTICAL_PATH,
                sha256_file(root / OPTICAL_PATH),
            ),
            "registration": _reference(
                "registration",
                registration["registration_id"],
                OUTPUT_REGISTRATION_PATH,
                _payload_sha(registration),
            ),
        },
        "manifest_version": "1.0.0",
        "output_contract": {
            "derivation": (
                "Standalone MCX-CL JNIfTI normalized field retained as a provisional "
                "software-pilot basis field; no device-dose interpretation."
            ),
            "normalization": "normalized by launched photon count through MCX isnormalize=1",
            "quantity": "fluence",
            "unit": "MCX normalized fluence units",
        },
        "outputs": [],
        "run_id": f"provisional_1070_v1__{timestamp}__{engine_hash[:8]}",
        "scenario_id": optical["scenario_id"],
        "scientific_status": "provisional",
        "source": {
            "emitter_id": superior["emitter_id"],
            "normalization": "unit launched-energy normalized basis field (MCX DoNormalize=true)",
            "source_model": superior["source_type"],
        },
        "stage": "pilot",
        "status": "planned",
        "wavelength_nm": 1070.0,
    }
    generated[OUTPUT_TEMPLATE_PATH] = manifest
    plan = {
        "basis_set_id": PILOT_ID,
        "code_dirty": True,
        "code_revision": CODE_REVISION,
        "config_root": f"configs/generated/{PILOT_ID}",
        "created_at": CREATED_AT,
        "emitter_ids": [row["pilot_emitter_id"] for row in selection],
        "engine_binding": "mcxcl_cli",
        "engine_build": "official source tag v2025.10; local arm64 build",
        "engine_version": "v2025.10",
        "photon_count": PHOTON_COUNT,
        "replicates": 1,
        "run_root": f"runs/{PILOT_ID}/prepared",
        "scenario_id": optical["scenario_id"],
        "scientific_status": "provisional",
        "synthetic_test_only": False,
        "template_manifest_path": OUTPUT_TEMPLATE_PATH.as_posix(),
        "template_manifest_sha256": _payload_sha(manifest),
    }
    generated[OUTPUT_PLAN_PATH] = plan
    return generated


def build_provisional_pilot(
    project_root: Path, *, check: bool = False
) -> dict[str, Any]:
    """Write or freshness-check the provisional representative pilot scaffold."""

    root = project_root.resolve()
    payloads = generate_provisional_pilot(root)
    stale: list[str] = []
    for relative, payload in payloads.items():
        path = root / relative
        expected = _json_text(payload)
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                stale.append(relative.as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    if stale:
        raise InputValidationError(
            "provisional pilot outputs are stale or missing:\n- "
            + "\n- ".join(stale)
        )

    schemas = {
        OUTPUT_GEOMETRY_PATH: "schemas/emitter_geometry.schema.json",
        OUTPUT_CALIBRATION_PATH: "schemas/calibration.schema.json",
        OUTPUT_REGISTRATION_PATH: "schemas/registration.schema.json",
        OUTPUT_ANALYSIS_PATH: "schemas/analysis_configuration.schema.json",
        OUTPUT_ENGINE_PATH: "schemas/engine_configuration.schema.json",
        OUTPUT_TEMPLATE_PATH: "schemas/run_manifest.schema.json",
        OUTPUT_PLAN_PATH: "schemas/basis_plan.schema.json",
    }
    for relative, schema in schemas.items():
        validate_json(root / schema, root / relative, require_complete=True)
    report = preflight_manifest(root / OUTPUT_TEMPLATE_PATH, root)
    return {
        "basis_set_id": PILOT_ID,
        "checksums_verified": report.checksums_verified,
        "emitters": 5,
        "mode": "check" if check else "write",
        "photon_count_per_emitter": PHOTON_COUNT,
        "production_eligible": False,
        "scientific_status": "provisional",
        "status": "valid",
        "template_manifest": OUTPUT_TEMPLATE_PATH.as_posix(),
    }
