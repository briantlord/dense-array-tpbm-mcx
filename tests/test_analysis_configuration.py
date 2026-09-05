import importlib
from pathlib import Path

from mcx_project.provenance import capture_code, resolve_recorded_code


def test_810_entrypoint_does_not_mutate_shared_defaults(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    shared = importlib.import_module("analyze_surrogate_1070_windows_basis")
    before = dict(shared.DEFAULT_SPEC)
    wrapper = importlib.import_module("analyze_surrogate_810_windows_basis")
    assert shared.DEFAULT_SPEC == before
    assert wrapper.SPEC["wavelength_nm"] == 810
    assert shared.DEFAULT_SPEC["wavelength_nm"] == 1070


def test_provenance_records_actual_entrypoint_shared_source_and_arguments(tmp_path):
    entrypoint = tmp_path / "run_810.py"
    shared = tmp_path / "shared.py"
    entrypoint.write_text("import shared\n", encoding="utf-8")
    shared.write_text("value = 810\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("test lock\n", encoding="utf-8")
    record = capture_code(tmp_path, entrypoint, ["--spec", "810.json"], shared=(shared,))
    assert record["entrypoint"] == "run_810.py"
    assert record["arguments"] == ["--spec", "810.json"]
    assert {row["path"] for row in record["sources"]} == {"run_810.py", "shared.py"}
    shared.write_text("value = 1070\n", encoding="utf-8")
    old = next(row for row in record["sources"] if row["path"] == "shared.py")
    assert resolve_recorded_code(tmp_path, old).read_text() == "value = 810\n"
