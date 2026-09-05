#!/usr/bin/env python3
"""Generate the frozen two-pass Yue figure digitization ledger."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from mcx_project.hashing import sha256_file


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = Path("references/papers/Yue_Humayun_2015_distributed_NIR_emitter_array.pdf")
CSV_PATH = Path("literature/yue2015_figure_digitization_v1.csv")
MANIFEST_PATH = Path("benchmarks/yue2015_approx_v1/digitization_manifest_v1.json")


CALIBRATIONS = {
    "fig2b": {
        "image_object": {"pdf_page": 5, "width_px": 1339, "height_px": 629},
        "x_axis": {
            "quantity": "penetration_depth_mm",
            "pass_1": [[846.0, 0.0], [1315.0, 120.0]],
            "pass_2": [[845.0, 0.0], [1314.0, 120.0]],
        },
        "y_axis": {
            "quantity": "log10_normalized_photon_flux",
            "scale": "log10",
            "pass_1": [[5.0, 0.0], [545.0, -12.0]],
            "pass_2": [[4.0, 0.0], [546.0, -12.0]],
        },
    },
    "fig4": {
        "image_object": {"pdf_page": 7, "width_px": 846, "height_px": 725},
        "x_axis": {
            "quantity": "penetration_depth_mm",
            "pass_1": [[163.0, 0.0], [734.0, 100.0]],
            "pass_2": [[164.0, 0.0], [733.0, 100.0]],
        },
        "y_axis": {
            "quantity": "gain",
            "scale": "linear",
            "pass_1": [[621.0, 0.0], [67.0, 100.0]],
            "pass_2": [[620.0, 0.0], [68.0, 100.0]],
        },
    },
    "fig5a": {
        "image_object": {"pdf_page": 7, "width_px": 1455, "height_px": 655},
        "x_axis": {
            "quantity": "penetration_depth_mm",
            "pass_1": [[119.0, 0.0], [521.0, 80.0]],
            "pass_2": [[118.0, 0.0], [522.0, 80.0]],
        },
        "y_axis": {
            "quantity": "gain",
            "scale": "linear",
            "pass_1": [[512.0, 0.0], [85.0, 45.0]],
            "pass_2": [[513.0, 0.0], [84.0, 45.0]],
        },
    },
    "fig5b": {
        "image_object": {"pdf_page": 7, "width_px": 1455, "height_px": 655},
        "x_axis": {
            "quantity": "number_of_sources",
            "pass_1": [[853.0, 1.0], [1405.0, 277.0]],
            "pass_2": [[852.0, 1.0], [1406.0, 277.0]],
        },
        "y_axis": {
            "quantity": "flux_uniformity_sd_over_mean",
            "scale": "linear",
            "pass_1": [[554.0, 0.0], [44.0, 50.0]],
            "pass_2": [[553.0, 0.0], [45.0, 50.0]],
        },
    },
    "fig6c": {
        "image_object": {"pdf_page": 7, "width_px": 1000, "height_px": 823},
        "x_axis": {
            "quantity": "penetration_depth_mm",
            "pass_1": [[204.0, 0.0], [831.0, 100.0]],
            "pass_2": [[203.0, 0.0], [832.0, 100.0]],
        },
        "y_axis": {
            "quantity": "gain",
            "scale": "linear",
            "pass_1": [[763.0, 0.0], [497.0, 120.0]],
            "pass_2": [[762.0, 0.0], [496.0, 120.0]],
        },
    },
}


POINTS = [
    # Figure 2b: the five regional curves at the prespecified 60-mm headline depth.
    ("fig2b", "frontal_open_square", 60.0, 247.5, 248.0, "regional profile"),
    ("fig2b", "north_pole_filled_square", 60.0, 271.5, 271.0, "regional profile"),
    ("fig2b", "parietal_filled_circle", 60.0, 290.3, 291.0, "regional profile"),
    ("fig2b", "temporal_open_triangle", 60.0, 315.9, 316.0, "regional profile"),
    ("fig2b", "occipital_open_circle", 60.0, 327.1, 327.0, "regional profile"),
    # Figure 4: pencil-beam multisource/single-source gain diamonds.
    *[
        ("fig4", "pencil_gain", depth, y1, y2, "blue diamond")
        for depth, y1, y2 in zip(
            range(0, 101, 10),
            [614.0, 614.0, 608.0, 594.0, 577.0, 560.0, 534.0, 504.0, 441.0, 319.5, 75.0],
            [614.0, 613.0, 608.0, 594.0, 578.0, 560.0, 534.0, 503.0, 442.0, 320.0, 76.0],
            strict=True,
        )
    ],
    # Figure 5a: all six source-density gain curves at the 60-mm headline depth.
    ("fig5a", "277_sources_star", 60.0, 378.5, 379.0, "source-density curve"),
    ("fig5a", "229_sources_diamond", 60.0, 396.9, 397.0, "source-density curve"),
    ("fig5a", "181_sources_down_triangle", 60.0, 407.3, 407.0, "source-density curve"),
    ("fig5a", "105_sources_up_triangle", 60.0, 454.0, 454.0, "source-density curve"),
    ("fig5a", "53_sources_circle", 60.0, 483.8, 484.0, "source-density curve"),
    ("fig5a", "13_sources_square", 60.0, 501.0, 501.0, "source-density curve"),
    # Figure 5b includes the one-source reference plus the six reported density tiers.
    *[
        ("fig5b", "uniformity", float(sources), y1, y2, "open circle")
        for sources, y1, y2 in [
            (1, 75.5, 76.0),
            (13, 368.9, 369.0),
            (53, 459.4, 459.0),
            (105, 485.6, 486.0),
            (181, 499.9, 500.0),
            (229, 506.6, 507.0),
            (277, 510.3, 510.0),
        ]
    ],
    # Figure 6c: 690-nm multisource/single-source gain diamonds.
    *[
        ("fig6c", "gain_690nm", depth, y1, y2, "blue diamond")
        for depth, y1, y2 in [
            (0, 759.0, 759.0),
            (10, 759.0, 758.0),
            (20, 758.0, 758.0),
            (30, 752.0, 752.0),
            (40, 742.0, 741.0),
            (50, 734.0, 734.0),
            (60, 726.0, 727.0),
            (70, 700.0, 700.0),
            (80, 670.0, 670.0),
            (100, 501.0, 502.0),
        ]
    ],
]


def _calibrate(pixel: float, endpoints: list[list[float]]) -> float:
    (pixel_0, value_0), (pixel_1, value_1) = endpoints
    return value_0 + (pixel - pixel_0) * (value_1 - value_0) / (pixel_1 - pixel_0)


def _one_pixel_resolution(endpoints: list[list[float]]) -> float:
    (pixel_0, value_0), (pixel_1, value_1) = endpoints
    return abs((value_1 - value_0) / (pixel_1 - pixel_0))


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for figure, series, x_value, pixel_1, pixel_2, marker in POINTS:
        calibration = CALIBRATIONS[figure]
        y_axis = calibration["y_axis"]
        value_1 = _calibrate(pixel_1, y_axis["pass_1"])
        value_2 = _calibrate(pixel_2, y_axis["pass_2"])
        mean_axis_value = (value_1 + value_2) / 2.0
        pixel_resolution = max(
            _one_pixel_resolution(y_axis["pass_1"]),
            _one_pixel_resolution(y_axis["pass_2"]),
        )
        uncertainty_axis = math.hypot(
            abs(value_1 - value_2) / 2.0, pixel_resolution
        )
        if y_axis["scale"] == "log10":
            y_value = 10.0**mean_axis_value
            y_lower = 10.0 ** (mean_axis_value - uncertainty_axis)
            y_upper = 10.0 ** (mean_axis_value + uncertainty_axis)
            uncertainty_kind = "log10_half_repeat_plus_one_pixel"
        else:
            y_value = mean_axis_value
            y_lower = max(0.0, mean_axis_value - uncertainty_axis)
            y_upper = mean_axis_value + uncertainty_axis
            uncertainty_kind = "linear_half_repeat_plus_one_pixel"
        rows.append(
            {
                "figure_panel": figure,
                "marker": marker,
                "pass_1_axis_value": value_1,
                "pass_1_pixel_y": pixel_1,
                "pass_2_axis_value": value_2,
                "pass_2_pixel_y": pixel_2,
                "series": series,
                "uncertainty_axis_units": uncertainty_axis,
                "uncertainty_kind": uncertainty_kind,
                "x_quantity": calibration["x_axis"]["quantity"],
                "x_value": x_value,
                "y_lower": y_lower,
                "y_quantity": y_axis["quantity"],
                "y_upper": y_upper,
                "y_value": y_value,
            }
        )
    return rows


def main() -> None:
    rows = build_rows()
    csv_path = ROOT / CSV_PATH
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "calibrations": CALIBRATIONS,
        "digitization_id": "yue2015_figures_2b_4_5a_5b_6c_v1",
        "digitization_rule": (
            "Two separate pixel-center and two-point axis calibrations on the "
            "publisher's embedded 300-ppi figure objects. Point uncertainty combines "
            "half the between-pass axis-value difference and one-pixel axis resolution "
            "in quadrature."
        ),
        "figures": ["2b", "4", "5a", "5b", "6c"],
        "generation_script": "scripts/digitize_yue_figures.py",
        "output_csv": CSV_PATH.as_posix(),
        "output_csv_sha256": sha256_file(csv_path),
        "pdf_path": PDF_PATH.as_posix(),
        "pdf_sha256": sha256_file(ROOT / PDF_PATH),
        "point_count": len(rows),
        "review_status": "single_operator_two_pass_complete",
        "scientific_status": "benchmark_digitization",
        "source_extraction": (
            "Poppler pdfimages extraction of embedded page-5/page-7 figure objects; "
            "temporary PNGs are not project evidence and are not committed."
        ),
        "status_note": (
            "Digitized points are paper-comparison targets with image-resolution "
            "uncertainty, not source numerical data supplied by the authors."
        ),
    }
    manifest_path = ROOT / MANIFEST_PATH
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "digitization_id": manifest["digitization_id"],
                "output": CSV_PATH.as_posix(),
                "points": len(rows),
                "status": "complete",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
