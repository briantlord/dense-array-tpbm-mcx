import importlib.util
from pathlib import Path

from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]


def test_report_suppresses_unqualified_ratios_and_keeps_absolute_deposition(tmp_path):
    spec = importlib.util.spec_from_file_location("regional_report", ROOT / "scripts/analyze_regional_absorbed_energy_density.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = load_json(ROOT / "results/surrogate_yue277_810_vs_1070_regional_absorbed_energy_v1/result.json")
    for row in result["comparisons"]:
        row["ratio_qualified"] = False
        row["ratio_810_to_1070"] = None
    module.write_report(tmp_path, result["regional_rows"], result["comparisons"], result["checks"])
    text = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "not qualified" in text
    assert "1054" not in text
    assert "e-08" in text
