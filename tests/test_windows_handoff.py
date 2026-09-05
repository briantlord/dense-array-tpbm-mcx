import json
from pathlib import Path

import pytest

from mcx_project.validation import InputValidationError, validate_json
from mcx_project.windows_handoff import (
    RTX3080TI_TARGET,
    build_windows_opencl_payloads,
)
from mcx_project.hashing import sha256_file


ROOT = Path(__file__).resolve().parents[1]


def _probe() -> dict[str, str]:
    return {
        "engine_version": "MCXCL v2025.10",
        "executable": r"C:\mcx\mcxcl.exe",
        "executable_sha256": "a" * 64,
        "device_report": "NVIDIA GeForce RTX 3080",
        "platform": "Windows-11-10.0.26100-SP0",
    }


def test_windows_payloads_are_distinct_and_schema_valid(tmp_path: Path) -> None:
    environment, template, plan = build_windows_opencl_payloads(
        ROOT,
        _probe(),
        code_revision="b" * 40,
        created_at="2026-08-15T12:00:00Z",
    )
    assert environment["device"] == "NVIDIA GeForce RTX 3080"
    assert template["engine"]["gpu"] == "NVIDIA GeForce RTX 3080"
    assert template["engine"]["runtime"].startswith("Windows")
    assert "arm64" not in template["engine"]["build"]
    assert plan["basis_set_id"] == "surrogate_yue277_1070_windows_opencl_basis_v1"
    assert plan["run_root"] != "runs/surrogate_yue277_1070_basis_v1"

    template_path = tmp_path / "template.json"
    plan_path = tmp_path / "plan.json"
    template_path.write_text(json.dumps(template), encoding="utf-8")
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    validate_json(ROOT / "schemas/run_manifest.schema.json", template_path)
    validate_json(
        ROOT / "schemas/basis_plan.schema.json", plan_path, require_complete=True
    )


def test_windows_rtx3080ti_payloads_are_exact_and_versioned(tmp_path: Path) -> None:
    probe = _probe()
    probe["device_report"] = "NVIDIA GeForce RTX 3080 Ti"
    environment, template, plan = build_windows_opencl_payloads(
        ROOT,
        probe,
        code_revision="b" * 40,
        created_at="2026-08-15T12:00:00Z",
        target=RTX3080TI_TARGET,
    )
    assert environment["device"] == "NVIDIA GeForce RTX 3080 Ti"
    assert template["engine"]["gpu"] == "NVIDIA GeForce RTX 3080 Ti"
    assert "rtx3080ti" in plan["basis_set_id"]
    assert plan["run_root"] != "runs/surrogate_yue277_1070_basis_v1"

    template_path = tmp_path / "template.json"
    plan_path = tmp_path / "plan.json"
    template_path.write_text(json.dumps(template), encoding="utf-8")
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    validate_json(ROOT / "schemas/run_manifest.schema.json", template_path)
    validate_json(
        ROOT / "schemas/basis_plan.schema.json", plan_path, require_complete=True
    )


def test_rtx3080_target_refuses_rtx3080ti() -> None:
    probe = _probe()
    probe["device_report"] = "NVIDIA GeForce RTX 3080 Ti"
    with pytest.raises(InputValidationError):
        build_windows_opencl_payloads(
            ROOT,
            probe,
            code_revision="b" * 40,
            created_at="2026-08-15T12:00:00Z",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("engine_version", "MCXCL v2024.2"),
        ("device_report", "NVIDIA GeForce RTX 3070"),
        ("platform", "macOS-15-arm64"),
    ],
)
def test_windows_payload_refuses_wrong_environment(field: str, value: str) -> None:
    probe = _probe()
    probe[field] = value
    with pytest.raises(InputValidationError):
        build_windows_opencl_payloads(
            ROOT,
            probe,
            code_revision="b" * 40,
            created_at="2026-08-15T12:00:00Z",
        )


def test_machine_readable_handoff_checkpoint_hashes_match() -> None:
    state = json.loads(
        (ROOT / "handoff/windows_rtx3080/state.json").read_text(encoding="utf-8")
    )
    for key, value in state["frozen_inputs"].items():
        if not key.endswith("_path"):
            continue
        prefix = key.removesuffix("_path")
        assert sha256_file(ROOT / value) == state["frozen_inputs"][f"{prefix}_sha256"]
    assert state["environment_boundary"]["apple_index_must_not_run_on_windows"]
    assert not state["environment_boundary"]["cuda_backend_ready"]
