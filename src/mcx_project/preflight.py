"""Fail-closed validation of a run manifest and all referenced artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from .hashing import sha256_file
from .validation import InputValidationError, load_json, validate_json


_ARTIFACT_CONTRACTS = {
    "anatomy": ("anatomy_id", "schemas/anatomy_metadata.schema.json"),
    "optical_properties": ("scenario_id", "schemas/optical_properties.schema.json"),
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


@dataclass(frozen=True)
class PreflightReport:
    manifest: Path
    run_id: str
    artifacts_validated: int
    checksums_verified: int


def _safe_project_path(project_root: Path, raw_path: str, *, field: str) -> Path:
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise InputValidationError(f"{field} must be a project-relative path: {raw_path}")
    resolved_root = project_root.resolve()
    resolved = (resolved_root / Path(*relative.parts)).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise InputValidationError(f"{field} escapes the project root: {raw_path}")
    if not resolved.is_file():
        raise InputValidationError(f"{field} does not exist or is not a file: {raw_path}")
    return resolved


def _validate_checksum(path: Path, expected: str, *, field: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise InputValidationError(
            f"checksum mismatch for {field}: expected {expected}, got {actual}"
        )


def validate_emitter_semantics(value: dict[str, Any]) -> None:
    emitters = value["emitters"]
    emitter_ids = [emitter["emitter_id"] for emitter in emitters]
    duplicates = sorted({item for item in emitter_ids if emitter_ids.count(item) > 1})
    if duplicates:
        raise InputValidationError(f"duplicate emitter IDs: {', '.join(duplicates)}")

    positions: dict[tuple[float, float, float], str] = {}
    for emitter in emitters:
        normal = np.asarray(emitter["normal"], dtype=np.float64)
        norm = float(np.linalg.norm(normal))
        if not np.isclose(norm, 1.0, rtol=0.0, atol=1e-6):
            raise InputValidationError(
                f"emitter {emitter['emitter_id']} normal has norm {norm}, expected 1"
            )
        position = tuple(float(component) for component in emitter["position_mm"])
        if position in positions and not emitter.get("duplicate_position_justification"):
            raise InputValidationError(
                f"emitter {emitter['emitter_id']} duplicates the position of "
                f"{positions[position]} without justification"
            )
        positions[position] = emitter["emitter_id"]

    expected = value.get("expected_emitter_count")
    if expected is not None and len(emitters) != expected:
        raise InputValidationError(
            f"expected {expected} emitters but found {len(emitters)}"
        )


def validate_optical_semantics(value: dict[str, Any]) -> None:
    tissue_ids = [row["tissue_id"] for row in value["tissues"]]
    if len(tissue_ids) != len(set(tissue_ids)):
        raise InputValidationError("optical table contains duplicate tissue IDs")


def _validate_cross_artifact_semantics(
    manifest: dict[str, Any], artifacts: dict[str, dict[str, Any]]
) -> None:
    geometry = artifacts["emitter_geometry"]
    optical = artifacts["optical_properties"]
    anatomy = artifacts["anatomy"]
    registration = artifacts["registration"]
    calibration = artifacts["calibration"]
    engine_config = artifacts["engine_configuration"]
    source = manifest["source"]

    matching = [
        emitter
        for emitter in geometry["emitters"]
        if emitter["emitter_id"] == source["emitter_id"]
    ]
    if len(matching) != 1:
        raise InputValidationError(
            f"manifest source emitter {source['emitter_id']} is absent or non-unique"
        )
    emitter = matching[0]
    if not emitter["enabled"]:
        raise InputValidationError(f"manifest source emitter {source['emitter_id']} is disabled")

    wavelength = float(manifest["wavelength_nm"])
    if not np.isclose(float(emitter["wavelength_peak_nm"]), wavelength, atol=1e-9):
        raise InputValidationError("manifest and emitter wavelengths do not match")
    if not np.isclose(float(optical["wavelength_nm"]), wavelength, atol=1e-9):
        raise InputValidationError("manifest and optical-table wavelengths do not match")

    if manifest["scenario_id"] != optical["scenario_id"]:
        raise InputValidationError("manifest and optical-table scenario IDs do not match")

    if source["source_model"] != emitter["source_type"]:
        raise InputValidationError("manifest and emitter source models do not match")
    if engine_config["source"]["emitter_id"] != source["emitter_id"]:
        raise InputValidationError("manifest and engine configuration source IDs do not match")
    if engine_config["source"]["type"] != source["source_model"]:
        raise InputValidationError("manifest and engine configuration source models do not match")

    execution = manifest["execution"]
    if engine_config["nphoton"] != execution["photon_count"]:
        raise InputValidationError("manifest and engine configuration photon counts do not match")
    if engine_config["seed"] != execution["seed"]:
        raise InputValidationError("manifest and engine configuration seeds do not match")
    if engine_config["time_gates_s"] != execution["time_gates_s"]:
        raise InputValidationError("manifest and engine configuration time gates do not match")
    if engine_config["volume"]["shape_voxels"] != manifest["grid"]["shape_voxels"]:
        raise InputValidationError("manifest and engine configuration grid shapes do not match")
    if anatomy["shape_voxels"] != manifest["grid"]["shape_voxels"]:
        raise InputValidationError("manifest and anatomy grid shapes do not match")
    if anatomy["final_voxel_size_mm"] != manifest["grid"]["voxel_size_mm"]:
        raise InputValidationError("manifest and anatomy voxel sizes do not match")
    if anatomy["coordinate_frame"] != manifest["grid"]["coordinate_frame"]:
        raise InputValidationError("manifest and anatomy coordinate frames do not match")
    volume = engine_config["volume"]
    if volume["generator"] == "label_volume_nifti":
        if volume["path"] != anatomy["volume_representation"]:
            raise InputValidationError(
                "engine label volume does not match anatomy volume representation"
            )
    elif volume["generator"] != "homogeneous_cube":
        raise InputValidationError("unsupported engine volume generator")

    if registration["source_frame"] != geometry["coordinate_frame"]:
        raise InputValidationError("registration source frame does not match emitter geometry")
    if registration["target_frame"] != anatomy["coordinate_frame"]:
        raise InputValidationError("registration target frame does not match anatomy")
    if not registration["accepted"]:
        raise InputValidationError("registration has not been accepted")

    calibration_records = {
        record["emitter_id"]: record for record in calibration["records"]
    }
    if emitter["calibration_id"] != calibration["calibration_id"]:
        raise InputValidationError("emitter calibration ID does not match calibration artifact")
    if source["emitter_id"] not in calibration_records:
        raise InputValidationError("source emitter has no calibration record")
    record = calibration_records[source["emitter_id"]]
    for field in ("wavelength_peak_nm", "optical_power_cw_W", "power_uncertainty_W"):
        if not np.isclose(float(record[field]), float(emitter[field]), atol=1e-12):
            raise InputValidationError(f"emitter and calibration {field} values do not match")

    anatomy_labels = [label["id"] for label in anatomy["labels"]]
    optical_labels = [row["tissue_id"] for row in optical["tissues"]]
    if anatomy_labels != optical_labels:
        raise InputValidationError("anatomy and optical-table tissue IDs do not match in order")
    expected_properties = []
    for row in optical["tissues"]:
        # MCX reserves medium 0 as the background row and documents it as
        # [0, 0, 1, 1]. The scientific optical table still stores the physical
        # background/air value; this engine-only sentinel is applied here.
        if row["tissue_id"] == 0:
            expected_properties.append([0.0, 0.0, 1.0, 1.0])
        else:
            expected_properties.append(
                [row["mua_mm-1"], row["mus_mm-1"], row["g"], row["n"]]
            )
    if not np.allclose(
        np.asarray(engine_config["properties_mm"], dtype=np.float64),
        np.asarray(expected_properties, dtype=np.float64),
        rtol=0.0,
        atol=1e-12,
    ):
        raise InputValidationError("engine optical properties do not match the optical table")

    expected_synthetic = manifest["scientific_status"] == "synthetic_test_only"
    for role, artifact in artifacts.items():
        if artifact.get("synthetic_test_only") is not expected_synthetic:
            raise InputValidationError(
                f"inputs.{role}.synthetic_test_only conflicts with scientific_status"
            )


def preflight_manifest(manifest_path: Path, project_root: Path) -> PreflightReport:
    """Validate the manifest, every artifact, all hashes, and cross-file invariants."""

    project_root = project_root.resolve()
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_relative_to(project_root):
        raise InputValidationError("manifest must be located inside the project root")

    manifest_schema = project_root / "schemas/run_manifest.schema.json"
    validate_json(manifest_schema, manifest_path, require_complete=True)
    manifest = load_json(manifest_path)

    artifacts: dict[str, dict[str, Any]] = {}
    checksum_count = 0
    for role, reference in manifest["inputs"].items():
        expected_id_field, expected_schema = _ARTIFACT_CONTRACTS[role]
        if reference["id_field"] != expected_id_field:
            raise InputValidationError(
                f"inputs.{role}.id_field must be {expected_id_field}"
            )
        if reference["schema_path"] != expected_schema:
            raise InputValidationError(
                f"inputs.{role}.schema_path must be {expected_schema}"
            )
        artifact_path = _safe_project_path(
            project_root, reference["path"], field=f"inputs.{role}.path"
        )
        schema_path = _safe_project_path(
            project_root, reference["schema_path"], field=f"inputs.{role}.schema_path"
        )
        _validate_checksum(artifact_path, reference["sha256"], field=f"inputs.{role}")
        checksum_count += 1
        validate_json(schema_path, artifact_path, require_complete=True)
        artifact = load_json(artifact_path)
        if artifact.get(reference["id_field"]) != reference["artifact_id"]:
            raise InputValidationError(
                f"inputs.{role}.artifact_id does not match {reference['id_field']}"
            )
        artifacts[role] = artifact

    if (
        manifest["engine"]["configuration_sha256"]
        != manifest["inputs"]["engine_configuration"]["sha256"]
    ):
        raise InputValidationError(
            "engine.configuration_sha256 does not match the engine-configuration artifact"
        )

    validate_emitter_semantics(artifacts["emitter_geometry"])
    validate_optical_semantics(artifacts["optical_properties"])
    engine_volume = artifacts["engine_configuration"]["volume"]
    if engine_volume["generator"] == "label_volume_nifti":
        volume_path = _safe_project_path(
            project_root,
            engine_volume["path"],
            field="inputs.engine_configuration.volume.path",
        )
        _validate_checksum(
            volume_path,
            engine_volume["sha256"],
            field="inputs.engine_configuration.volume",
        )
        checksum_count += 1
    _validate_cross_artifact_semantics(manifest, artifacts)

    for index, output in enumerate(manifest.get("outputs", [])):
        output_path = _safe_project_path(
            project_root, output["path"], field=f"outputs[{index}].path"
        )
        _validate_checksum(output_path, output["sha256"], field=f"outputs[{index}]")
        checksum_count += 1

    return PreflightReport(
        manifest=manifest_path,
        run_id=manifest["run_id"],
        artifacts_validated=len(artifacts),
        checksums_verified=checksum_count,
    )
