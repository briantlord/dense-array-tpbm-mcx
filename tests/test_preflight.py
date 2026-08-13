import json
import shutil
from pathlib import Path

import pytest

from mcx_project.preflight import preflight_manifest, validate_emitter_semantics
from mcx_project.validation import InputValidationError, load_json


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "runs/synthetic_smoke_m4pro/manifest.json"


def test_complete_smoke_manifest_passes_preflight() -> None:
    report = preflight_manifest(MANIFEST, ROOT)
    assert report.artifacts_validated == 7
    assert report.checksums_verified == 8


def test_preflight_detects_artifact_tampering(tmp_path: Path) -> None:
    for directory in ("schemas", "inputs", "configs", "runs"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
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
