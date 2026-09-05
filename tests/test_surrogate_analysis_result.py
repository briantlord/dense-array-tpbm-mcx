from pathlib import Path

from mcx_project.hashing import sha256_file
from mcx_project.provenance import resolve_recorded_code
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = (
    ROOT / "results/surrogate_yue277_1070_windows_rtx3080ti_opencl_analysis_v1"
)
EQUIVALENCE = (
    ROOT
    / "benchmarks/surrogate_yue277_1070_windows_rtx3080ti_opencl/"
    "aggregate_equivalence_v1/result.json"
)


def test_surrogate_analysis_result_is_complete_bounded_and_conditional() -> None:
    result = load_json(RESULT_DIR / "result_summary.json")
    assert result["status"] == "complete"
    assert result["source_count"] == 277
    assert result["aggregation"]["source_stack_materialized"] is False
    assert result["aggregation"]["field_checksum_verified_before_use"] is True
    assert result["reference_protocol"]["reference_emitter_id"] == "SUR1070_275"
    assert "not_target_helmet" in result["scientific_status"]
    for roi in result["roi_results"].values():
        metrics = roi["field_first"]
        assert metrics["ef_dom"] >= 1.0
        assert 0.0 <= metrics["non_dominant_contribution_fraction"] <= 1.0
        assert 1.0 <= metrics["n_eff"] <= 277.0
        assert metrics["ef_ref"] >= 1.0
        assert sum(row["fraction"] for row in metrics["top_contributors"]) <= 1.0


def test_direct_equivalence_passes_every_prespecified_threshold() -> None:
    result = load_json(EQUIVALENCE)
    assert result["status"] == "pass"
    assert all(result["acceptance_components"].values())
    for name, threshold in result["thresholds"].items():
        assert result["metrics"][name] <= threshold


def test_result_manifest_matches_tracked_outputs_and_analyzer() -> None:
    manifest = load_json(RESULT_DIR / "result_manifest.json")
    script = resolve_recorded_code(ROOT, manifest["code"])
    assert manifest["code"]["sha256"] == sha256_file(script)
    tracked_kinds = {"figure", "table", "summary", "report"}
    for output in manifest["outputs"]:
        if output["kind"] in tracked_kinds:
            path = ROOT / output["path"]
            assert output["sha256"] == sha256_file(path)
            assert output["bytes"] == path.stat().st_size
