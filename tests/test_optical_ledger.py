import csv
import json
from pathlib import Path

import numpy as np
import pytest

from mcx_project.optical_ledger import audit_optical_ledger
from mcx_project.validation import InputValidationError, validate_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = PROJECT_ROOT / "literature/optical_properties_1070_source_ledger.json"


def _ledger() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def test_1070_ledger_cross_file_audit_is_valid_but_blocked() -> None:
    report = audit_optical_ledger(PROJECT_ROOT)

    assert report["status"] == "valid_but_blocked"
    assert report["production_launch_allowed"] is False
    assert report["anatomy_labels_covered"] == 12
    assert report["evidence_records"] == 59
    assert report["unresolved_production_cells"] == 60


def test_1070_ledger_covers_native_anatomy_labels_exactly() -> None:
    ledger = _ledger()
    anatomy = json.loads(
        (
            PROJECT_ROOT
            / "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/anatomy_metadata.json"
        ).read_text(encoding="utf-8")
    )

    observed = [
        (row["tissue_id"], row["tissue_name"]) for row in ledger["coverage"]
    ]
    expected = [(row["id"], row["name"]) for row in anatomy["labels"]]
    assert observed == expected


def test_1070_spectral_model_evaluations_preserve_quantity_and_units() -> None:
    records = {row["record_id"]: row for row in _ledger()["evidence_records"]}
    wavelength_nm = 1070.0

    expected_cm = {
        "bashkatov_2005_skin_musp": 73.7 * wavelength_nm**-0.22
        + 1.1e12 * wavelength_nm**-4,
        "bashkatov_2005_fat_musp": 1050.6 * wavelength_nm**-0.68,
        "bashkatov_2006_skull_musp": 1533.02 * wavelength_nm**-0.65,
        "dura_secondary_spectral_model": 5.733e9 * wavelength_nm**-3.286
        + 206.854 * wavelength_nm**-0.439,
    }

    for record_id, expected_original in expected_cm.items():
        record = records[record_id]
        assert record["quantity"] == "musp"
        assert record["original"]["unit"] == "cm^-1"
        np.testing.assert_allclose(record["original"]["value"], expected_original)
        np.testing.assert_allclose(
            record["target_value_1070"], expected_original / 10.0
        )


def test_neighboring_1064_table_does_not_pass_complete_production_gate() -> None:
    production = PROJECT_ROOT / "inputs/optical_properties/production_1070_tbd.json"
    schema = PROJECT_ROOT / "schemas/optical_properties.schema.json"

    validate_json(schema, production)
    with pytest.raises(InputValidationError, match="unresolved TBD values"):
        validate_json(schema, production, require_complete=True)

    cassano = next(
        row
        for row in _ledger()["evidence_records"]
        if row["record_id"] == "cassano_1064_compiled_table"
    )
    assert cassano["evidence_status"] == "neighboring_wavelength_only"
    assert cassano["target_value_1070"] == "TBD"


def test_kothuri_exact_1070_transcription_recomputes_means_and_units() -> None:
    path = (
        PROJECT_ROOT / "literature/kothuri_2025_human_bone_1070_transcription.csv"
    )
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 6
    for row in rows:
        replicates = [
            float(row["replicate_1_cm-1"]),
            float(row["replicate_2_cm-1"]),
            float(row["replicate_3_cm-1"]),
        ]
        mean_cm = sum(replicates) / len(replicates)
        np.testing.assert_allclose(
            float(row["mean_cm-1"]), mean_cm, rtol=1e-8, atol=1e-12
        )
        np.testing.assert_allclose(
            float(row["mean_mm-1"]), mean_cm / 10, rtol=1e-8, atol=1e-12
        )


def test_shapey_exact_1070_transcription_matches_ledger_candidates() -> None:
    path = PROJECT_ROOT / "literature/shapey_2022_1070_transcription.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    expected = {
        "gray_matter": (0.08892, 2.0896383630934898),
        "white_matter": (0.0404, 7.1437578099100403),
        "dura": (0.07021, 2.29157905020713),
    }
    records = {row["record_id"]: row for row in _ledger()["evidence_records"]}

    assert len(rows) == 3
    for row in rows:
        tissue = row["tissue_name"]
        mua, musp = expected[tissue]
        assert float(row["wavelength_nm"]) == 1070
        np.testing.assert_allclose(float(row["mua_revised_mean_mm-1"]), mua)
        np.testing.assert_allclose(float(row["musp_model_fitted_mm-1"]), musp)
        prefix = {"gray_matter": "gm", "white_matter": "wm", "dura": "dura"}[tissue]
        np.testing.assert_allclose(records[f"shapey_2022_{prefix}_mua"]["target_value_1070"], mua)
        np.testing.assert_allclose(records[f"shapey_2022_{prefix}_musp"]["target_value_1070"], musp)

    assert records["shapey_2022_fixed_g_085"]["source_kind"] == "simulation_assumption"
    assert records["shapey_2022_fixed_n_140"]["source_kind"] == "simulation_assumption"


