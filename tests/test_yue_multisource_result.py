from pathlib import Path

from mcx_project.hashing import sha256_file
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "benchmarks/yue2015_approx_v1/multisource_1e8_v2"
EQUIVALENCE_RESULT = (
    ROOT / "benchmarks/yue2015_approx_v1/aggregate_equivalence_v1/result.json"
)


def test_multisource_outputs_are_hash_bound_and_keep_the_failed_gate() -> None:
    summary = load_json(RESULT_DIR / "summary.json")
    assert summary["analysis_id"] == "yue2015_850_multisource_1e8_v2"
    assert summary["photon_count_per_source"] == 100_000_000
    assert summary["reference_source"] == "YUE277"
    assert summary["fig4_direct_comparison"]["point_count"] == 11
    assert summary["frozen_acceptance_evaluation"]["profile_spearman_pass"] is True
    assert summary["frozen_acceptance_evaluation"]["density_order_pass"] is True
    assert summary["frozen_acceptance_evaluation"]["headline_relative_error_pass"] is False
    for filename, expected_hash in summary["outputs"].items():
        assert sha256_file(RESULT_DIR / filename) == expected_hash


def test_direct_two_source_aggregate_equivalence_passes() -> None:
    result = load_json(EQUIVALENCE_RESULT)
    assert result["status"] == "pass"
    assert all(result["acceptance_components"].values())
    assert result["metrics"]["maximum_tissue_integral_relative_error"] < 0.001
    assert result["metrics"]["median_axis_profile_relative_error"] < 0.02
    assert result["metrics"]["median_valid_voxel_relative_error"] < 0.01
