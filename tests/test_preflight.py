import json
import shutil
from pathlib import Path

import pytest

from mcx_project.preflight import (
    preflight_manifest,
    validate_emitter_semantics,
    validate_optical_scientific_status,
)
from mcx_project.validation import InputValidationError, load_json


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "runs/synthetic_smoke_m4pro/manifest.json"


def _copy_preflight_fixture(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    shutil.copytree(
        ROOT / "inputs/synthetic_test_only",
        tmp_path / "inputs/synthetic_test_only",
    )
    (tmp_path / "configs").mkdir()
    for name in ("synthetic_analysis_v1.json", "synthetic_smoke_opencl_v1.json"):
        shutil.copy2(ROOT / "configs" / name, tmp_path / "configs" / name)
    shutil.copytree(
        ROOT / "runs/synthetic_smoke_m4pro",
        tmp_path / "runs/synthetic_smoke_m4pro",
    )


def test_complete_smoke_manifest_passes_preflight() -> None:
    report = preflight_manifest(MANIFEST, ROOT)
    assert report.artifacts_validated == 7
    assert report.checksums_verified == 8


def test_preflight_detects_artifact_tampering(tmp_path: Path) -> None:
    _copy_preflight_fixture(tmp_path)
    optical = tmp_path / "inputs/synthetic_test_only/optical_properties.json"
    value = load_json(optical)
    value["tissues"][1]["mua_mm-1"] = 0.006
    optical.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(InputValidationError, match="checksum mismatch"):
        preflight_manifest(
            tmp_path / "runs/synthetic_smoke_m4pro/manifest.json", tmp_path
        )


def test_emitter_semantics_reject_duplicate_ids_and_nonunit_normals() -> None:
    geometry = load_json(ROOT / "inputs/synthetic_test_only/emitter_geometry.json")
    geometry["emitters"][1]["emitter_id"] = "SYN001"
    with pytest.raises(InputValidationError, match="duplicate emitter IDs"):
        validate_emitter_semantics(geometry)

    geometry = load_json(ROOT / "inputs/synthetic_test_only/emitter_geometry.json")
    geometry["emitters"][0]["normal"] = [0.0, 0.0, 2.0]
    with pytest.raises(InputValidationError, match="normal has norm"):
        validate_emitter_semantics(geometry)


def test_preflight_requires_mcx_reserved_background_row(tmp_path: Path) -> None:
    _copy_preflight_fixture(tmp_path)
    config = tmp_path / "configs/synthetic_smoke_opencl_v1.json"
    value = load_json(config)
    value["properties_mm"][0] = [0.0, 0.0, 0.0, 1.0]
    config.write_text(json.dumps(value), encoding="utf-8")

    manifest = tmp_path / "runs/synthetic_smoke_m4pro/manifest.json"
    manifest_value = load_json(manifest)
    from mcx_project.hashing import sha256_file

    changed_hash = sha256_file(config)
    manifest_value["inputs"]["engine_configuration"]["sha256"] = changed_hash
    manifest_value["engine"]["configuration_sha256"] = changed_hash
    manifest.write_text(json.dumps(manifest_value), encoding="utf-8")

    with pytest.raises(InputValidationError, match="engine optical properties"):
        preflight_manifest(manifest, tmp_path)


def test_preflight_rejects_provisional_optics_in_production_run() -> None:
    optical = load_json(
        ROOT / "inputs/optical_properties/provisional_1070_v1/central.json"
    )
    with pytest.raises(InputValidationError, match="scientific statuses"):
        validate_optical_scientific_status(
            {"scientific_status": "production"}, optical
        )


def test_source_coordinates_are_validated_even_after_rehashing(tmp_path):
    _copy_preflight_fixture(tmp_path)
    config_path = tmp_path / "configs/synthetic_smoke_opencl_v1.json"
    config = load_json(config_path)
    config["source"]["position_voxels"] = [-10000, -10000, -10000]
    config["source"]["direction"] = [0, 0, 0]
    config_path.write_text(json.dumps(config), encoding="utf-8")
    from mcx_project.hashing import sha256_file
    manifest_path = tmp_path / "runs/synthetic_smoke_m4pro/manifest.json"
    manifest = load_json(manifest_path)
    digest = sha256_file(config_path)
    manifest["inputs"]["engine_configuration"]["sha256"] = digest
    manifest["engine"]["configuration_sha256"] = digest
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(InputValidationError, match="unit vector"):
        preflight_manifest(manifest_path, tmp_path)