def test_digitized_1070_curves_recompute_from_saved_axis_calibrations() -> None:
    path = PROJECT_ROOT / "literature/digitized_1070_primary_curves.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 7
    for row in rows:
        axis_x_min = float(row["x_axis_min"])
        axis_x_max = float(row["x_axis_max"])
        pixel_x_min = float(row["x_pixel_min"])
        pixel_x_max = float(row["x_pixel_max"])
        selected_x = float(row["selected_x_pixel"])
        wavelength = axis_x_min + (selected_x - pixel_x_min) * (
            axis_x_max - axis_x_min
        ) / (pixel_x_max - pixel_x_min)
        assert wavelength == pytest.approx(1070, abs=1.0)

        axis_y_min = float(row["y_axis_min"])
        axis_y_max = float(row["y_axis_max"])
        pixel_y_min = float(row["y_pixel_min"])
        pixel_y_max = float(row["y_pixel_max"])
        selected_y = float(row["selected_y_pixel"])
        fraction = (pixel_y_min - selected_y) / (pixel_y_min - pixel_y_max)
        if row["y_axis_scale"] == "log10":
            reconstructed = 10 ** (
                np.log10(axis_y_min)
                + fraction * (np.log10(axis_y_max) - np.log10(axis_y_min))
            )
        else:
            reconstructed = axis_y_min + fraction * (axis_y_max - axis_y_min)

        original = float(row["original_value"])
        assert reconstructed == pytest.approx(original, rel=0.02, abs=0.002)
        target = float(row["target_value_1070"])
        if row["original_unit"] == "cm^-1":
            assert target == pytest.approx(original / 10, rel=0.01)
        else:
            assert target == pytest.approx(original)


def test_roggan_curve_states_are_not_reversed() -> None:
    records = {row["record_id"]: row for row in _ledger()["evidence_records"]}
    oxy = records["roggan_1999_blood_mua_oxy_digitized"]
    deoxy = records["roggan_1999_blood_mua_deoxy_digitized"]

    assert oxy["measurement_context"]["state"].startswith("oxygenated")
    assert deoxy["measurement_context"]["state"].startswith("deoxygenated")
    assert oxy["target_value_1070"] == pytest.approx(0.259)
    assert deoxy["target_value_1070"] == pytest.approx(0.190)


def test_new_exact_1070_transcriptions_match_ledger() -> None:
    records = {row["record_id"]: row for row in _ledger()["evidence_records"]}

    with (
        PROJECT_ROOT / "literature/mosca_2020_porcine_muscle_1070_transcription.csv"
    ).open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            np.testing.assert_allclose(
                float(row["mean_mm-1"]), float(row["mean_cm-1"]) / 10
            )
            np.testing.assert_allclose(
                records[row["record_id"]]["target_value_1070"],
                float(row["mean_mm-1"]),
            )

    with (
        PROJECT_ROOT / "literature/damagatla_2026_in_vivo_human_1070_summary.csv"
    ).open(newline="", encoding="utf-8") as stream:
        rows = {row["location"]: row for row in csv.DictReader(stream)}
    upper = rows["Upper_arm"]
    forehead = rows["Forehead"]
    np.testing.assert_allclose(
        records["damagatla_2026_upper_arm_mua"]["target_value_1070"],
        float(upper["mua_mean_cm-1"]) / 10,
    )
    np.testing.assert_allclose(
        records["damagatla_2026_upper_arm_musp"]["target_value_1070"],
        float(upper["musp_mean_cm-1"]) / 10,
    )
    np.testing.assert_allclose(
        records["damagatla_2026_forehead_mua"]["target_value_1070"],
        float(forehead["mua_mean_cm-1"]) / 10,
    )
    np.testing.assert_allclose(
        records["damagatla_2026_forehead_musp"]["target_value_1070"],
        float(forehead["musp_mean_cm-1"]) / 10,
    )


