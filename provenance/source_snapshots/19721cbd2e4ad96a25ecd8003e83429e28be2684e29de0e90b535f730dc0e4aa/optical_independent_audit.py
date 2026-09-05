"""Independent cross-check of the provisional 1070-nm optical table.

This audit intentionally reconstructs the central values from the saved source
transcriptions instead of importing the scenario generator.  It can verify
quantity identity, unit conversion, wavelength labeling, and arithmetic.  It
cannot turn a single-operator graph digitization or a surrogate tissue binding
into production evidence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .validation import InputValidationError, load_json


CENTRAL = Path("inputs/optical_properties/provisional_1070_v1/central.json")
MANIFEST = Path(
    "inputs/optical_properties/provisional_1070_v1/scenario_set_manifest.json"
)
LEDGER = Path("literature/optical_properties_1070_source_ledger.json")
OUTPUT_JSON = Path("literature/optical_properties_1070_independent_audit_2026-08-14.json")
OUTPUT_MD = Path("literature/optical_properties_1070_independent_audit_2026-08-14.md")

SOURCE_TABLES = (
    Path("literature/shapey_2022_1070_transcription.csv"),
    Path("literature/digitized_1070_primary_curves.csv"),
    Path("literature/friebel_blood_1070_digitization.csv"),
    Path("literature/damagatla_2026_in_vivo_human_1070_summary.csv"),
    Path("literature/kothuri_2025_human_bone_1070_transcription.csv"),
    Path("literature/water_csf_1070_candidates.csv"),
)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_values(root: Path) -> dict[int, dict[str, Any]]:
    shapey = _rows(root / SOURCE_TABLES[0])
    primary_curves = _rows(root / SOURCE_TABLES[1])
    friebel = _rows(root / SOURCE_TABLES[2])
    damagatla = _rows(root / SOURCE_TABLES[3])
    kothuri = _rows(root / SOURCE_TABLES[4])
    water = _rows(root / SOURCE_TABLES[5])

    shapey_by_id = {int(row["tissue_id"]): row for row in shapey}
    curve_by_id = {row["record_id"]: row for row in primary_curves}
    friebel_by_id = {row["record_id"]: row for row in friebel}
    damagatla_by_location = {row["location"]: row for row in damagatla}
    water_by_id = {row["record_id"]: row for row in water}
    marrow_rows = {
        row["quantity"]: row
        for row in kothuri
        if row["source_component"] == "frozen_bone_marrow"
    }

    # Re-evaluated here from the published cm^-1 spectral laws, independently
    # of the scenario generator and ledger target-value cells.
    fat_musp = 1050.6 * (1070.0 ** -0.68) / 10.0
    skull_musp = 1533.02 * (1070.0 ** -0.65) / 10.0

    def shapey_values(tissue_id: int) -> tuple[float, float]:
        row = shapey_by_id[tissue_id]
        return float(row["mua_revised_mean_mm-1"]), float(
            row["musp_model_fitted_mm-1"]
        )

    gm_mua, gm_musp = shapey_values(2)
    wm_mua, wm_musp = shapey_values(3)
    dura_mua, dura_musp = shapey_values(10)
    fat_mua = float(curve_by_id["bashkatov_2005_fat_mua_digitized"]["target_value_1070"])
    skull_mua = float(curve_by_id["bashkatov_2006_skull_mua_digitized"]["target_value_1070"])
    upper_arm = damagatla_by_location["Upper_arm"]
    forehead = damagatla_by_location["Forehead"]
    csf_mua = float(water_by_id["hale_querry_1973_water_mua_interp"]["target_value_1070"])
    csf_n = float(water_by_id["daimon_masumura_2007_water_n"]["target_value_1070"])
    blood_mua = float(friebel_by_id["friebel_2006_blood_mua_oxy_hct42"]["target_value_1070"])
    blood_musp = float(friebel_by_id["friebel_2006_blood_musp_oxy_hct42"]["target_value_1070"])
    blood_g = float(friebel_by_id["friebel_2006_blood_g_oxy_hct42"]["target_value_1070"])

    # `kind` describes the weakest link in each row, not a claim that every
    # component has the same evidence type.
    return {
        0: dict(name="background_air", mua=0.0, musp=None, g=0.0, n=1.0, kind="model_convention", wavelengths={1070.0}),
        1: dict(name="cerebrospinal_fluid", mua=csf_mua, musp=0.01, g=0.89, n=csf_n, kind="water_proxy_plus_neighboring_1064_assumption", wavelengths={1060.0, 1064.0, 1070.0, 1080.0}),
        2: dict(name="gray_matter", mua=gm_mua, musp=gm_musp, g=0.85, n=1.4, kind="exact_table_plus_fixed_inverse_inputs", wavelengths={1070.0}),
        3: dict(name="white_matter", mua=wm_mua, musp=wm_musp, g=0.85, n=1.4, kind="exact_table_plus_fixed_inverse_inputs", wavelengths={1070.0}),
        4: dict(name="fat", mua=fat_mua, musp=fat_musp, g=0.9, n=1.4, kind="graph_plus_spectral_model_and_assumptions", wavelengths={1070.0}),
        5: dict(name="muscles", mua=float(upper_arm["mua_mean_mm-1"]), musp=float(upper_arm["musp_mean_mm-1"]), g=0.9, n=1.4, kind="exact_bulk_tissue_surrogate_plus_assumptions", wavelengths={1070.0}),
        6: dict(name="skin_and_muscles", mua=float(forehead["mua_mean_mm-1"]), musp=float(forehead["musp_mean_mm-1"]), g=0.9, n=1.4, kind="exact_bulk_composite_surrogate_plus_assumptions", wavelengths={1070.0}),
        7: dict(name="skull", mua=skull_mua, musp=skull_musp, g=0.9, n=1.4, kind="graph_plus_spectral_model_and_assumptions", wavelengths={1070.0}),
        9: dict(name="fat_2", mua=fat_mua, musp=fat_musp, g=0.9, n=1.4, kind="shared_fat_proxy_assumption", wavelengths={1070.0}),
        10: dict(name="dura", mua=dura_mua, musp=dura_musp, g=0.85, n=1.4, kind="exact_table_plus_fixed_inverse_inputs", wavelengths={1070.0}),
        11: dict(name="marrow", mua=float(marrow_rows["mua"]["mean_mm-1"]), musp=float(marrow_rows["musp"]["mean_mm-1"]), g=0.9, n=1.4, kind="exact_tibial_surrogate_plus_assumptions", wavelengths={1070.0}),
        12: dict(name="vessels", mua=blood_mua, musp=blood_musp, g=blood_g, n=1.4, kind="graph_digitized_blood_binding_plus_n_assumption", wavelengths={1070.0}),
    }


def _close(observed: float, expected: float) -> bool:
    return math.isclose(observed, expected, rel_tol=2e-10, abs_tol=2e-12)


def audit_provisional_1070(root: Path) -> dict[str, Any]:
    root = root.resolve()
    central = load_json(root / CENTRAL)
    manifest = load_json(root / MANIFEST)
    ledger = load_json(root / LEDGER)
    expected = _expected_values(root)
    ledger_ids = {row["record_id"] for row in ledger["evidence_records"]}

    errors: list[str] = []
    tissue_results: list[dict[str, Any]] = []
    central_by_id = {int(row["tissue_id"]): row for row in central["tissues"]}
    if set(central_by_id) != set(expected):
        errors.append("central tissue IDs do not match the independent expectation set")

    for tissue_id, target in expected.items():
        row = central_by_id.get(tissue_id)
        if row is None:
            continue
        checks: dict[str, bool] = {
            "tissue_name": row["tissue_name"] == target["name"],
            "mua_mm-1": _close(float(row["mua_mm-1"]), float(target["mua"])),
            "g": _close(float(row["g"]), float(target["g"])),
            "n": _close(float(row["n"]), float(target["n"])),
            "wavelength_labels": target["wavelengths"].issubset(
                {float(value) for value in row["source_wavelengths_nm"]}
            ),
            "assumption_label": row["source_kind"] == "assumption",
        }
        if target["musp"] is None:
            checks["musp_quantity"] = row["source_musp_mm-1"] == "not_used"
            expected_mus = 0.0
        else:
            checks["musp_quantity"] = _close(
                float(row["source_musp_mm-1"]), float(target["musp"])
            )
            expected_mus = float(target["musp"]) / (1.0 - float(target["g"]))
        checks["mus_from_musp_and_g"] = _close(float(row["mus_mm-1"]), expected_mus)
        failed = sorted(name for name, passed in checks.items() if not passed)
        if failed:
            errors.append(f"tissue {tissue_id} failed checks: {', '.join(failed)}")
        tissue_results.append(
            {
                "tissue_id": tissue_id,
                "tissue_name": target["name"],
                "evidence_class": target["kind"],
                "checks": checks,
                "status": "pass" if not failed else "fail",
            }
        )

    provenance_errors: list[str] = []
    for binding in manifest["field_provenance"]:
        for field in ("mua", "musp", "g", "n"):
            missing = sorted(set(binding[field]) - ledger_ids)
            if missing:
                provenance_errors.append(
                    f"tissue {binding['tissue_id']} {field} missing records {missing}"
                )
    errors.extend(provenance_errors)

    parameter_fields = {"mua_mm-1", "mus_mm-1", "source_musp_mm-1", "g", "n"}
    variant_results: list[dict[str, Any]] = []
    for metadata in manifest["variants"]:
        scenario = load_json(root / metadata["path"])
        scenario_by_id = {int(row["tissue_id"]): row for row in scenario["tissues"]}
        variant_errors: list[str] = []
        if float(scenario["wavelength_nm"]) != 1070.0:
            variant_errors.append("scenario wavelength is not 1070 nm")
        if scenario["coefficient_unit"] != "mm^-1":
            variant_errors.append("coefficient unit is not mm^-1")
        if set(scenario_by_id) != set(central_by_id):
            variant_errors.append("tissue IDs differ from the central scenario")
        observed_changes: dict[int, set[str]] = {}
        for tissue_id, row in scenario_by_id.items():
            central_row = central_by_id[tissue_id]
            if row["tissue_name"] != central_row["tissue_name"]:
                variant_errors.append(f"tissue {tissue_id} name changed")
            if row["source_kind"] not in {
                "assumption",
                "interpolation",
                "extrapolation",
            }:
                variant_errors.append(
                    f"tissue {tissue_id} has an ineligible provisional source kind"
                )
            source_wavelengths = {
                float(value) for value in row["source_wavelengths_nm"]
            }
            if not source_wavelengths:
                variant_errors.append(f"tissue {tissue_id} lacks source wavelengths")
            if row["source_kind"] == "assumption" and 1070.0 not in source_wavelengths:
                variant_errors.append(
                    f"tissue {tissue_id} assumption lacks a 1070 target label"
                )
            if row["source_musp_mm-1"] == "not_used":
                expected_variant_mus = 0.0
            else:
                expected_variant_mus = float(row["source_musp_mm-1"]) / (
                    1.0 - float(row["g"])
                )
            direct_mus_with_consistency_musp = row["conversion"].startswith(
                "Direct 1070-nm graph-digitized mus"
            )
            if direct_mus_with_consistency_musp:
                relative_consistency_error = abs(
                    float(row["mus_mm-1"]) - expected_variant_mus
                ) / max(float(row["mus_mm-1"]), expected_variant_mus)
                if relative_consistency_error > 0.10:
                    variant_errors.append(
                        f"tissue {tissue_id} direct mus and consistency musp differ by more than 10%"
                    )
            elif not _close(float(row["mus_mm-1"]), expected_variant_mus):
                variant_errors.append(f"tissue {tissue_id} has inconsistent mus/musp/g")
            changed = {
                field
                for field in parameter_fields
                if row[field] != central_row[field]
            }
            if changed:
                observed_changes[tissue_id] = changed
        if set(observed_changes) != set(metadata["changed_tissue_ids"]):
            variant_errors.append("changed tissue IDs differ from the manifest")
        observed_fields = set().union(*observed_changes.values()) if observed_changes else set()
        if observed_fields != set(metadata["changed_fields"]):
            variant_errors.append("changed fields differ from the manifest")
        if variant_errors:
            errors.extend(
                f"variant {metadata['case']}: {message}" for message in variant_errors
            )
        variant_results.append(
            {
                "case": metadata["case"],
                "status": "pass" if not variant_errors else "fail",
            }
        )

    blockers = [
        "Bashkatov and Friebel central graph points remain single-operator digitizations, not independently redigitized values.",
        "CSF scattering and anisotropy are unchanged neighboring-1064 simulation assumptions; the absorption and refractive index are water proxies.",
        "The muscle, composite skin-and-muscle, marrow, vessel, and fat_2 bindings contain unresolved atlas-to-measurement surrogate assumptions.",
        "Most tissue refractive indices and several anisotropy values are fixed inverse-model or project assumptions rather than 1070-nm measurements.",
        "The all-TBD production table remains authoritative and no nominal scenario is frozen.",
    ]
    source_tables = [
        {"path": path.as_posix(), "sha256": _sha256(root / path)}
        for path in SOURCE_TABLES
    ]
    return {
        "audit_id": "provisional_1070_independent_quantity_unit_wavelength_v1",
        "audit_date": "2026-08-14",
        "scope": [
            "independent reconstruction from saved source transcriptions",
            "mua versus musp versus mus quantity identity",
            "cm^-1 to mm^-1 and spectral-formula arithmetic",
            "1070 versus neighboring-wavelength labeling",
            "field-provenance record resolution",
        ],
        "out_of_scope": [
            "second-operator graph redigitization",
            "new primary-source measurements",
            "scientific acceptance of surrogate tissue mappings",
        ],
        "mechanical_status": "pass" if not errors else "fail",
        "scientific_status": "blocked",
        "production_launch_allowed": False,
        "errors": errors,
        "scientific_blockers": blockers,
        "source_tables": source_tables,
        "tissues": tissue_results,
        "variants": variant_results,
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Independent 1070-nm quantity, unit, and wavelength audit",
        "",
        f"**Audit:** `{report['audit_id']}`",
        "",
        f"**Mechanical result:** **{report['mechanical_status'].upper()}**",
        "",
        "**Scientific/production result:** **BLOCKED**",
        "",
        "## What passed",
        "",
        "A second implementation reconstructed the provisional central table from the saved source CSV transcriptions rather than from the scenario generator. It separately re-evaluated the Bashkatov fat and skull scattering formulas, checked every `mua`/`musp`/`mus` quantity label and conversion, recomputed `mus = musp/(1-g)`, checked required wavelength labels, and resolved every field-provenance record ID. All 12 central tissue rows and all 14 declared sensitivity variants passed those checks.",
        "",
        "| ID | Tissue | Evidence class | Result |",
        "|---:|---|---|:---:|",
    ]
    for row in report["tissues"]:
        lines.append(
            f"| {row['tissue_id']} | {row['tissue_name']} | `{row['evidence_class']}` | {row['status'].upper()} |"
        )
    lines.extend(
        [
            "",
            "## What did not pass scientifically",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["scientific_blockers"])
    lines.extend(
        [
            "",
            "This is therefore a completed independent quantity/unit/wavelength audit of the saved provisional implementation, not a second-person validation of every plotted source value and not approval of `nominal_1070_v1`. The provisional files remain appropriate for bounded sensitivity work only.",
            "",
            "## Audit boundary",
            "",
            "The audit can detect transcription-to-implementation errors, formula/unit mistakes, quantity swaps, mislabeled neighboring wavelengths, and broken provenance links. It cannot decide that a bulk upper-arm measurement is isolated cranial muscle, that tibial frozen marrow is cranial marrow, or that a fixed refractive index is measured. Those are scientific model choices and remain explicit sensitivity axes.",
            "",
        ]
    )
    return "\n".join(lines)


def write_independent_audit(root: Path, *, check: bool = False) -> dict[str, Any]:
    report = audit_provisional_1070(root)
    if report["errors"]:
        raise InputValidationError(
            "independent 1070-nm audit failed:\n- " + "\n- ".join(report["errors"])
        )
    outputs = {
        root / OUTPUT_JSON: json.dumps(report, indent=2, sort_keys=True) + "\n",
        root / OUTPUT_MD: _markdown(report),
    }
    if check:
        stale = [str(path.relative_to(root)) for path, text in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
        if stale:
            raise InputValidationError(f"independent audit outputs are stale: {stale}")
    else:
        for path, text in outputs.items():
            path.write_text(text, encoding="utf-8")
    return report
