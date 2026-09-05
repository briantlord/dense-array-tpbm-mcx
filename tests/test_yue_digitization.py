import csv
from pathlib import Path

import pytest

from mcx_project.hashing import sha256_file
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "literature/yue2015_figure_digitization_v1.csv"
MANIFEST_PATH = (
    ROOT / "benchmarks/yue2015_approx_v1/digitization_manifest_v1.json"
)


def _rows() -> list[dict[str, str]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_digitization_manifest_binds_pdf_and_output() -> None:
    manifest = load_json(MANIFEST_PATH)
    assert manifest["figures"] == ["2b", "4", "5a", "5b", "6c"]
    assert manifest["point_count"] == 39
    assert manifest["review_status"] == "single_operator_two_pass_complete"
    assert manifest["output_csv_sha256"] == sha256_file(CSV_PATH)
    assert manifest["pdf_sha256"] == sha256_file(
        ROOT / manifest["pdf_path"]
    )


def test_digitized_headline_values_match_the_plotted_scale() -> None:
    rows = _rows()

    def value(figure: str, series: str, x_value: float) -> float:
        row = next(
            row
            for row in rows
            if row["figure_panel"] == figure
            and row["series"] == series
            and float(row["x_value"]) == x_value
        )
        assert float(row["y_lower"]) < float(row["y_value"]) < float(row["y_upper"])
        return float(row["y_value"])

    assert value("fig4", "pencil_gain", 40.0) == pytest.approx(7.78, rel=0.02)
    assert value("fig5a", "181_sources_down_triangle", 60.0) == pytest.approx(
        11.08, rel=0.02
    )
    assert value("fig5a", "105_sources_up_triangle", 60.0) == pytest.approx(
        6.15, rel=0.02
    )
    assert value("fig6c", "gain_690nm", 40.0) == pytest.approx(9.47, rel=0.02)


def test_density_gain_and_uniformity_have_reported_ordering() -> None:
    rows = _rows()
    density_gain = [
        row
        for row in rows
        if row["figure_panel"] == "fig5a" and float(row["x_value"]) == 60.0
    ]
    gains = {
        int(row["series"].split("_", maxsplit=1)[0]): float(row["y_value"])
        for row in density_gain
    }
    assert [gains[count] for count in (13, 53, 105, 181, 229, 277)] == sorted(
        gains.values()
    )

    uniformity = [
        float(row["y_value"])
        for row in rows
        if row["figure_panel"] == "fig5b"
    ]
    assert uniformity == sorted(uniformity, reverse=True)