def test_water_proxy_values_recompute() -> None:
    records = {row["record_id"]: row for row in _ledger()["evidence_records"]}
    assert records["hale_querry_1973_water_mua_interp"]["target_value_1070"] == pytest.approx(
        ((0.120 + 0.130) / 2) / 10
    )

    wavelength_um = 1.070
    terms = [
        (5.689093832e-1, 5.110301794e-3),
        (1.719708856e-1, 1.825180155e-2),
        (2.062501582e-2, 2.624158904e-2),
        (1.123965424e-1, 1.067505178e1),
    ]
    expected_n = np.sqrt(
        1
        + sum(
            coefficient * wavelength_um**2 / (wavelength_um**2 - pole)
            for coefficient, pole in terms
        )
    )
    assert records["daimon_masumura_2007_water_n"]["target_value_1070"] == pytest.approx(
        expected_n
    )
    assert records["daimon_masumura_2007_water_n"]["review_status"] == "single_reviewed"


def test_cortese_scm_power_law_is_explicitly_extrapolated() -> None:
    records = {row["record_id"]: row for row in _ledger()["evidence_records"]}
    model = records["cortese_2023_scm_musp_extrap_1070"]
    expected_mm = 8.0 * (1070 / 785) ** (-0.66) / 10

    assert model["source_kind"] == "spectral_model"
    assert model["evidence_status"] == "candidate_spectral_model_1070"
    assert model["target_value_1070"] == pytest.approx(expected_mm)
    assert records["cortese_2023_scm_mua_1050_context"]["target_value_1070"] == "TBD"

    with (
        PROJECT_ROOT / "literature/cortese_2023_scm_1070_transcription.csv"
    ).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6
    for row in rows:
        expected_cm = float(row["A_cm-1_at_785"]) * (1070 / 785) ** (
            -float(row["b"])
        )
        assert float(row["musp_target_cm-1"]) == pytest.approx(expected_cm)
        assert float(row["musp_target_mm-1"]) == pytest.approx(expected_cm / 10)


def test_friebel_1070_digitizations_recompute_from_saved_axes() -> None:
    path = PROJECT_ROOT / "literature/friebel_blood_1070_digitization.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 10
    records = {row["record_id"]: row for row in _ledger()["evidence_records"]}
    ledger_record_ids = {
        "friebel_2006_blood_mua_oxy_hct42",
        "friebel_2006_blood_g_oxy_hct42",
        "friebel_2006_blood_musp_oxy_hct42",
        "friebel_2009_blood_mua_oxy_hct33",
        "friebel_2009_blood_mua_deoxy_hct33",
        "friebel_2009_blood_mus_oxy_hct33",
        "friebel_2009_blood_mus_deoxy_hct33",
        "friebel_2009_blood_g_oxy_deoxy_hct33",
    }

    for row in rows:
        wavelength = float(row["x_axis_min"]) + (
            float(row["selected_x_pixel"]) - float(row["x_pixel_min"])
        ) * (float(row["x_axis_max"]) - float(row["x_axis_min"])) / (
            float(row["x_pixel_max"]) - float(row["x_pixel_min"])
        )
        assert wavelength == pytest.approx(1070, abs=1.0)

        fraction = (
            float(row["y_pixel_min"]) - float(row["selected_y_pixel"])
        ) / (float(row["y_pixel_min"]) - float(row["y_pixel_max"]))
        if row["y_axis_scale"] == "log10":
            reconstructed = 10 ** (
                np.log10(float(row["y_axis_min"]))
                + fraction
                * (
                    np.log10(float(row["y_axis_max"]))
                    - np.log10(float(row["y_axis_min"]))
                )
            )
        else:
            reconstructed = float(row["y_axis_min"]) + fraction * (
                float(row["y_axis_max"]) - float(row["y_axis_min"])
            )
        assert reconstructed == pytest.approx(float(row["target_value_1070"]), rel=1e-8)

        if row["record_id"] in ledger_record_ids:
            assert records[row["record_id"]]["target_value_1070"] == pytest.approx(
                float(row["target_value_1070"])
            )

    assert "friebel_2006_blood_mus_oxy_hct42" not in records


def test_candidate_scenario_matrix_references_only_ledger_records() -> None:
    matrix = json.loads(
        (
            PROJECT_ROOT
            / "literature/optical_properties_1070_candidate_scenarios.json"
        ).read_text(encoding="utf-8")
    )
    ledger_ids = {row["record_id"] for row in _ledger()["evidence_records"]}
    anatomy = json.loads(
        (
            PROJECT_ROOT
            / "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/anatomy_metadata.json"
        ).read_text(encoding="utf-8")
    )

    assert matrix["production_runnable"] is False
    assert [
        (row["tissue_id"], row["tissue_name"])
        for row in matrix["central_candidate"]
    ] == [(row["id"], row["name"]) for row in anatomy["labels"]]
    for row in matrix["central_candidate"]:
        assert set(row["bindings"]) <= ledger_ids
    for axis in matrix["sensitivity_axes"]:
        for case in axis["cases"]:
            assert set(case["bindings"]) <= ledger_ids
