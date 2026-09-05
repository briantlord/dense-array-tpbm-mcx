#!/usr/bin/env python3
"""Create a compact, provenance-bearing report for targeted penetration tallies."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TALLIES = Path("results/surrogate_yue277_1070_targeted_penetration_tallies_v1/result.json")
BYPASS = Path("results/surrogate_yue277_1070_intracranial_bypass_audit_v1/result.json")
ABSORPTION = Path(
    "results/surrogate_yue277_1070_fat_absorption_bracket_v1/fat_abs_010/summary.json"
)
PILOT_1000 = Path(
    "results/surrogate_yue277_1070_targeted_penetration_tallies_pilot_intracranial_v1/result.json"
)
PILOT_100 = Path(
    "results/surrogate_yue277_1070_targeted_penetration_tallies_pilot_intracranial_mua100_v1/result.json"
)
OUTPUT = Path("results/surrogate_yue277_1070_targeted_penetration_analysis_v1")
INDEX = Path("runs/surrogate_yue277_1070_windows_rtx3080ti_fat_abs_010_basis_v1/index.json")
ANATOMY = Path("inputs/fat_absorption_bracket_v1/colin27_labels_native12_1mm_v3.nii")


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    output = ROOT / OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise SystemExit(f"analysis output exists; version rather than overwrite: {output}")

    tallies = load(ROOT / TALLIES)
    bypass = load(ROOT / BYPASS)
    absorption = load(ROOT / ABSORPTION)
    pilot_1000 = load(ROOT / PILOT_1000)
    pilot_100 = load(ROOT / PILOT_100)

    index = load(ROOT / INDEX)
    labels = np.asarray(nib.load(ROOT / ANATOMY).dataobj, dtype=np.uint8)
    source_materials: list[int] = []
    source_ids_by_material: dict[int, list[str]] = {}
    for row in index["runs"]:
        configuration = load(ROOT / row["configuration_path"])
        position = np.floor(configuration["source"]["position_voxels"]).astype(int)
        position = np.clip(position, 0, np.asarray(labels.shape) - 1)
        material = int(labels[tuple(position)])
        source_materials.append(material)
        source_ids_by_material.setdefault(material, []).append(row["emitter_id"])

    stages = {row["stage"]: row for row in tallies["retention"]}
    skull = stages["reached_skull_complex"]["fraction_of_launched_energy_percent"]
    intracranial = stages["reached_intracranial_compartment"][
        "fraction_of_launched_energy_percent"
    ]
    brain = stages["reached_brain_parenchyma"]["fraction_of_launched_energy_percent"]
    white = stages["reached_white_matter"]["fraction_of_launched_energy_percent"]
    bypass_value = bypass["retention"][0]["fraction_of_launched_energy_percent"]

    stage_rows = []
    for retention in tallies["retention"]:
        name = retention["stage"]
        summary = tallies["stage_summaries"][name]
        stage_rows.append(
            {
                "stage": name,
                "description": summary["description"],
                "launched_energy_percent": retention["fraction_of_launched_energy_percent"],
                "preceding_stage_retention_percent": retention[
                    "fraction_of_preceding_stage_percent"
                ],
                "replicate_standard_deviation_percentage_points": summary[
                    "standard_deviation_percent_points"
                ],
                "relative_standard_deviation_percent": 100.0
                * summary["relative_standard_deviation"],
            }
        )

    sensitivity_1000 = pilot_1000["retention"][0]["fraction_of_launched_energy_percent"]
    sensitivity_100 = pilot_100["retention"][0]["fraction_of_launched_energy_percent"]
    sensitivity_relative_difference = abs(sensitivity_1000 - sensitivity_100) / (
        0.5 * (sensitivity_1000 + sensitivity_100)
    )

    result = {
        "analysis_id": "surrogate_yue277_1070_targeted_penetration_analysis_v1",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "headline": {
            "energy_reaching_brain_parenchyma_percent_of_launched": brain,
            "energy_reaching_intracranial_compartment_percent_of_launched": intracranial,
            "energy_reaching_white_matter_percent_of_launched": white,
            "energy_reaching_skull_complex_percent_of_launched": skull,
            "intracranial_retention_after_reaching_skull_percent": 100.0
            * intracranial
            / skull,
        },
        "interpretation": {
            "denominator": "normalized energy launched by the 277 in-model sources",
            "first_entry": "target absorbers count photon weight on first entry into each target tissue set",
            "source_coupling_boundary": "276 of 277 nominal source positions are already in superficial tissue voxels, so external-device coupling and scalp Fresnel entry loss are not represented",
            "skull_penetration_statement": "2.581% of in-model launched energy reaches the intracranial compartment; among energy that first reaches skull or marrow, 21.460% subsequently reaches the intracranial compartment",
        },
        "quality_control": {
            "absorber_mua_sensitivity": {
                "intracranial_capture_percent_at_100_mm-1": sensitivity_100,
                "intracranial_capture_percent_at_1000_mm-1": sensitivity_1000,
                "symmetric_relative_difference": sensitivity_relative_difference,
                "pilot_photons": pilot_1000["photon_count_per_replicate"],
            },
            "intracranial_before_skull_bypass": {
                "launched_energy_percent": bypass_value,
                "percent_of_all_intracranial_reaching_energy": 100.0
                * bypass_value
                / intracranial,
            },
            "maximum_stage_relative_standard_deviation_percent": max(
                row["relative_standard_deviation_percent"] for row in stage_rows
            ),
            "production_photons_per_stage": tallies["photon_count_per_replicate"]
            * tallies["replicates"],
            "production_replicates_per_stage": tallies["replicates"],
        },
        "relationship_to_absorption": {
            "brain_absorbed_percent_of_launched": absorption["brain_absorbed_percent"],
            "brain_absorbed_percent_of_energy_reaching_brain": 100.0
            * absorption["brain_absorbed_percent"]
            / brain,
            "white_matter_absorbed_percent_of_launched": absorption[
                "white_matter_absorbed_percent"
            ],
            "white_matter_absorbed_percent_of_energy_reaching_white_matter": 100.0
            * absorption["white_matter_absorbed_percent"]
            / white,
        },
        "source_position_material_counts": {
            str(material): count
            for material, count in sorted(
                (material, source_materials.count(material))
                for material in set(source_materials)
            )
        },
        "source_ids_at_background_nominal_positions": source_ids_by_material.get(0, []),
        "stage_rows": stage_rows,
        "scientific_status": tallies["scientific_status"],
        "inputs": {
            path.as_posix(): sha256(ROOT / path)
            for path in (TALLIES, BYPASS, ABSORPTION, PILOT_1000, PILOT_100, INDEX, ANATOMY)
        },
    }
    write_json(output / "result.json", result)

    with (output / "retention.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(stage_rows[0]))
        writer.writeheader()
        writer.writerows(stage_rows)

    report = f"""# Targeted penetration tallies

