#!/usr/bin/env python3
"""Prepare the immutable 277-source whole-head water-only counterfactual basis."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from mcx_project.basis import prepare_basis_plan
from mcx_project.hashing import sha256_file
from mcx_project.preflight import preflight_manifest
from mcx_project.validation import load_json, validate_json


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_ID = "provisional_1070_whole_head_water_term_at_810_v1"
BASIS_SET_ID = "surrogate_yue277_1070_windows_rtx3080ti_water_whole_head_basis_v1"
BASE_OPTICAL = Path("inputs/fat_absorption_bracket_v1/fat_abs_010.json")
OVERLAY = Path(
    "inputs/optical_properties/provisional_1070_water_sensitivity_v1/"
    "whole_head_water_to_810_overlay.json"
)
EFFECTIVE_OPTICAL = Path(
    "inputs/optical_properties/provisional_1070_water_sensitivity_v1/"
    "whole_head_water_to_810_effective.json"
)
BASE_ENGINE = Path("configs/fat_abs_010_engine_template_v1.json")
ENGINE_CONFIG = Path("configs/surrogate_yue277_1070_water_whole_head_v1_engine_template.json")
BASE_TEMPLATE = Path(
    "runs/surrogate_yue277_1070_windows_rtx3080ti_fat_abs_010_basis_v1/"
    "template_manifest.json"
)
TEMPLATE = Path("runs") / BASIS_SET_ID / "template_manifest.json"
BASE_PLAN = Path("configs/surrogate_yue277_1070_windows_rtx3080ti_fat_abs_010_basis_v1.json")
PLAN = Path("configs") / f"{BASIS_SET_ID}.json"


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _write_immutable(relative: Path, value: Any) -> None:
    path = ROOT / relative
    rendered = _json_bytes(value)
    if path.exists():
        if path.read_bytes() != rendered:
            raise RuntimeError(f"refusing to replace immutable artifact: {relative}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _reference(path: Path, artifact_id: str, id_field: str, schema: str) -> dict[str, str]:
    return {
        "artifact_id": artifact_id,
        "id_field": id_field,
        "path": path.as_posix(),
        "schema_path": schema,
        "sha256": sha256_file(ROOT / path),
    }


def _effective_optical() -> dict[str, Any]:
    value = copy.deepcopy(load_json(ROOT / BASE_OPTICAL))
    overlay = load_json(ROOT / OVERLAY)
    by_id = {int(row["tissue_id"]): row for row in value["tissues"]}
    for override in overlay["overrides"]:
        tissue_id = int(override["tissue_id"])
        by_id[tissue_id].update(
            {key: item for key, item in override.items() if key != "tissue_id"}
        )
        by_id[tissue_id]["notes"] += (
            " Counterfactual: only the water-derived absorption term is evaluated "
            "at 810 nm; scattering, n, and non-water absorption remain at 1070 nm."
        )
    value["scenario_id"] = SCENARIO_ID
    value["tissues"] = [by_id[key] for key in sorted(by_id)]
    return value


def _engine(optical: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(load_json(ROOT / BASE_ENGINE))
    rows = {int(row["tissue_id"]): row for row in optical["tissues"]}
    for tissue_id, row in rows.items():
        if tissue_id == 0:
            continue
        value["properties_mm"][tissue_id] = [
            float(row["mua_mm-1"]),
            float(row["mus_mm-1"]),
            float(row["g"]),
            float(row["n"]),
        ]
    value["configuration_id"] = "surrogate_yue277_1070_water_whole_head_v1_engine_template"
    return value


def main() -> int:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    timestamp = created_at.replace("-", "").replace(":", "").replace("T", "t").replace("Z", "z")

    optical = _effective_optical()
    _write_immutable(EFFECTIVE_OPTICAL, optical)
    validate_json(
        ROOT / "schemas/optical_properties.schema.json",
        ROOT / EFFECTIVE_OPTICAL,
        require_complete=True,
    )

    engine = _engine(optical)
    _write_immutable(ENGINE_CONFIG, engine)
    validate_json(
        ROOT / "schemas/engine_configuration.schema.json",
        ROOT / ENGINE_CONFIG,
        require_complete=True,
    )

    template = copy.deepcopy(load_json(ROOT / BASE_TEMPLATE))
    template["created_at"] = created_at
    template["scenario_id"] = SCENARIO_ID
    template["run_id"] = f"{SCENARIO_ID}__{timestamp}__{sha256_file(ROOT / ENGINE_CONFIG)[:8]}"
    template["status"] = "planned"
    template["error"] = None
    template["outputs"] = []
    template["code"] = {
        "repository": template["code"]["repository"],
        "revision": revision,
        "dirty": True,
    }
    template["engine"]["configuration_sha256"] = sha256_file(ROOT / ENGINE_CONFIG)
    template["inputs"]["optical_properties"] = _reference(
        EFFECTIVE_OPTICAL,
        SCENARIO_ID,
        "scenario_id",
        "schemas/optical_properties.schema.json",
    )
    template["inputs"]["engine_configuration"] = _reference(
        ENGINE_CONFIG,
        engine["configuration_id"],
        "configuration_id",
        "schemas/engine_configuration.schema.json",
    )
    _write_immutable(TEMPLATE, template)
    validate_json(
        ROOT / "schemas/run_manifest.schema.json",
        ROOT / TEMPLATE,
        require_complete=True,
    )
    preflight_manifest(ROOT / TEMPLATE, ROOT)

    plan = copy.deepcopy(load_json(ROOT / BASE_PLAN))
    plan.update(
        {
            "basis_set_id": BASIS_SET_ID,
            "scenario_id": SCENARIO_ID,
            "created_at": created_at,
            "code_revision": revision,
            "code_dirty": True,
            "template_manifest_path": TEMPLATE.as_posix(),
            "template_manifest_sha256": sha256_file(ROOT / TEMPLATE),
            "config_root": f"configs/generated/{BASIS_SET_ID}",
            "run_root": f"runs/{BASIS_SET_ID}",
        }
    )
    _write_immutable(PLAN, plan)
    validate_json(
        ROOT / "schemas/basis_plan.schema.json", ROOT / PLAN, require_complete=True
    )
    index = prepare_basis_plan(ROOT / PLAN, ROOT)
    print(
        json.dumps(
            {
                "status": "prepared_not_executed",
                "basis_set_id": BASIS_SET_ID,
                "run_count": len(index["runs"]),
                "index_path": f"runs/{BASIS_SET_ID}/index.json",
                "optical_properties_path": EFFECTIVE_OPTICAL.as_posix(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
