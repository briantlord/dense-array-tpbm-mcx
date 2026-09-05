#!/usr/bin/env python3
"""Create compact QC records for the completed provisional Colin27 pilot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from mcx_project.preflight import preflight_manifest
from mcx_project.standalone import load_jnii_field
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = Path(
    "runs/provisional_1070_representative_pilot_v2/prepared/index.json"
)
OUTPUT_JSON = Path("runs/provisional_1070_representative_pilot_v2/pilot_qc.json")
OUTPUT_MARKDOWN = Path("runs/provisional_1070_representative_pilot_v2/pilot_qc.md")


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def main() -> None:
    index = load_json(ROOT / INDEX_PATH)
    records: list[dict[str, Any]] = []
    completed_times: list[str] = []
    anatomy_labels: np.ndarray | None = None
    anatomy_affine: np.ndarray | None = None
    tissue_names: dict[int, str] = {}

    for planned in index["runs"]:
        manifest_path = ROOT / planned["manifest_path"]
        preflight_manifest(manifest_path, ROOT)
        manifest = load_json(manifest_path)
        if manifest["status"] != "complete":
            raise RuntimeError(f"run is not complete: {manifest_path}")

        if anatomy_labels is None:
            anatomy_ref = manifest["inputs"]["anatomy"]
            anatomy = load_json(ROOT / anatomy_ref["path"])
            image = nib.load(ROOT / anatomy["volume_representation"])
            anatomy_labels = np.asarray(image.dataobj, dtype=np.uint8)
            anatomy_affine = np.asarray(anatomy["affine"], dtype=np.float64)
            tissue_names = {
                int(row["id"]): row["name"] for row in anatomy["labels"]
            }

        fluence_ref = next(
            output for output in manifest["outputs"] if output["kind"] == "fluence"
        )
        field = np.squeeze(load_jnii_field(ROOT / fluence_ref["path"]))
        if field.shape != anatomy_labels.shape:
            raise RuntimeError(
                f"field/anatomy shape mismatch for {planned['emitter_id']}"
            )
        config = load_json(
            ROOT / manifest["inputs"]["engine_configuration"]["path"]
        )
        source_voxel = np.asarray(config["source"]["position_voxels"], dtype=float)
        source_index = np.rint(source_voxel).astype(int)
        source_tissue = int(anatomy_labels[tuple(source_index)])
        maximum_index = np.asarray(
            np.unravel_index(int(np.argmax(field)), field.shape), dtype=int
        )
        maximum_world = (
            anatomy_affine @ np.r_[maximum_index.astype(float), 1.0]
        )[:3]
        source_world = (anatomy_affine @ np.r_[source_voxel, 1.0])[:3]
        tissue_sums = {
            tissue_names[tissue_id]: float(
                np.sum(field[anatomy_labels == tissue_id], dtype=np.float64)
            )
            for tissue_id in sorted(tissue_names)
        }
        gray_mask = anatomy_labels == 2
        white_mask = anatomy_labels == 3
        summary = load_json(manifest_path.parent / "summary.json")
        execution = load_json(manifest_path.parent / "execution.json")
        completed_times.append(execution["completed_at"])
        checks = {
            "finite": bool(np.all(np.isfinite(field))),
            "gray_matter_reached": bool(tissue_sums["gray_matter"] > 0.0),
            "nonnegative": bool(np.min(field) >= 0.0),
            "nonuniform": bool(np.std(field, dtype=np.float64) > 0.0),
            "source_inside_labeled_tissue": source_tissue != 0,
            "white_matter_reached": bool(tissue_sums["white_matter"] > 0.0),
        }
        records.append(
            {
                "absorbed_energy_percent": summary["engine"][
                    "absorbed_energy_percent"
                ],
                "checks": checks,
                "emitter_id": planned["emitter_id"],
                "field_maximum": float(np.max(field)),
                "field_sum": float(np.sum(field, dtype=np.float64)),
                "gray_matter_positive_fraction": float(
                    np.count_nonzero(field[gray_mask]) / np.count_nonzero(gray_mask)
                ),
                "gray_matter_sum": tissue_sums["gray_matter"],
                "maximum_distance_from_source_mm": float(
                    np.linalg.norm(maximum_world - source_world)
                ),
                "maximum_voxel": maximum_index.tolist(),
                "positive_voxels": int(np.count_nonzero(field)),
                "run_id": manifest["run_id"],
                "source_tissue_id": source_tissue,
                "source_tissue_name": tissue_names[source_tissue],
                "source_voxel": source_voxel.tolist(),
                "tissue_sums": tissue_sums,
                "white_matter_positive_fraction": float(
                    np.count_nonzero(field[white_mask]) / np.count_nonzero(white_mask)
                ),
                "white_matter_sum": tissue_sums["white_matter"],
            }
        )

    report = {
        "all_checks_passed": all(
            all(record["checks"].values()) for record in records
        ),
        "basis_set_id": index["basis_set_id"],
        "completed_runs": len(records),
        "index_path": INDEX_PATH.as_posix(),
        "latest_completed_at": max(completed_times),
        "note": (
            "Software and placement QC for 100,000-photon provisional runs. "
            "Values are not convergence-qualified, calibrated device dose, or efficacy."
        ),
        "predecessor_attempt": {
            "basis_set_id": "provisional_1070_representative_pilot_v1",
            "disposition": (
                "Superior run failed when the restricted process exposed no OpenCL "
                "device; preserved as immutable failure evidence. Remaining v1 runs "
                "were not launched."
            ),
        },
        "records": records,
        "scientific_status": "provisional",
    }
    output_json = ROOT / OUTPUT_JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(_json_text(report), encoding="utf-8")

    lines = [
        "# Provisional 1070-nm representative pilot QC",
        "",
        report["note"],
        "",
        "| Emitter | Absorbed energy (%) | Positive voxels | GM sum | WM sum | Max distance from source (mm) | Checks |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for record in records:
        lines.append(
            "| {emitter_id} | {absorbed_energy_percent:.5f} | "
            "{positive_voxels:,} | {gray_matter_sum:.6g} | "
            "{white_matter_sum:.6g} | {maximum_distance_from_source_mm:.3f} | "
            "{check_status} |".format(
                **record,
                check_status=(
                    "PASS" if all(record["checks"].values()) else "FAIL"
                ),
            )
        )
    lines.extend(
        [
            "",
            "The v1 superior attempt is retained as a failed immutable run because the restricted process exposed no OpenCL device. The complete v2 set ran with direct M4 Pro OpenCL access.",
            "",
        ]
    )
    (ROOT / OUTPUT_MARKDOWN).write_text("\n".join(lines), encoding="utf-8")
    print(_json_text({key: report[key] for key in (
        "all_checks_passed",
        "basis_set_id",
        "completed_runs",
        "latest_completed_at",
    )}), end="")


if __name__ == "__main__":
    main()
