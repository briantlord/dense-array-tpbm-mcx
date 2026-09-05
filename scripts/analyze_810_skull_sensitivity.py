#!/usr/bin/env python3
"""Summarize the targeted 810-nm skull optical-property comparison."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("inputs/optical_properties/provisional_810_v1/scenario_set_manifest.json")
OUTPUT = Path("results/surrogate_yue277_810_targeted_skull_comparison_v1")
RESULTS = {
    "in_vivo_first": Path("results/surrogate_yue277_810_targeted_skull_in_vivo_v1/result.json"),
    "cassano_high_scatter": Path("results/surrogate_yue277_810_targeted_skull_cassano_v1/result.json"),
    "pitzschke_low_attenuation": Path("results/surrogate_yue277_810_targeted_skull_pitzschke_v1/result.json"),
}


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    output = ROOT / OUTPUT
    output.mkdir(parents=True, exist_ok=False)
    manifest_path = ROOT / MANIFEST
    manifest = load(manifest_path)
    cases = {row["case"]: row for row in manifest["cases"]}
    rows: list[dict[str, Any]] = []
    input_hashes = {MANIFEST.as_posix(): sha256(manifest_path)}

    for case_name, relative_path in RESULTS.items():
        path = ROOT / relative_path
        result = load(path)
        input_hashes[relative_path.as_posix()] = sha256(path)
        retention = {row["stage"]: row for row in result["retention"]}
        skull = retention["reached_skull_complex"]["fraction_of_launched_energy_percent"]
        intracranial = retention["reached_intracranial_compartment"][
            "fraction_of_launched_energy_percent"
        ]
        conditional = 100.0 * intracranial / skull
        evidence = cases[case_name]
        summary = result["stage_summaries"]["reached_intracranial_compartment"]
        mua = float(evidence["skull_mua_mm-1"])
        musp = float(evidence["skull_musp_mm-1"])
        rows.append(
            {
                "case": case_name,
                "scenario_id": evidence["scenario_id"],
                "skull_mua_mm-1": mua,
                "skull_musp_mm-1": musp,
                "diffusion_mueff_mm-1": math.sqrt(3.0 * mua * (mua + musp)),
                "reached_skull_percent_launched": skull,
                "reached_intracranial_percent_launched": intracranial,
                "intracranial_percent_of_skull_reaching": conditional,
                "skull_to_intracranial_attrition_percent": 100.0 - conditional,
                "intracranial_replicate_sd_percentage_points": summary[
                    "standard_deviation_percent_points"
                ],
                "intracranial_relative_sd_percent": 100.0
                * summary["relative_standard_deviation"],
            }
        )

    primary = next(row for row in rows if row["case"] == "in_vivo_first")
    for row in rows:
        row["intracranial_change_vs_primary_percent"] = 100.0 * (
            row["reached_intracranial_percent_launched"]
            / primary["reached_intracranial_percent_launched"]
            - 1.0
        )
        row["conditional_change_vs_primary_percent"] = 100.0 * (
            row["intracranial_percent_of_skull_reaching"]
            / primary["intracranial_percent_of_skull_reaching"]
            - 1.0
        )

    csv_path = output / "comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    result = {
        "analysis_id": "surrogate_yue277_810_targeted_skull_comparison_v1",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "inputs": input_hashes,
        "rows": rows,
        "interpretation": {
            "denominator": "normalized energy launched by the 277 in-model sources",
            "conditional_metric": "intracranial first-entry tally divided by skull-or-marrow first-entry tally from separate matched simulations",
            "attrition_warning": "skull-to-intracranial attrition is not skull absorption alone; it includes absorption and trajectories redirected or escaped before first intracranial entry",
            "isolation": "only skull label 7 changes; all other media, emitter geometry, anatomy, photon counts, and tally definitions are fixed",
            "marrow_limit": "label 11 remains the Cassano skull-like proxy and is not part of the sensitivity axis",
        },
        "scientific_status": "provisional_810_optics_yue_derived_spatial_surrogate_not_target_hardware_not_measured_dose_not_biological_efficacy",
    }
    (output / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    report_lines = [
        "# Targeted 810-nm skull optical-property comparison",
        "",
        "The in-vivo-first case is the primary estimate. Cassano is the higher-scattering sensitivity and Pitzschke is the lower-attenuation cadaver-fit sensitivity.",
        "",
        "| Skull case | mua (mm^-1) | musp (mm^-1) | Reaches skull (% launched) | Reaches intracranial (% launched) | Intracranial / reaches-skull | Change vs primary |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        report_lines.append(
            f"| {row['case']} | {row['skull_mua_mm-1']:.3f} | "
            f"{row['skull_musp_mm-1']:.2f} | "
            f"{row['reached_skull_percent_launched']:.4f}% | "
            f"{row['reached_intracranial_percent_launched']:.4f}% | "
            f"{row['intracranial_percent_of_skull_reaching']:.2f}% | "
            f"{row['intracranial_change_vs_primary_percent']:+.1f}% |"
        )
    report_lines.extend(
        [
            "",
            "The complement of the conditional percentage is not skull absorption. It includes absorption anywhere before intracranial first entry plus scattering/backscatter that redirects energy away or out of the modeled head.",
            "",
            "The nearly identical skull-entry control values show that the superficial path is matched. Differences in intracranial entry therefore arise from the label-7 skull coefficients, subject to the fixed skull-like marrow proxy.",
            "",
            "These are normalized in-model energy fractions, not device irradiance, biological efficacy, or external scalp-coupling measurements.",
        ]
    )
    (output / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
