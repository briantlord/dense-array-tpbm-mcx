"""Build a full 277-source Yue-derived 1070-nm surrogate scaffold."""

from __future__ import annotations

import copy
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .hashing import sha256_file
from .preflight import preflight_manifest
from .provisional_pilot import (
    _engine_properties,
    _reference,
    _registration,
    _source_in_voxels,
    select_representative_emitters,
)
from .validation import InputValidationError, load_json, validate_json


SURROGATE_ID = "surrogate_yue277_1070_v1"
BASIS_SET_ID = "surrogate_yue277_1070_basis_v1"
CREATED_AT = "2026-08-14T22:00:00Z"
CODE_REVISION = "32b12d6581ba82af39daa3b59528a1b17e977dca"
PHOTON_COUNT_CANDIDATE = 10_000_000

DONOR_GEOMETRY = Path("inputs/emitters/yue2015_approx_v1/emitter_geometry.json")
ANATOMY = Path(
    "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/anatomy_metadata.json"
)
OPTICAL = Path("inputs/optical_properties/provisional_1070_v1/central.json")
GEOMETRY = Path(f"inputs/emitters/{SURROGATE_ID}/emitter_geometry.json")
CALIBRATION = Path(f"inputs/emitters/{SURROGATE_ID}/calibration.json")
REGISTRATION = Path(f"inputs/registration/{SURROGATE_ID}.json")
ANALYSIS = Path(f"configs/{SURROGATE_ID}_analysis.json")
ENGINE = Path(f"configs/{SURROGATE_ID}_engine_template.json")
CONVERGENCE = Path(f"configs/{SURROGATE_ID}_regional_convergence.json")
CONVERGENCE_EXTENSION = Path(
    f"configs/{SURROGATE_ID}_regional_convergence_extension_v2.json"
)
TEMPLATE = Path(f"runs/{SURROGATE_ID}/template_manifest.json")
BASIS_PLAN = Path(f"configs/{BASIS_SET_ID}.json")
CONVERGENCE_RESULT = Path(
    "results/surrogate_yue277_1070_v1/regional_convergence_v2/results.json"
)
SELECTED_PHOTON_COUNT = 100_000_000


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _payload_sha(value: Any) -> str:
    return sha256(_json_text(value).encode("utf-8")).hexdigest()


