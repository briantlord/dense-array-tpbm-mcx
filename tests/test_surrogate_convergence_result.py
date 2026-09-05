from pathlib import Path

from mcx_project.hashing import sha256_file
from mcx_project.surrogate_1070 import (
    BASIS_PLAN,
    CONVERGENCE,
    CONVERGENCE_EXTENSION,
    GEOMETRY,
)
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "results/surrogate_yue277_1070_v1/regional_convergence_v1/results.json"
V2 = ROOT / "results/surrogate_yue277_1070_v1/regional_convergence_v2/results.json"
INDEX = ROOT / "runs/surrogate_yue277_1070_basis_v1/index.json"


def test_failed_lower_tier_and_passing_extension_are_both_preserved() -> None:
    initial = load_json(V1)
    final = load_json(V2)
    assert initial["candidate_full_basis_photon_count"] == 10_000_000
    assert initial["basis_plan_candidate_ready"] is False
    assert final["candidate_full_basis_photon_count"] == 100_000_000
    assert final["basis_plan_candidate_ready"] is True
    assert initial["protocol_sha256"] == sha256_file(ROOT / CONVERGENCE)
    assert final["protocol_sha256"] == sha256_file(ROOT / CONVERGENCE_EXTENSION)
    assert final["geometry_sha256"] == sha256_file(ROOT / GEOMETRY)
    controlling = [
        row
        for row in final["comparisons"]
        if row["current_photon_count"] == 100_000_000
    ]
    assert len(controlling) == 5
    assert all(row["all_thresholds_pass"] for row in controlling)


def test_prepared_full_basis_matches_the_convergence_decision() -> None:
    plan = load_json(ROOT / BASIS_PLAN)
    index = load_json(INDEX)
    assert plan["photon_count"] == 100_000_000
    assert index["basis_set_id"] == plan["basis_set_id"]
    assert len(index["runs"]) == 277
    assert len({row["emitter_id"] for row in index["runs"]}) == 277
    assert len({row["seed"] for row in index["runs"]}) == 277
