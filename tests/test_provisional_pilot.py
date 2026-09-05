from pathlib import Path

from mcx_project.preflight import preflight_manifest
from mcx_project.provisional_pilot import (
    OUTPUT_GEOMETRY_PATH,
    OUTPUT_PLAN_PATH,
    OUTPUT_TEMPLATE_PATH,
    _engine_properties,
    build_provisional_pilot,
    select_representative_emitters,
)
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]


def test_representative_selection_is_deterministic_and_regional() -> None:
    donor = load_json(
        ROOT / "inputs/emitters/yue2015_approx_v1/emitter_geometry.json"
    )
    selected = select_representative_emitters(donor)
    assert [(region, output_id, row["emitter_id"]) for region, output_id, row in selected] == [
        ("superior", "P1070_SUPERIOR", "YUE275"),
        ("anterior", "P1070_ANTERIOR", "YUE011"),
        ("posterior", "P1070_POSTERIOR", "YUE031"),
        ("left_temporal", "P1070_LEFT_TEMPORAL", "YUE022"),
        ("right_temporal", "P1070_RIGHT_TEMPORAL", "YUE040"),
    ]


def test_sparse_colin_labels_create_an_inert_medium_8_row() -> None:
    optical = load_json(
        ROOT / "inputs/optical_properties/provisional_1070_v1/central.json"
    )
    properties = _engine_properties(optical)
    assert len(properties) == 13
    assert properties[8] == [0.0, 0.0, 1.0, 1.0]
    assert properties[9][0] == 0.103
    assert properties[12][0] > 0


def test_generated_pilot_is_fresh_preflighted_and_nonproduction() -> None:
    report = build_provisional_pilot(ROOT, check=True)
    assert report["status"] == "valid"
    assert report["scientific_status"] == "provisional"
    assert report["production_eligible"] is False
    assert report["emitters"] == 5

    geometry = load_json(ROOT / OUTPUT_GEOMETRY_PATH)
    assert geometry["expected_emitter_count"] == 5
    assert {row["wavelength_peak_nm"] for row in geometry["emitters"]} == {1070.0}
    assert all("not target helmet geometry" in row["provenance"] for row in geometry["emitters"])

    manifest = load_json(ROOT / OUTPUT_TEMPLATE_PATH)
    plan = load_json(ROOT / OUTPUT_PLAN_PATH)
    assert manifest["stage"] == "pilot"
    assert manifest["scientific_status"] == plan["scientific_status"] == "provisional"
    assert plan["photon_count"] == 100_000
    assert len(plan["emitter_ids"]) == 5
    preflight_manifest(ROOT / OUTPUT_TEMPLATE_PATH, ROOT)
