from pathlib import Path

from mcx_project.hashing import sha256_file
from mcx_project.validation import load_json, validate_json


ROOT = Path(__file__).resolve().parents[1]


def test_postprocessing_protocol_is_versioned_without_mutating_bound_v1() -> None:
    bound = ROOT / "configs/surrogate_yue277_1070_v1_analysis.json"
    post = ROOT / "configs/surrogate_yue277_1070_v1_analysis_v2.json"
    manifest = load_json(
        ROOT
        / "runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1/"
        "sur1070_001/r001/manifest.json"
    )
    assert manifest["inputs"]["analysis_configuration"]["sha256"] == sha256_file(bound)
    validate_json(
        ROOT / "schemas/analysis_configuration.schema.json",
        post,
        require_complete=True,
    )
    config = load_json(post)
    assert config["analysis_id"].endswith("_v2")
    assert config["reference_protocol"]["reference_emitter_id"] == "SUR1070_275"


def test_windows_aggregate_equivalence_protocol_is_prespecified() -> None:
    protocol = load_json(
        ROOT
        / "configs/surrogate_yue277_1070_windows_rtx3080ti_aggregate_equivalence_v1.json"
    )
    assert protocol["source_emitter_ids"] == ["SUR1070_011", "SUR1070_031"]
    assert protocol["direct_total_photons"] == 200_000_000
    assert protocol["direct_normalization_correction"] == 2.0
    assert protocol["acceptance"] == {
        "maximum_tissue_integral_relative_error": 0.05,
        "median_axis_profile_relative_error": 0.10,
        "median_valid_voxel_relative_error": 0.10,
    }
