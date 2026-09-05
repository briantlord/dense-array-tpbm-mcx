import shutil
import json
from pathlib import Path

import numpy as np
import pytest

from mcx_project.basis import (
    BasisExecutionError,
    BasisPreparationError,
    deterministic_seed,
    execute_basis_run,
    prepare_basis_plan,
)
from mcx_project.preflight import preflight_manifest
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
TEST_IDENTITY = {"engine_version": "v2025.10", "executable_sha256": "1" * 64,
                 "gpu": "Apple M4 Pro", "selected_device": 1}


def _project_copy(tmp_path: Path) -> Path:
    for directory in ("schemas", "inputs/synthetic_test_only"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    (tmp_path / "configs").mkdir()
    for name in (
        "synthetic_analysis_v1.json",
        "synthetic_smoke_opencl_v1.json",
        "synthetic_basis_plan_v1.json",
    ):
        shutil.copy2(ROOT / "configs" / name, tmp_path / "configs" / name)
    shutil.copytree(
        ROOT / "runs/synthetic_smoke_m4pro",
        tmp_path / "runs/synthetic_smoke_m4pro",
    )
    plan_path = tmp_path / "configs/synthetic_basis_plan_v1.json"
    plan = load_json(plan_path)
    plan["engine_build"] = "synthetic test fixture; executable_sha256=" + "1" * 64
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    return tmp_path


def test_deterministic_seeds_are_stable_distinct_and_signed_int32_safe() -> None:
    first = deterministic_seed("basis_v1", "SYN001", 1)
    assert first == deterministic_seed("basis_v1", "SYN001", 1)
    assert first != deterministic_seed("basis_v1", "SYN001", 2)
    assert first != deterministic_seed("basis_v1", "SYN002", 1)
    assert 1 <= first <= 2**31 - 1


def test_prepare_basis_is_idempotent_and_emits_one_manifest_per_run(
    tmp_path: Path,
) -> None:
    project = _project_copy(tmp_path)
    plan = project / "configs/synthetic_basis_plan_v1.json"
    first = prepare_basis_plan(plan, project)
    second = prepare_basis_plan(plan, project)

    assert first == second
    assert len(first["runs"]) == 4
    assert len({run["seed"] for run in first["runs"]}) == 4
    assert len({run["run_id"] for run in first["runs"]}) == 4
    for run in first["runs"]:
        report = preflight_manifest(project / run["manifest_path"], project)
        assert report.run_id == run["run_id"]
        manifest = load_json(project / run["manifest_path"])
        assert manifest["stage"] == "pilot"
        assert manifest["engine"]["binding"] == "mcxcl_cli"
        assert "unit launched-energy" in manifest["source"]["normalization"]


def test_prepare_refuses_to_replace_changed_generated_config(tmp_path: Path) -> None:
    project = _project_copy(tmp_path)
    plan = project / "configs/synthetic_basis_plan_v1.json"
    index = prepare_basis_plan(plan, project)
    generated = project / index["runs"][0]["configuration_path"]
    generated.write_text("{}\n", encoding="utf-8")

    with pytest.raises(BasisPreparationError, match="immutable file"):
        prepare_basis_plan(plan, project)


def test_execute_is_atomic_and_skips_verified_complete_run(tmp_path: Path) -> None:
    project = _project_copy(tmp_path)
    index = prepare_basis_plan(
        project / "configs/synthetic_basis_plan_v1.json", project
    )
    manifest_path = project / index["runs"][0]["manifest_path"]
    calls = 0

    def executor(config, _run_directory):
        nonlocal calls
        calls += 1
        field = np.full((60, 60, 60, 1), float(config["seed"] % 13 + 1))
        return field, {"backend": "test", "seed": config["seed"], **TEST_IDENTITY}

    assert execute_basis_run(manifest_path, project, executor, engine_probe=lambda: TEST_IDENTITY) == "complete"
    assert calls == 1
    assert not (manifest_path.parent / "run.lock").exists()
    manifest = load_json(manifest_path)
    assert manifest["status"] == "complete"
    assert len(manifest["outputs"]) == 3
    preflight_manifest(manifest_path, project)

    assert execute_basis_run(manifest_path, project, executor) == "skipped"
    assert calls == 1


def test_failed_run_is_recorded_and_requires_a_new_run_id(tmp_path: Path) -> None:
    project = _project_copy(tmp_path)
    index = prepare_basis_plan(
        project / "configs/synthetic_basis_plan_v1.json", project
    )
    manifest_path = project / index["runs"][1]["manifest_path"]

    def executor(_config, _run_directory):
        raise RuntimeError("synthetic executor failure")

    with pytest.raises(BasisExecutionError, match="synthetic executor failure"):
        execute_basis_run(manifest_path, project, executor, engine_probe=lambda: TEST_IDENTITY)
    assert not (manifest_path.parent / "run.lock").exists()
    assert (manifest_path.parent / "failure.json").is_file()
    manifest = load_json(manifest_path)
    assert manifest["status"] == "failed"
    assert "synthetic executor failure" in manifest["error"]
    preflight_manifest(manifest_path, project)

    with pytest.raises(BasisExecutionError, match="new run ID"):
        execute_basis_run(manifest_path, project, executor)


def test_execution_honors_exclusive_run_lock(tmp_path: Path) -> None:
    project = _project_copy(tmp_path)
    index = prepare_basis_plan(
        project / "configs/synthetic_basis_plan_v1.json", project
    )
    manifest_path = project / index["runs"][0]["manifest_path"]
    (manifest_path.parent / "run.lock").write_text("occupied\n", encoding="utf-8")

    with pytest.raises(BasisExecutionError, match="run is locked"):
        execute_basis_run(
            manifest_path,
            project,
            lambda _config, _run_directory: (np.ones((60, 60, 60, 1)), {}),
        )


def test_wrong_engine_is_blocked_before_executor_and_recorded_after_executor(tmp_path):
    project = _project_copy(tmp_path)
    index = prepare_basis_plan(project / "configs/synthetic_basis_plan_v1.json", project)
    manifest_path = project / index["runs"][0]["manifest_path"]
    wrong = {**TEST_IDENTITY, "executable_sha256": "0" * 64}
    def must_not_launch(*args):
        pytest.fail("mismatched engine reached executor")
    with pytest.raises(BasisExecutionError, match="checksum"):
        execute_basis_run(manifest_path, project, must_not_launch, engine_probe=lambda: wrong)
    assert load_json(manifest_path)["status"] == "planned"
    assert not (manifest_path.parent / "fluence.npy").exists()
    with pytest.raises(BasisExecutionError, match="checksum"):
        execute_basis_run(manifest_path, project,
            lambda *_: (np.ones((60,60,60,1)), wrong), engine_probe=lambda: TEST_IDENTITY)
    assert load_json(manifest_path)["status"] == "failed"
    assert not (manifest_path.parent / "fluence.npy").exists()