def _surrogate_geometry(donor: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    emitters: list[dict[str, Any]] = []
    donor_to_surrogate: dict[str, str] = {}
    for index, source in enumerate(donor["emitters"], start=1):
        row = copy.deepcopy(source)
        emitter_id = f"SUR1070_{index:03d}"
        donor_to_surrogate[source["emitter_id"]] = emitter_id
        row.update(
            {
                "beam_parameter_value": (
                    "zero-width pencil Yue-spatial surrogate; target 1070-nm beam "
                    "profile has not been supplied"
                ),
                "calibration_id": "surrogate_yue277_1070_unit_source_v1",
                "emitter_id": emitter_id,
                "group_id": f"yue_surrogate_{source['group_id']}",
                "phase_group": "cw_unit_basis",
                "provenance": (
                    f"Position and inward normal copied from donor {source['emitter_id']} "
                    "in yue2015_table1_277_approx_v1. This is a Yue-derived spatial "
                    "surrogate for software and conditional overlap analysis, not target "
                    "helmet CAD, registration, beam geometry, or radiometry."
                ),
                "wavelength_peak_nm": 1070.0,
            }
        )
        emitters.append(row)
    return (
        {
            "coordinate_frame": donor["coordinate_frame"],
            "dataset_id": SURROGATE_ID,
            "emitters": emitters,
            "expected_emitter_count": 277,
            "geometry_id": SURROGATE_ID,
            "geometry_version": "v1",
            "helmet_model": (
                "Yue Table-1 277-source Colin27 spatial surrogate; target helmet unknown"
            ),
            "position_unit": "mm",
            "synthetic_test_only": False,
        },
        donor_to_surrogate,
    )


def _calibration(geometry: dict[str, Any]) -> dict[str, Any]:
    return {
        "calibration_id": "surrogate_yue277_1070_unit_source_v1",
        "date": "2026-08-14",
        "instrument": "numerical unit-launched-energy convention; not a radiometer",
        "provenance": (
            "Every source is assigned unit relative weight solely to create normalized "
            "basis fields. No target-device optical power, spectrum, duty cycle, beam, "
            "coupling, or uncertainty is represented."
        ),
        "records": [
            {
                "emitter_id": row["emitter_id"],
                "optical_power_cw_W": 1.0,
                "power_uncertainty_W": 0.0,
                "wavelength_peak_nm": 1070.0,
            }
            for row in geometry["emitters"]
        ],
        "synthetic_test_only": False,
    }


def generate_surrogate_1070(project_root: Path) -> dict[Path, dict[str, Any]]:
    root = project_root.resolve()
    donor = load_json(root / DONOR_GEOMETRY)
    anatomy = load_json(root / ANATOMY)
    optical = load_json(root / OPTICAL)
    if donor["expected_emitter_count"] != 277:
        raise InputValidationError("Yue donor geometry must contain 277 emitters")
    if optical["scientific_status"] != "provisional" or optical["wavelength_nm"] != 1070:
        raise InputValidationError("surrogate requires provisional 1070-nm optics")

    geometry, donor_to_surrogate = _surrogate_geometry(donor)
    calibration = _calibration(geometry)
    registration = _registration(geometry["coordinate_frame"])
    registration["registration_id"] = f"{SURROGATE_ID}_direct_colin27_v1"
    registration["provenance"] = (
        "Identity transform because the Yue-derived donor positions were already "
        "projected into the accepted Colin27 frame. Accepted only for this surrogate; "
        "it does not cross the target-hardware registration gate."
    )

    regional_donors = select_representative_emitters(donor)
    regional_ids = {
        region: donor_to_surrogate[row["emitter_id"]]
        for region, _pilot_id, row in regional_donors
    }
    analysis = {
        "analysis_id": f"{SURROGATE_ID}_analysis_v1",
        "metrics": ["ef_dom", "ef_ref", "ncf", "n_eff"],
        "ratio_absolute_threshold": 1e-12,
        "roi_methods": ["field_first", "metric_first"],
        "source_weighting": [
            {
                "interpretation": (
                    "Unit relative output per emitter; total relative launched energy "
                    "increases with enabled-source count."
                ),
                "per_emitter_weight": 1.0,
                "policy": "constant_per_emitter",
                "total_weight": 277.0,
                "weighting_id": "constant_per_emitter_unit_v1",
            },
            {
                "interpretation": (
                    "Unit total relative launched energy divided equally across all "
                    "277 emitters; not a measured device-power condition."
                ),
                "per_emitter_weight": 1.0 / 277.0,
                "policy": "constant_total",
                "total_weight": 1.0,
                "weighting_id": "constant_total_unit_v1",
            },
        ],
        "sum_dtype": "float64",
        "synthetic_test_only": False,
    }

    first = geometry["emitters"][0]
    source_position, source_direction = _source_in_voxels(first, anatomy)
    volume_path = Path(anatomy["volume_representation"])
    engine = {
        "configuration_id": f"{SURROGATE_ID}_engine_template_v1",
        "isnormalize": 1,
        "nphoton": PHOTON_COUNT_CANDIDATE,
        "outputtype": "fluence",
        "properties_mm": _engine_properties(optical),
        "seed": 1,
        "source": {
            "direction": source_direction,
            "emitter_id": first["emitter_id"],
            "position_voxels": source_position,
            "type": "pencil",
        },
        "synthetic_test_only": False,
        "time_gates_s": {"end": 5e-9, "start": 0.0, "step": 5e-9},
        "volume": {
            "generator": "label_volume_nifti",
            "path": volume_path.as_posix(),
            "sha256": sha256_file(root / volume_path),
            "shape_voxels": anatomy["shape_voxels"],
        },
    }
    generated: dict[Path, dict[str, Any]] = {
        GEOMETRY: geometry,
        CALIBRATION: calibration,
        REGISTRATION: registration,
        ANALYSIS: analysis,
        ENGINE: engine,
    }
    manifest = {
        "code": {"dirty": False, "repository": "MCX Project", "revision": CODE_REVISION},
        "created_at": CREATED_AT,
        "engine": {
            "backend": "opencl",
            "binding": "mcxcl_cli",
            "binding_version": "v2025.10",
            "build": "official source tag v2025.10; local arm64 build",
            "configuration_sha256": _payload_sha(engine),
            "engine_version": "v2025.10",
            "family": "MCX",
            "gpu": "Apple M4 Pro",
            "runtime": "Apple OpenCL on macOS arm64",
        },
        "error": None,
        "execution": {
            "photon_count": PHOTON_COUNT_CANDIDATE,
            "replicate": 1,
            "seed": 1,
            "time_gates_s": engine["time_gates_s"],
        },
        "grid": {
            "coordinate_frame": anatomy["coordinate_frame"],
            "shape_voxels": anatomy["shape_voxels"],
            "voxel_size_mm": anatomy["final_voxel_size_mm"],
        },
        "inputs": {
            "analysis_configuration": _reference("analysis_configuration", analysis["analysis_id"], ANALYSIS, _payload_sha(analysis)),
            "anatomy": _reference("anatomy", anatomy["anatomy_id"], ANATOMY, sha256_file(root / ANATOMY)),
            "calibration": _reference("calibration", calibration["calibration_id"], CALIBRATION, _payload_sha(calibration)),
            "emitter_geometry": _reference("emitter_geometry", geometry["geometry_id"], GEOMETRY, _payload_sha(geometry)),
            "engine_configuration": _reference("engine_configuration", engine["configuration_id"], ENGINE, _payload_sha(engine)),
            "optical_properties": _reference("optical_properties", optical["scenario_id"], OPTICAL, sha256_file(root / OPTICAL)),
            "registration": _reference("registration", registration["registration_id"], REGISTRATION, _payload_sha(registration)),
        },
        "manifest_version": "1.0.0",
        "output_contract": {
            "derivation": "MCX OutputType=f canonical basis field; no device-dose interpretation.",
            "normalization": "normalized per launched energy through MCX isnormalize=1",
            "quantity": "fluence",
            "unit": "MCX normalized fluence units",
        },
        "outputs": [],
        "run_id": f"{SURROGATE_ID}__20260814t220000z__{_payload_sha(engine)[:8]}",
        "scenario_id": optical["scenario_id"],
        "scientific_status": "provisional",
        "source": {
            "emitter_id": first["emitter_id"],
            "normalization": "unit launched-energy normalized basis field (MCX DoNormalize=true)",
            "source_model": "pencil",
        },
        "stage": "pilot",
        "status": "planned",
        "wavelength_nm": 1070.0,
    }
    generated[TEMPLATE] = manifest
    generated[CONVERGENCE] = {
        "axis_depths_mm": {"start": 0, "step": 1, "stop": 60},
        "candidate_full_basis_photon_count": PHOTON_COUNT_CANDIDATE,
        "photon_counts": [100_000, 1_000_000, 10_000_000],
        "profile_validity": {
            "depth_range_mm": [20, 60],
            "minimum_fraction_of_current_profile_max": 1e-8,
        },
        "protocol_id": f"{SURROGATE_ID}_regional_convergence_v1",
        "regional_emitter_ids": regional_ids,
        "replicates_per_count": 3,
        "scenario_id": optical["scenario_id"],
        "status": "frozen_before_execution",
        "stop_rules": [
            "Select the candidate full-basis photon count only if every region passes the final transition.",
            "If any region fails at 10^7 photons, extend the same versioned protocol to 10^8 before preparing the full basis.",
            "Do not interpret this convergence study as target-helmet validation.",
        ],
        "thresholds": {
            "profile_median_cv_max": 0.10,
            "profile_median_step_change_max": 0.10,
            "tissue_integral_cv_max": 0.05,
            "tissue_integral_step_change_max": 0.05,
        },
    }
    generated[CONVERGENCE_EXTENSION] = {
        "axis_depths_mm": {"start": 0, "step": 1, "stop": 60},
        "candidate_full_basis_photon_count": 100_000_000,
        "photon_counts": [100_000, 1_000_000, 10_000_000, 100_000_000],
        "prior_results_path": (
            "results/surrogate_yue277_1070_v1/regional_convergence_v1/results.json"
        ),
        "profile_validity": {
            "depth_range_mm": [20, 60],
            "minimum_fraction_of_current_profile_max": 1e-8,
        },
        "protocol_id": f"{SURROGATE_ID}_regional_convergence_extension_v2",
        "regional_emitter_ids": regional_ids,
        "replicates_per_count": 3,
        "scenario_id": optical["scenario_id"],
        "status": "frozen_after_1e7_candidate_failed",
        "stop_rules": [
            "Reuse the checksum-recorded v1 summaries and run only the new 10^8 tier.",
            "Select 10^8 for the full basis only if every region passes the 10^7-to-10^8 transition.",
            "Do not increase beyond 10^8 or alter the profile sampling without another versioned decision.",
            "Do not interpret this convergence study as target-helmet validation.",
        ],
        "thresholds": {
            "profile_median_cv_max": 0.10,
            "profile_median_step_change_max": 0.10,
            "tissue_integral_cv_max": 0.05,
            "tissue_integral_step_change_max": 0.05,
        },
    }
    return generated


def build_surrogate_1070(project_root: Path, *, check: bool = False) -> dict[str, Any]:
    root = project_root.resolve()
    payloads = generate_surrogate_1070(root)
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
        raise InputValidationError("surrogate outputs are stale or missing:\n- " + "\n- ".join(stale))
    schemas = {
        GEOMETRY: "schemas/emitter_geometry.schema.json",
        CALIBRATION: "schemas/calibration.schema.json",
        REGISTRATION: "schemas/registration.schema.json",
        ANALYSIS: "schemas/analysis_configuration.schema.json",
        ENGINE: "schemas/engine_configuration.schema.json",
        TEMPLATE: "schemas/run_manifest.schema.json",
    }
    for relative, schema in schemas.items():
        validate_json(root / schema, root / relative, require_complete=True)
    preflight_manifest(root / TEMPLATE, root)
    return {
        "basis_plan": "pending regional convergence decision",
        "candidate_photon_count": PHOTON_COUNT_CANDIDATE,
        "emitters": 277,
        "mode": "check" if check else "write",
        "production_eligible": False,
        "regional_emitters": 5,
        "scientific_status": "provisional",
        "status": "valid",
        "surrogate_id": SURROGATE_ID,
    }


def freeze_surrogate_basis_plan(
    project_root: Path, *, check: bool = False
) -> dict[str, Any]:
    """Freeze the full plan only after the versioned regional gate passes."""

    root = project_root.resolve()
    result = load_json(root / CONVERGENCE_RESULT)
    if result["basis_plan_candidate_ready"] is not True:
        raise InputValidationError("regional convergence has not passed")
    if result["candidate_full_basis_photon_count"] != SELECTED_PHOTON_COUNT:
        raise InputValidationError("convergence result did not select 100 million photons")
    if result["protocol_sha256"] != sha256_file(root / CONVERGENCE_EXTENSION):
        raise InputValidationError("convergence result does not match the frozen extension")
    if result["geometry_sha256"] != sha256_file(root / GEOMETRY):
        raise InputValidationError("convergence result does not match the surrogate geometry")
    template = load_json(root / TEMPLATE)
    plan = {
        "basis_set_id": BASIS_SET_ID,
        "code_dirty": False,
        "code_revision": CODE_REVISION,
        "config_root": f"configs/generated/{BASIS_SET_ID}",
        "created_at": "2026-08-14T23:30:00Z",
        "emitter_ids": "enabled",
        "engine_binding": "mcxcl_cli",
        "engine_build": "official source tag v2025.10; local arm64 build",
        "engine_version": "v2025.10",
        "photon_count": SELECTED_PHOTON_COUNT,
        "replicates": 1,
        "run_root": f"runs/{BASIS_SET_ID}",
        "scenario_id": template["scenario_id"],
        "scientific_status": "provisional",
        "synthetic_test_only": False,
        "template_manifest_path": TEMPLATE.as_posix(),
        "template_manifest_sha256": sha256_file(root / TEMPLATE),
    }
    expected = _json_text(plan)
    path = root / BASIS_PLAN
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            raise InputValidationError("frozen surrogate basis plan is stale or missing")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8")
    validate_json(
        root / "schemas/basis_plan.schema.json", path, require_complete=True
    )
    return {
        "basis_plan": BASIS_PLAN.as_posix(),
        "emitters": 277,
        "mode": "check" if check else "write",
        "photon_count": SELECTED_PHOTON_COUNT,
        "scientific_status": "provisional",
        "status": "frozen_after_regional_convergence",
    }
