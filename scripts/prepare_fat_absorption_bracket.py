#!/usr/bin/env python3
"""Prepare immutable RTX 3080 Ti bases for a 1070-nm fat-mua bracket."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from mcx_project.hashing import sha256_file
from mcx_project.preflight import preflight_manifest
from mcx_project.validation import validate_json


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = Path("inputs/fat_absorption_bracket_v1")
VOLUME_PATH = INPUT_ROOT / "colin27_labels_native12_1mm_v3.nii"
ANATOMY_PATH = INPUT_ROOT / "anatomy_metadata.json"
GEOMETRY_PATH = INPUT_ROOT / "emitter_geometry.json"
CALIBRATION_PATH = INPUT_ROOT / "calibration.json"
REGISTRATION_PATH = INPUT_ROOT / "registration.json"
ANALYSIS_PATH = INPUT_ROOT / "analysis.json"
PROTOCOL_PATH = INPUT_ROOT / "protocol.json"

BASE_PATHS = {
    "anatomy": Path(
        "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/anatomy_metadata.json"
    ),
    "geometry": Path("inputs/emitters/surrogate_yue277_1070_v1/emitter_geometry.json"),
    "calibration": Path("inputs/emitters/surrogate_yue277_1070_v1/calibration.json"),
    "registration": Path("inputs/registration/surrogate_yue277_1070_v1.json"),
    "analysis": Path("configs/surrogate_yue277_1070_v1_analysis_v2.json"),
    "optical": Path("inputs/optical_properties/provisional_1070_v1/central.json"),
    "engine": Path("configs/surrogate_yue277_1070_v1_engine_template.json"),
    "template": Path(
        "runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_v1/template_manifest.json"
    ),
    "plan": Path("configs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1.json"),
    "environment": Path("environment/windows_rtx3080ti_opencl_v1.json"),
}

CASES = (
    {
        "case": "fat_abs_005065",
        "scenario_id": "provisional_1070_fat_abs_005065_v1",
        "mua_mm-1": 0.005065,
        "role": "low_exact_lipid",
        "citation": (
            "Van Veen et al. 2005 DOI 10.1117/1.2085149; "
            "https://omlc.org/spectra/fat/fat.txt at 1070 nm"
        ),
        "conversion": (
            "Exact 1070-nm processed Van Veen point: 5.065 m^-1 divided by "
            "1000 to 0.005065 mm^-1; Bashkatov fat scattering is held fixed."
        ),
        "uncertainty": (
            "Purified mammalian lipid is not vascularized human cranial adipose; "
            "atlas fat and fat_2 identity remains unresolved."
        ),
    },
    {
        "case": "fat_abs_010",
        "scenario_id": "provisional_1070_fat_abs_010_v1",
        "mua_mm-1": 0.010,
        "role": "recommended_effective_adipose",
        "citation": (
            "Van Veen et al. 2005 exact-1070 lipid spectrum; Damagatla et al. "
            "2026 DOI 10.1038/s41597-026-06586-9 exact-1070 in-vivo abdomen"
        ),
        "conversion": (
            "Project-selected effective-adipose bracket value informed by "
            "0.005065 mm^-1 purified lipid and 0.0096518333 mm^-1 mean bulk "
            "in-vivo abdomen; Bashkatov fat scattering is held fixed."
        ),
        "uncertainty": (
            "Not a direct scalp-adipose measurement; combines lipid-only and bulk "
            "abdominal evidence as a declared provisional sensitivity assumption."
        ),
    },
    {
        "case": "fat_abs_030",
        "scenario_id": "provisional_1070_fat_abs_030_v1",
        "mua_mm-1": 0.030,
        "role": "high_effective_adipose",
        "citation": (
            "Damagatla et al. 2026 DOI 10.1038/s41597-026-06586-9 "
            "exact-1070 in-vivo abdomen subject-mean range"
        ),
        "conversion": (
            "Rounded high bracket within the observed 0.00502-0.0310167 mm^-1 "
            "bulk abdominal subject-mean range; Bashkatov fat scattering is held fixed."
        ),
        "uncertainty": (
            "Bulk abdomen is layered rather than isolated scalp adipose; this is a "
            "high sensitivity endpoint, not a nominal tissue claim."
        ),
    },
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _payload_sha256(value: Any) -> str:
    return sha256(_json_bytes(value)).hexdigest()


def _git_json(root: Path, path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "show", f"HEAD:{path.as_posix()}"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout)


def _write_immutable(root: Path, relative: Path, value: Any) -> None:
    path = root / relative
    rendered = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != rendered:
            raise RuntimeError(f"refusing to replace immutable artifact: {relative}")
        return
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _reference(
    role: str, artifact_id: str, path: Path, digest: str
) -> dict[str, str]:
    schema_and_id = {
        "analysis_configuration": ("analysis_id", "schemas/analysis_configuration.schema.json"),
        "anatomy": ("anatomy_id", "schemas/anatomy_metadata.schema.json"),
        "calibration": ("calibration_id", "schemas/calibration.schema.json"),
        "emitter_geometry": ("geometry_id", "schemas/emitter_geometry.schema.json"),
        "engine_configuration": (
            "configuration_id",
            "schemas/engine_configuration.schema.json",
        ),
        "optical_properties": ("scenario_id", "schemas/optical_properties.schema.json"),
        "registration": ("registration_id", "schemas/registration.schema.json"),
    }
    id_field, schema_path = schema_and_id[role]
    return {
        "artifact_id": artifact_id,
        "id_field": id_field,
        "path": path.as_posix(),
        "schema_path": schema_path,
        "sha256": digest,
    }


def _engine_properties(optical: dict[str, Any]) -> list[list[float]]:
    maximum = max(int(row["tissue_id"]) for row in optical["tissues"])
    properties = [[0.0, 0.0, 1.0, 1.0] for _ in range(maximum + 1)]
    for row in optical["tissues"]:
        tissue_id = int(row["tissue_id"])
        if tissue_id:
            properties[tissue_id] = [
                float(row["mua_mm-1"]),
                float(row["mus_mm-1"]),
                float(row["g"]),
                float(row["n"]),
            ]
    return properties


def _case_paths(case: str) -> dict[str, Path]:
    basis_id = f"surrogate_yue277_1070_windows_rtx3080ti_{case}_basis_v1"
    run_root = Path("runs") / basis_id
    return {
        "optical": INPUT_ROOT / f"{case}.json",
        "engine": Path("configs") / f"{case}_engine_template_v1.json",
        "template": run_root / "template_manifest.json",
        "plan": Path("configs") / f"{basis_id}.json",
        "config_root": Path("configs/generated") / basis_id,
        "run_root": run_root,
    }


def main() -> int:
    root = ROOT.resolve()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if status:
        raise SystemExit("repository must be clean before binding immutable runs")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    anatomy = _git_json(root, BASE_PATHS["anatomy"])
    anatomy["volume_representation"] = VOLUME_PATH.as_posix()
    geometry = _git_json(root, BASE_PATHS["geometry"])
    calibration = _git_json(root, BASE_PATHS["calibration"])
    registration = _git_json(root, BASE_PATHS["registration"])
    analysis = _git_json(root, BASE_PATHS["analysis"])
    central = _git_json(root, BASE_PATHS["optical"])
    base_engine = _git_json(root, BASE_PATHS["engine"])
    base_template = _git_json(root, BASE_PATHS["template"])
    base_plan = _git_json(root, BASE_PATHS["plan"])
    environment = _git_json(root, BASE_PATHS["environment"])

    if environment["device"] != "NVIDIA GeForce RTX 3080 Ti":
        raise SystemExit("saved environment is not the validated RTX 3080 Ti")
    if "2025.10" not in environment["engine_version"]:
        raise SystemExit("saved environment is not MCX-CL v2025.10")
    if sha256_file(root / VOLUME_PATH) != base_engine["volume"]["sha256"]:
        raise SystemExit("local bracket anatomy copy does not match the frozen volume")

    shared = {
        ANATOMY_PATH: anatomy,
        GEOMETRY_PATH: geometry,
        CALIBRATION_PATH: calibration,
        REGISTRATION_PATH: registration,
        ANALYSIS_PATH: analysis,
    }
    for relative, value in shared.items():
        _write_immutable(root, relative, value)

    shared_references = {
        "analysis_configuration": _reference(
            "analysis_configuration", analysis["analysis_id"], ANALYSIS_PATH, _payload_sha256(analysis)
        ),
        "anatomy": _reference(
            "anatomy", anatomy["anatomy_id"], ANATOMY_PATH, _payload_sha256(anatomy)
        ),
        "calibration": _reference(
            "calibration", calibration["calibration_id"], CALIBRATION_PATH, _payload_sha256(calibration)
        ),
        "emitter_geometry": _reference(
            "emitter_geometry", geometry["geometry_id"], GEOMETRY_PATH, _payload_sha256(geometry)
        ),
        "registration": _reference(
            "registration", registration["registration_id"], REGISTRATION_PATH, _payload_sha256(registration)
        ),
    }

    case_records: list[dict[str, Any]] = []
    timestamp = created_at.replace("-", "").replace(":", "").replace("T", "t").replace("Z", "z")
    for spec in CASES:
        paths = _case_paths(spec["case"])
        optical = copy.deepcopy(central)
        optical["scenario_id"] = spec["scenario_id"]
        for row in optical["tissues"]:
            if int(row["tissue_id"]) in {4, 9}:
                row["mua_mm-1"] = spec["mua_mm-1"]
                row["citation"] = spec["citation"]
                row["conversion"] = spec["conversion"]
                row["source_kind"] = "assumption"
                row["source_wavelengths_nm"] = [1070.0]
                row["uncertainty"] = spec["uncertainty"]
                row["notes"] += (
                    f" Fat-absorption bracket role: {spec['role']}; scattering unchanged."
                )
        _write_immutable(root, paths["optical"], optical)
        validate_json(
            root / "schemas/optical_properties.schema.json",
            root / paths["optical"],
            require_complete=True,
        )

        engine = copy.deepcopy(base_engine)
        engine["configuration_id"] = f"{spec['case']}_engine_template_v1"
        engine["properties_mm"] = _engine_properties(optical)
        engine["volume"]["path"] = VOLUME_PATH.as_posix()
        engine["volume"]["sha256"] = sha256_file(root / VOLUME_PATH)
        _write_immutable(root, paths["engine"], engine)
        validate_json(
            root / "schemas/engine_configuration.schema.json",
            root / paths["engine"],
            require_complete=True,
        )

        template = copy.deepcopy(base_template)
        template["created_at"] = created_at
        template["code"] = {
            "repository": base_template["code"]["repository"],
            "revision": revision,
            "dirty": False,
        }
        template["scenario_id"] = spec["scenario_id"]
        template["run_id"] = (
            f"{spec['scenario_id']}__{timestamp}__{_payload_sha256(engine)[:8]}"
        )
        template["status"] = "planned"
        template["error"] = None
        template["outputs"] = []
        template["engine"].update(
            {
                "configuration_sha256": _payload_sha256(engine),
                "binding": environment["binding"],
                "binding_version": environment["engine_version"],
                "engine_version": environment["engine_version"],
                "build": (
                    "official Windows MCX-CL v2025.10 binary; executable_sha256="
                    + environment["executable_sha256"]
                ),
                "gpu": environment["device"],
                "runtime": environment["platform"],
            }
        )
        template["inputs"].update(shared_references)
        template["inputs"]["optical_properties"] = _reference(
            "optical_properties", optical["scenario_id"], paths["optical"], _payload_sha256(optical)
        )
        template["inputs"]["engine_configuration"] = _reference(
            "engine_configuration", engine["configuration_id"], paths["engine"], _payload_sha256(engine)
        )
        _write_immutable(root, paths["template"], template)
        validate_json(
            root / "schemas/run_manifest.schema.json",
            root / paths["template"],
            require_complete=True,
        )
        preflight_manifest(root / paths["template"], root)

        plan = copy.deepcopy(base_plan)
        plan.update(
            {
                "basis_set_id": paths["run_root"].name,
                "scenario_id": spec["scenario_id"],
                "created_at": created_at,
                "code_revision": revision,
                "code_dirty": False,
                "engine_binding": environment["binding"],
                "engine_version": environment["engine_version"],
                "engine_build": template["engine"]["build"],
                "template_manifest_path": paths["template"].as_posix(),
                "template_manifest_sha256": _payload_sha256(template),
                "config_root": paths["config_root"].as_posix(),
                "run_root": paths["run_root"].as_posix(),
            }
        )
        _write_immutable(root, paths["plan"], plan)
        validate_json(
            root / "schemas/basis_plan.schema.json",
            root / paths["plan"],
            require_complete=True,
        )
        case_records.append(
            {
                **spec,
                "optical_path": paths["optical"].as_posix(),
                "engine_path": paths["engine"].as_posix(),
                "template_path": paths["template"].as_posix(),
                "plan_path": paths["plan"].as_posix(),
                "run_root": paths["run_root"].as_posix(),
            }
        )

    protocol = {
        "protocol_id": "surrogate_yue277_1070_fat_absorption_bracket_v1",
        "created_at": created_at,
        "code_revision": revision,
        "scientific_status": (
            "provisional_yue_derived_spatial_surrogate_not_target_helmet_"
            "not_measured_dose_not_biological_efficacy"
        ),
        "environment": {
            "path": BASE_PATHS["environment"].as_posix(),
            "device": environment["device"],
            "engine_version": environment["engine_version"],
            "executable_sha256": environment["executable_sha256"],
        },
        "frozen_dimensions": {
            "emitter_count": 277,
            "photon_count_per_emitter": 100_000_000,
            "replicates_per_emitter": 1,
            "fat_tissue_ids": [4, 9],
            "changed_parameter": "mua_mm-1 only",
            "fat_scattering_held_fixed": True,
        },
        "evidence": [
            {
                "source": "Van Veen et al. 2005",
                "doi": "10.1117/1.2085149",
                "data": "https://omlc.org/spectra/fat/fat.txt",
                "value_1070_mm-1": 0.005065,
            },
            {
                "source": "Damagatla et al. 2026 in-vivo abdomen",
                "doi": "10.1038/s41597-026-06586-9",
                "mean_1070_mm-1": 0.00965183333333,
                "subject_mean_range_1070_mm-1": [0.00502, 0.0310166666667],
            },
        ],
        "existing_extreme_high_baseline": {
            "scenario_id": "provisional_1070_v1",
            "fat_mua_mm-1": 0.103,
            "basis_index": (
                "runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1/index.json"
            ),
            "aggregate_analysis": (
                "results/surrogate_yue277_1070_windows_rtx3080ti_opencl_analysis_v1"
            ),
        },
        "cases": case_records,
    }
    _write_immutable(root, PROTOCOL_PATH, protocol)
    print(json.dumps({"status": "prepared_not_executed", "protocol": PROTOCOL_PATH.as_posix(), "cases": case_records}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