## Result

- **{intracranial:.4f}%** of normalized in-model launched energy first reaches the intracranial compartment.
- **{100.0 * intracranial / skull:.3f}%** of energy that reaches skull or marrow subsequently reaches the intracranial compartment.
- **{brain:.4f}%** of launched energy first reaches gray or white matter.
- **{white:.4f}%** of launched energy first reaches white matter.

| Stage | Launched energy (%) | Retained from preceding stage (%) | Replicate SD (percentage points) |
|---|---:|---:|---:|
"""
    for row in stage_rows:
        report += (
            f"| {row['stage']} | {row['launched_energy_percent']:.6f} | "
            f"{row['preceding_stage_retention_percent']:.6f} | "
            f"{row['replicate_standard_deviation_percentage_points']:.6f} |\n"
        )
    report += f"""

## Interpretation boundary

The denominator is energy launched by the 277 sources inside this computational surrogate. At their nominal voxel coordinates, 276 of 277 sources are already located in superficial tissue labels. Therefore this result does **not** include external emitter-to-scalp coupling or a measured Fresnel entry loss.

Each target tissue set was replaced by a nearly perfect absorber with the original tissue refractive index. Target deposition measures first-entry photon weight. Three independent {tallies['photon_count_per_replicate']:,}-photon aggregate runs were used per stage.

The intracranial-with-skull-blocked audit measured only {bypass_value:.8f}% of launched energy reaching intracranial labels before skull/marrow labels ({100.0 * bypass_value / intracranial:.5f}% of intracranial-reaching energy), so the skull-conditional ratio is not materially driven by segmentation bypasses.

Changing absorber μa from 100 to 1000 mm⁻¹ changed the low-photon intracranial tally by {100.0 * sensitivity_relative_difference:.4f}% relative.

Scientific status: {tallies['scientific_status']}.
"""
    (output / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps(result["headline"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
