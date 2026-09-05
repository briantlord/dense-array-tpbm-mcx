#!/usr/bin/env python3
"""Summarize the targeted 810-nm dura and marrow sensitivity experiment."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("results/surrogate_yue277_810_dura_marrow_sensitivity_analysis_v2")
CASES = {
    "refined_primary": {
        "axis": "primary",
        "path": Path("results/surrogate_yue277_810_targeted_dura_marrow_refined_v2"),
    },
    "marrow_skull_like": {
        "axis": "marrow",
        "path": Path("results/surrogate_yue277_810_targeted_marrow_skull_like_v2"),
    },
    "marrow_trabecular": {
        "axis": "marrow",
        "path": Path("results/surrogate_yue277_810_targeted_marrow_trabecular_v2"),
    },
    "dura_skull_like": {
        "axis": "dura",
        "path": Path("results/surrogate_yue277_810_targeted_dura_skull_like_v2"),
    },
}
STAGES = [
    "reached_skull_complex",
    "reached_intracranial_compartment",
    "reached_brain_parenchyma",
    "reached_white_matter",
]


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def max_closure_error(case_dir: Path) -> float:
    errors = []
    for result_path in case_dir.glob("*/r*/result.json"):
        row = load(result_path)
        errors.append(
            abs(
                float(row["energy_output_total_percent"])
                - float(row["log_absorbed_energy_percent"])
            )
        )
    if not errors:
        raise ValueError(f"no replicate results found in {case_dir}")
    return max(errors)


def main() -> None:
    output = ROOT / OUTPUT
    output.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    inputs: dict[str, str] = {}

    for case, metadata in CASES.items():
        case_dir = ROOT / metadata["path"]
        result_path = case_dir / "result.json"
        result = load(result_path)
        inputs[metadata["path"].joinpath("result.json").as_posix()] = sha256(result_path)
        retention = {row["stage"]: row for row in result["retention"]}
        summaries = result["stage_summaries"]
        row: dict[str, Any] = {
            "case": case,
            "axis": metadata["axis"],
            "scenario_id": result["optical_properties"]["scenario_id"],
            "max_energy_closure_error_percentage_points": max_closure_error(case_dir),
        }
        for stage in STAGES:
            if stage not in retention:
                row[f"{stage}_percent_launched"] = None
                row[f"{stage}_relative_sd_percent"] = None
                continue
            row[f"{stage}_percent_launched"] = retention[stage][
                "fraction_of_launched_energy_percent"
            ]
            row[f"{stage}_relative_sd_percent"] = (
                100.0 * summaries[stage]["relative_standard_deviation"]
            )
        rows.append(row)

    primary = next(row for row in rows if row["case"] == "refined_primary")
    for row in rows:
        for stage in STAGES[1:]:
            key = f"{stage}_percent_launched"
            value = row[key]
            row[f"{stage}_change_vs_primary_percent"] = (
                100.0 * (value / primary[key] - 1.0) if value is not None else None
            )

    csv_path = output / "comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = {
        "analysis_id": "surrogate_yue277_810_dura_marrow_sensitivity_analysis_v2",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "inputs": inputs,
        "rows": rows,
        "interpretation": {
            "primary": "in-vivo-first skull, exact-810 Shapey dura, exact-810 Kothuri frozen tibial marrow",
            "marrow_axis": "label 11 only; Shapey dura and all other media fixed",
            "dura_axis": "label 10 only; Kothuri frozen marrow and all other media fixed",
            "intracranial_dura_limit": "dura is part of the intracranial tally surface, so dura sensitivity is evaluated only at brain and white matter",
            "denominator": "normalized energy launched by the 277 in-model sources",
        },
        "scientific_status": "provisional_810_refined_dura_marrow_yue_spatial_surrogate_not_target_hardware_not_measured_dose_not_biological_efficacy",
    }
    (output / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    report = [
        "# Targeted 810-nm dura and marrow sensitivity",
        "",
        "The refined primary uses Shapey's exact-810 post-mortem human dura row and Kothuri's exact-810 frozen human tibial-marrow row. Sensitivities change one atlas tissue at a time.",
        "",
        "| Case | Intracranial (% launched) | Brain (% launched) | White matter (% launched) | Brain change vs primary | White-matter change vs primary |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        def fmt(key: str, digits: int = 4) -> str:
            value = row[key]
            return "not run" if value is None else f"{value:.{digits}f}%"

        def change(key: str) -> str:
            value = row[key]
            return "not run" if value is None else f"{value:+.1f}%"

        report.append(
            f"| {row['case']} | {fmt('reached_intracranial_compartment_percent_launched')} | "
            f"{fmt('reached_brain_parenchyma_percent_launched')} | "
            f"{fmt('reached_white_matter_percent_launched')} | "
            f"{change('reached_brain_parenchyma_change_vs_primary_percent')} | "
            f"{change('reached_white_matter_change_vs_primary_percent')} |"
        )
    report.extend(
        [
            "",
            "Marrow is the larger uncertainty axis: the skull-like and trabecular endpoints bracket brain entry from about -9.7% to +10.8% around the frozen-marrow primary. The older skull-like dura proxy raises brain entry by about 2.5% and white-matter entry by about 3.1% relative to the Shapey dura row.",
            "",
            "These are first-entry energy tallies, not absorption fractions. They do not distinguish absorption from backscatter or escape before reaching the requested target.",
            "",
            "The primary remains provisional because neither source is living cranial tissue: Shapey is one post-mortem donor and Kothuri is frozen tibial marrow from one elderly donor with reported boundary effects.",
        ]
    )
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
