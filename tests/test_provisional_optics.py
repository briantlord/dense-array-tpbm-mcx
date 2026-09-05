import json
from pathlib import Path

import pytest

from mcx_project.preflight import validate_optical_scientific_status
from mcx_project.provisional_optics import build_provisional_optics
from mcx_project.validation import InputValidationError, load_json, validate_json


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_ROOT = ROOT / "inputs/optical_properties/provisional_1070_v1"
CENTRAL = SCENARIO_ROOT / "central.json"
MANIFEST = SCENARIO_ROOT / "scenario_set_manifest.json"
OPTICAL_SCHEMA = ROOT / "schemas/optical_properties.schema.json"
MANIFEST_SCHEMA = ROOT / "schemas/optical_scenario_set.schema.json"
PARAMETER_FIELDS = {"mua_mm-1", "mus_mm-1", "source_musp_mm-1", "g", "n"}


def _by_id(scenario: dict) -> dict[int, dict]:
    return {row["tissue_id"]: row for row in scenario["tissues"]}


def test_generated_provisional_scenario_set_is_fresh_and_schema_valid() -> None:
    report = build_provisional_optics(ROOT, check=True)
    assert report == {
        "central": "inputs/optical_properties/provisional_1070_v1/central.json",
        "mode": "check",
        "production_eligible": False,
        "scenario_set_id": "provisional_1070_v1",
        "status": "valid",
        "variants": 14,
    }

    validate_json(MANIFEST_SCHEMA, MANIFEST, require_complete=True)
    manifest = load_json(MANIFEST)
    assert manifest["variant_count"] == len(manifest["variants"]) == 14
    for relative in [manifest["central_path"], *(row["path"] for row in manifest["variants"])]:
        validate_json(OPTICAL_SCHEMA, ROOT / relative, require_complete=True)


def test_provisional_central_is_runnable_but_never_production_labeled() -> None:
    central = load_json(CENTRAL)
    anatomy = load_json(
        ROOT
        / "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/anatomy_metadata.json"
    )
    assert central["scientific_status"] == "provisional"
    assert central["synthetic_test_only"] is False
    assert central["wavelength_nm"] == 1070
    assert [row["tissue_id"] for row in central["tissues"]] == [
        row["id"] for row in anatomy["labels"]
    ]
    assert all(row["source_kind"] == "assumption" for row in central["tissues"])
    assert all(row["review_status"] == "single_reviewed" for row in central["tissues"])
    assert "TBD" not in json.dumps(central)

    with pytest.raises(InputValidationError, match="scientific statuses"):
        validate_optical_scientific_status(
            {"scientific_status": "production"}, central
        )
    validate_optical_scientific_status({"scientific_status": "provisional"}, central)


def test_central_mus_is_derived_from_saved_musp_and_g() -> None:
    central = load_json(CENTRAL)
    for row in central["tissues"]:
        if row["source_musp_mm-1"] == "not_used":
            assert row["tissue_id"] == 0
            assert row["mus_mm-1"] == 0
            continue
        assert row["mus_mm-1"] == pytest.approx(
            row["source_musp_mm-1"] / (1 - row["g"])
        )


def test_variants_change_only_declared_optical_parameters() -> None:
    central = _by_id(load_json(CENTRAL))
    manifest = load_json(MANIFEST)
    for metadata in manifest["variants"]:
        variant = load_json(ROOT / metadata["path"])
        assert variant["scientific_status"] == "provisional"
        assert variant["scenario_id"] == metadata["scenario_id"]
        observed_changes: dict[int, set[str]] = {}
        for tissue_id, row in _by_id(variant).items():
            changed = {
                field
                for field in PARAMETER_FIELDS
                if row[field] != central[tissue_id][field]
            }
            if changed:
                observed_changes[tissue_id] = changed
        assert set(observed_changes) == set(metadata["changed_tissue_ids"])
        assert set().union(*observed_changes.values()) == set(metadata["changed_fields"])


def test_neighboring_1064_sensitivity_remains_an_assumption() -> None:
    scenario = load_json(
        SCENARIO_ROOT / "sensitivities/fat_low_abs_1064.json"
    )
    for tissue_id in (4, 9):
        row = _by_id(scenario)[tissue_id]
        assert row["mua_mm-1"] == pytest.approx(0.0054)
        assert row["source_kind"] == "assumption"
        assert row["source_wavelengths_nm"] == [1064.0, 1070.0]
        assert "not represented as a measured 1070-nm value" in row["notes"]


def test_central_field_provenance_resolves_to_ledger_records() -> None:
    manifest = load_json(MANIFEST)
    ledger = load_json(ROOT / "literature/optical_properties_1070_source_ledger.json")
    ledger_ids = {row["record_id"] for row in ledger["evidence_records"]}
    central_ids = {row["tissue_id"] for row in load_json(CENTRAL)["tissues"]}
    assert {row["tissue_id"] for row in manifest["field_provenance"]} == central_ids
    for row in manifest["field_provenance"]:
        for field in ("mua", "musp", "g", "n"):
            assert set(row[field]) <= ledger_ids


def test_production_template_remains_independently_blocked() -> None:
    production = load_json(
        ROOT / "inputs/optical_properties/production_1070_tbd.json"
    )
    assert production["scenario_id"] == "nominal_1070_v1"
    for row in production["tissues"]:
        assert all(
            row[field] == "TBD"
            for field in ("mua_mm-1", "mus_mm-1", "source_musp_mm-1", "g", "n")
        )
