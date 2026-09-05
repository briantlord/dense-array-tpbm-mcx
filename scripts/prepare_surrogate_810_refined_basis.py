#!/usr/bin/env python3
"""Prepare the immutable 277-source refined-primary 810-nm Windows basis."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from mcx_project.basis import prepare_basis_plan
from mcx_project.hashing import sha256_file
from mcx_project.validation import load_json, validate_json


ROOT = Path(__file__).resolve().parents[1]
CREATED_AT = "2026-08-24T21:50:01Z"
CODE_REVISION = "00f714dfc3557d9803c94645e62c79b59f3f4e01"
SCENARIO_ID = "provisional_810_in_vivo_skull_refined_dura_marrow_v2"
BASIS_SET_ID = "surrogate_yue277_810_windows_rtx3080ti_opencl_basis_v3"
ENGINE_VERSION = "MCXCL Revision 12544350; v2025.10"
ENGINE_SHA256 = "15ceb16fec553cad4a0481cdf62792f3a512e77991d8304c8afe1c1d49f1a8ee"
ENGINE_BUILD = (
    "official Windows MCX-CL v2025.10 binary; "
    f"executable_sha256={ENGINE_SHA256}"
)

BASE_OPTICAL = Path("inputs/optical_properties/provisional_810_v1/central_in_vivo_skull.json")
OVERLAY = Path("inputs/optical_properties/provisional_810_v2/refined_primary_overlay.json")
EFFECTIVE_OPTICAL = Path("inputs/optical_properties/provisional_810_v2/central_refined_primary.json")
BASE_ENGINE = Path("configs/surrogate_yue277_1070_v1_engine_template.json")
ENGINE_CONFIG = Path("configs/surrogate_yue277_810_v2_engine_template.json")
BASE_ANALYSIS = Path("configs/surrogate_yue277_1070_v1_analysis_v2.json")
ANALYSIS_CONFIG = Path("configs/surrogate_yue277_810_v2_analysis.json")
BASE_GEOMETRY = Path("inputs/emitters/surrogate_yue277_1070_v1/emitter_geometry.json")
GEOMETRY = Path("inputs/emitters/surrogate_yue277_810_v1/emitter_geometry.json")
CALIBRATION = Path("inputs/emitters/surrogate_yue277_810_v1/calibration.json")
BASE_TEMPLATE = Path(
    "runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_v1/template_manifest.json"
)
TEMPLATE = Path("runs/surrogate_yue277_810_windows_rtx3080ti_opencl_v2/template_manifest.json")
PLAN = Path("configs/surrogate_yue277_810_windows_rtx3080ti_opencl_basis_v3.json")


def _write_immutable(path: Path, value: Any) -> None:
    path = ROOT / path
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise RuntimeError(f"refusing to replace immutable artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _reference(path: Path, artifact_id: str, id_field: str, schema: str) -> dict[str, str]:
    return {
        "artifact_id": artifact_id,
        "id_field": id_field,
        "path": path.as_posix(),
        "schema_path": schema,
        "sha256": sha256_file(ROOT / path),
    }


def _effective_optical() -> dict[str, Any]:
    base = copy.deepcopy(load_json(ROOT / BASE_OPTICAL))
    overlay = load_json(ROOT / OVERLAY)
    by_id = {int(row["tissue_id"]): row for row in base["tissues"]}
    for override in overlay["overrides"]:
        tissue_id = int(override["tissue_id"])
        by_id[tissue_id].update({key: value for key, value in override.items() if key != "tissue_id"})
    by_id[10].update(
        {
            "source_kind": "direct_measurement",
            "source_wavelengths_nm": [810.0],
            "tissue_definition": "Colin27 dura represented by ex-vivo post-mortem human cranial dura measured at 810 nm.",
            "uncertainty": "One post-mortem donor; sample preparation and fixed IAD g/n inputs limit in-vivo generalization.",
            "review_status": "double_checked",
        }
    )
    by_id[11].update(
        {
            "source_kind": "direct_measurement",
            "source_wavelengths_nm": [810.0],
            "tissue_definition": "Colin27 cranial-marrow label represented by frozen human tibial marrow measured at 810 nm.",
            "uncertainty": "One elderly donor and a non-cranial frozen-marrow proxy; targeted endpoint runs define the retained sensitivity band.",
            "review_status": "double_checked",
        }
    )
    base["scenario_id"] = SCENARIO_ID
    base["tissues"] = [by_id[key] for key in sorted(by_id)]
    return base


def _engine_config(optical: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(load_json(ROOT / BASE_ENGINE))
    rows = {int(row["tissue_id"]): row for row in optical["tissues"]}
    properties: list[list[float]] = []
    for tissue_id in range(13):
        row = rows.get(tissue_id)
        if row is None or tissue_id in {0, 8}:
            properties.append([0.0, 0.0, 1.0, 1.0])
        else:
            properties.append(
                [
                    float(row["mua_mm-1"]),
                    float(row["mus_mm-1"]),
                    float(row["g"]),
                    float(row["n"]),
                ]
            )
    config["configuration_id"] = "surrogate_yue277_810_v2_engine_template_v1"
    config["properties_mm"] = properties
    config["source"]["emitter_id"] = "SUR810_001"
    return config


def _analysis_config() -> dict[str, Any]:
    value = copy.deepcopy(load_json(ROOT / BASE_ANALYSIS))
    value["analysis_id"] = "surrogate_yue277_810_v2_analysis_v1"
    value["reference_protocol"]["reference_emitter_id"] = "SUR810_275"
    value["reference_protocol"]["interpretation"] = (
        "Superior-region single-source reference inherited from the frozen Yue-derived "
        "spatial surrogate. EF_ref is a conditional comparison, not a target-device "
        "baseline or biological reference."
    )
    return value


def _geometry() -> dict[str, Any]:
    value = copy.deepcopy(load_json(ROOT / BASE_GEOMETRY))
    value["dataset_id"] = "surrogate_yue277_810_v1"
    value["geometry_id"] = "surrogate_yue277_810_v1"
    value["helmet_model"] = (
        "Yue-derived 277-position spatial surrogate independently bound to 810 nm; "
        "not target helmet CAD or radiometry"
    )
    for row in value["emitters"]:
        row["emitter_id"] = row["emitter_id"].replace("SUR1070_", "SUR810_")
        row["calibration_id"] = "surrogate_yue277_810_unit_source_v1"
        row["wavelength_peak_nm"] = 810.0
        row["beam_parameter_value"] = (
            "zero-width pencil Yue-spatial surrogate; target 810-nm beam profile "
            "has not been supplied"
        )
        row["provenance"] = (
            row["provenance"]
            + " The position and normal are wavelength-independent geometry; this "
            "version is independently labeled and calibrated for the 810-nm basis."
        )
    return value


def _calibration() -> dict[str, Any]:
    geometry = load_json(ROOT / GEOMETRY)
    return {
        "calibration_id": "surrogate_yue277_810_unit_source_v1",
        "date": "2026-08-24",
        "instrument": "numerical unit-launched-energy convention; not a radiometer",
        "provenance": (
            "The Yue-derived 277-position spatial surrogate is reused independently at "
            "810 nm. Every source has unit relative weight only for normalized basis "
            "fields; no measured device power, beam, coupling, or dose is represented."
        ),
        "records": [
            {
                "emitter_id": row["emitter_id"],
                "optical_power_cw_W": 1.0,
                "power_uncertainty_W": 0.0,
                "wavelength_peak_nm": 810.0,
            }
            for row in geometry["emitters"]
            if row["enabled"]
        ],
        "synthetic_test_only": False,
    }


def _template(engine: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(load_json(ROOT / BASE_TEMPLATE))
    engine_hash = sha256_file(ROOT / ENGINE_CONFIG)
    timestamp = CREATED_AT.replace("-", "").replace(":", "").replace("T", "t").replace("Z", "z")
    value["created_at"] = CREATED_AT
    value["scenario_id"] = SCENARIO_ID
    value["wavelength_nm"] = 810.0
    value["run_id"] = f"{SCENARIO_ID}__{timestamp}__{engine_hash[:8]}"
    value["code"] = {
        "repository": "MCX Project",
        "revision": CODE_REVISION,
        "dirty": True,
    }
    value["source"]["emitter_id"] = engine["source"]["emitter_id"]
    value["engine"]["configuration_sha256"] = engine_hash
    value["engine"]["binding_version"] = ENGINE_VERSION
    value["engine"]["engine_version"] = ENGINE_VERSION
    value["engine"]["build"] = ENGINE_BUILD
    value["inputs"]["optical_properties"] = _reference(
        EFFECTIVE_OPTICAL, SCENARIO_ID, "scenario_id", "schemas/optical_properties.schema.json"
    )
    value["inputs"]["engine_configuration"] = _reference(
        ENGINE_CONFIG,
        engine["configuration_id"],
        "configuration_id",
        "schemas/engine_configuration.schema.json",
    )
    value["inputs"]["analysis_configuration"] = _reference(
        ANALYSIS_CONFIG,
        "surrogate_yue277_810_v2_analysis_v1",
        "analysis_id",
        "schemas/analysis_configuration.schema.json",
    )
    value["inputs"]["calibration"] = _reference(
        CALIBRATION,
        "surrogate_yue277_810_unit_source_v1",
        "calibration_id",
        "schemas/calibration.schema.json",
    )
    value["inputs"]["emitter_geometry"] = _reference(
        GEOMETRY,
        "surrogate_yue277_810_v1",
        "geometry_id",
        "schemas/emitter_geometry.schema.json",
    )
    return value


def _plan() -> dict[str, Any]:
    return {
        "basis_set_id": BASIS_SET_ID,
        "code_dirty": True,
        "code_revision": CODE_REVISION,
        "config_root": f"configs/generated/{BASIS_SET_ID}",
        "created_at": CREATED_AT,
        "emitter_ids": "enabled",
        "engine_binding": "mcxcl_cli",
        "engine_build": ENGINE_BUILD,
        "engine_version": ENGINE_VERSION,
        "photon_count": 100_000_000,
        "replicates": 1,
        "run_root": f"runs/{BASIS_SET_ID}",
        "scenario_id": SCENARIO_ID,
        "scientific_status": "provisional",
        "synthetic_test_only": False,
        "template_manifest_path": TEMPLATE.as_posix(),
        "template_manifest_sha256": sha256_file(ROOT / TEMPLATE),
    }


def main() -> int:
    optical = _effective_optical()
    _write_immutable(EFFECTIVE_OPTICAL, optical)
    _write_immutable(ENGINE_CONFIG, _engine_config(optical))
    _write_immutable(ANALYSIS_CONFIG, _analysis_config())
    _write_immutable(GEOMETRY, _geometry())
    _write_immutable(CALIBRATION, _calibration())
    engine = load_json(ROOT / ENGINE_CONFIG)
    _write_immutable(TEMPLATE, _template(engine))
    _write_immutable(PLAN, _plan())

    checks = (
        ("schemas/optical_properties.schema.json", EFFECTIVE_OPTICAL),
        ("schemas/engine_configuration.schema.json", ENGINE_CONFIG),
        ("schemas/analysis_configuration.schema.json", ANALYSIS_CONFIG),
        ("schemas/emitter_geometry.schema.json", GEOMETRY),
        ("schemas/calibration.schema.json", CALIBRATION),
        ("schemas/run_manifest.schema.json", TEMPLATE),
        ("schemas/basis_plan.schema.json", PLAN),
    )
    for schema, path in checks:
        validate_json(ROOT / schema, ROOT / path, require_complete=True)
    index = prepare_basis_plan(ROOT / PLAN, ROOT)
    print(
        json.dumps(
            {
                "status": "prepared_not_executed",
                "basis_set_id": BASIS_SET_ID,
                "run_count": len(index["runs"]),
                "index_path": f"runs/{BASIS_SET_ID}/index.json",
                "optical_properties_path": EFFECTIVE_OPTICAL.as_posix(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
