from pathlib import Path

import pytest

from mcx_project.surrogate_1070 import (
    ANALYSIS,
    BASIS_PLAN,
    CONVERGENCE,
    CONVERGENCE_EXTENSION,
    GEOMETRY,
    TEMPLATE,
    build_surrogate_1070,
    freeze_surrogate_basis_plan,
)
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]


def test_surrogate_scaffold_is_fresh_and_explicitly_nonhardware() -> None:
    report = build_surrogate_1070(ROOT, check=True)
    assert report["status"] == "valid"
    assert report["production_eligible"] is False
    assert report["emitters"] == 277

    geometry = load_json(ROOT / GEOMETRY)
    assert geometry["expected_emitter_count"] == len(geometry["emitters"]) == 277
    assert len({row["emitter_id"] for row in geometry["emitters"]}) == 277
    assert {row["wavelength_peak_nm"] for row in geometry["emitters"]} == {1070.0}
    assert all("not target helmet" in row["provenance"] for row in geometry["emitters"])

    manifest = load_json(ROOT / TEMPLATE)
    assert manifest["scientific_status"] == "provisional"


def test_weighting_policies_and_regional_protocol_are_frozen() -> None:
    analysis = load_json(ROOT / ANALYSIS)
    weights = {row["policy"]: row for row in analysis["source_weighting"]}
    assert weights["constant_per_emitter"]["total_weight"] == 277
    assert weights["constant_total"]["total_weight"] == 1
    assert weights["constant_total"]["per_emitter_weight"] == pytest.approx(1 / 277)

    protocol = load_json(ROOT / CONVERGENCE)
    assert protocol["photon_counts"] == [100_000, 1_000_000, 10_000_000]
    assert protocol["replicates_per_count"] == 3
    assert set(protocol["regional_emitter_ids"]) == {
        "superior", "anterior", "posterior", "left_temporal", "right_temporal"
    }
    assert len(set(protocol["regional_emitter_ids"].values())) == 5

    extension = load_json(ROOT / CONVERGENCE_EXTENSION)
    assert extension["photon_counts"][-1] == 100_000_000
    assert extension["candidate_full_basis_photon_count"] == 100_000_000
    assert extension["prior_results_path"].endswith("regional_convergence_v1/results.json")


def test_full_basis_plan_is_frozen_from_the_passing_extension() -> None:
    report = freeze_surrogate_basis_plan(ROOT, check=True)
    assert report["status"] == "frozen_after_regional_convergence"
    plan = load_json(ROOT / BASIS_PLAN)
    assert plan["emitter_ids"] == "enabled"
    assert plan["photon_count"] == 100_000_000
    assert plan["scientific_status"] == "provisional"
