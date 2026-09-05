"""Cross-file audit for the fail-closed 1070-nm optical-property ledger."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .validation import InputValidationError, load_json, validate_json


LEDGER_PATH = Path("literature/optical_properties_1070_source_ledger.json")
LEDGER_SCHEMA_PATH = Path("schemas/optical_property_source_ledger.schema.json")
ANATOMY_PATH = Path(
    "inputs/anatomy/colin27_2008/derived/native12_1mm_v3/anatomy_metadata.json"
)
PRODUCTION_PATH = Path("inputs/optical_properties/production_1070_tbd.json")
PRODUCTION_SCHEMA_PATH = Path("schemas/optical_properties.schema.json")


def _label_pairs(items: list[dict[str, Any]]) -> list[tuple[int, str]]:
    return [(int(item["tissue_id"]), str(item["tissue_name"])) for item in items]


def audit_optical_ledger(project_root: Path) -> dict[str, Any]:
    """Validate the ledger and enforce cross-file scientific-gate invariants."""

    root = project_root.resolve()
    ledger_path = root / LEDGER_PATH
    anatomy_path = root / ANATOMY_PATH
    production_path = root / PRODUCTION_PATH

    validate_json(root / LEDGER_SCHEMA_PATH, ledger_path)
    validate_json(root / PRODUCTION_SCHEMA_PATH, production_path)

    ledger = load_json(ledger_path)
    anatomy = load_json(anatomy_path)
    production = load_json(production_path)

    errors: list[str] = []
    anatomy_labels = [
        (int(label["id"]), str(label["name"])) for label in anatomy["labels"]
    ]
    coverage_labels = _label_pairs(ledger["coverage"])
    production_labels = _label_pairs(production["tissues"])

    if coverage_labels != anatomy_labels:
        errors.append("ledger coverage labels do not exactly match anatomy labels in order")
    if production_labels != anatomy_labels:
        errors.append("production optical labels do not exactly match anatomy labels in order")
    if ledger["anatomy_id"] != anatomy["anatomy_id"]:
        errors.append("ledger anatomy_id does not match anatomy metadata")
    if float(production["wavelength_nm"]) != float(ledger["target_wavelength_nm"]):
        errors.append("production wavelength does not match ledger target wavelength")

    records = ledger["evidence_records"]
    record_ids = [str(record["record_id"]) for record in records]
    duplicate_record_ids = sorted(
        record_id for record_id, count in Counter(record_ids).items() if count > 1
    )
    if duplicate_record_ids:
        errors.append(f"duplicate evidence record IDs: {duplicate_record_ids}")
    record_by_id = {str(record["record_id"]): record for record in records}

    for coverage in ledger["coverage"]:
        tissue_id = int(coverage["tissue_id"])
        for record_id in coverage["candidate_record_ids"]:
            if record_id not in record_by_id:
                errors.append(
                    f"tissue {tissue_id} references missing evidence record {record_id}"
                )
            elif tissue_id not in record_by_id[record_id]["tissue_ids"]:
                errors.append(
                    f"evidence record {record_id} does not include referenced tissue {tissue_id}"
                )

    numeric_candidate_statuses = {
        "candidate_exact_1070",
        "candidate_spectral_model_1070",
    }
    for record in records:
        if len(record["tissue_ids"]) != len(record["tissue_names"]):
            errors.append(
                f"evidence record {record['record_id']} has mismatched tissue ID/name counts"
            )
        if (
            record["evidence_status"] in numeric_candidate_statuses
            and record["quantity"] not in {"multi_quantity_table", "composite_mapping"}
            and not isinstance(record["target_value_1070"], (int, float))
        ):
            errors.append(
                f"numeric 1070 candidate {record['record_id']} lacks a numeric target value"
            )
        if (
            record["source_kind"] == "direct_measurement"
            and not record["source"]["primary_source"]
        ):
            errors.append(
                f"direct-measurement record {record['record_id']} is not tied to a primary source"
            )
        if (
            record["evidence_status"] == "neighboring_wavelength_only"
            and record["target_value_1070"] != "TBD"
        ):
            errors.append(
                f"neighboring-wavelength record {record['record_id']} improperly supplies a 1070 value"
            )

    unresolved_production = 0
    for tissue in production["tissues"]:
        for key in ("mua_mm-1", "mus_mm-1", "source_musp_mm-1", "g", "n"):
            if tissue[key] == "TBD":
                unresolved_production += 1

    if ledger["status"] == "frozen":
        if any(item["production_status"] != "frozen" for item in ledger["coverage"]):
            errors.append("a frozen ledger contains coverage rows that are not frozen")
        try:
            validate_json(
                root / PRODUCTION_SCHEMA_PATH,
                production_path,
                require_complete=True,
            )
        except InputValidationError as error:
            errors.append(f"frozen ledger has incomplete production table: {error}")
    elif unresolved_production == 0:
        errors.append("a non-frozen ledger unexpectedly has a complete production table")

    if errors:
        raise InputValidationError(
            "optical-property ledger audit failed:\n- " + "\n- ".join(errors)
        )

    evidence_counts = Counter(record["evidence_status"] for record in records)
    return {
        "status": "valid_but_blocked" if ledger["status"] != "frozen" else "frozen",
        "ledger_id": ledger["ledger_id"],
        "target_wavelength_nm": ledger["target_wavelength_nm"],
        "anatomy_labels_covered": len(coverage_labels),
        "evidence_records": len(records),
        "evidence_status_counts": dict(sorted(evidence_counts.items())),
        "unresolved_production_cells": unresolved_production,
        "production_launch_allowed": ledger["status"] == "frozen",
    }
