"""Build assumption-explicit provisional 1070-nm optical scenarios."""

from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
from typing import Any

from .validation import InputValidationError, load_json, validate_json


OUTPUT_ROOT = Path("inputs/optical_properties/provisional_1070_v1")
CENTRAL_PATH = OUTPUT_ROOT / "central.json"
MANIFEST_PATH = OUTPUT_ROOT / "scenario_set_manifest.json"
OPTICAL_SCHEMA = Path("schemas/optical_properties.schema.json")
MANIFEST_SCHEMA = Path("schemas/optical_scenario_set.schema.json")
LEDGER_PATH = Path("literature/optical_properties_1070_source_ledger.json")


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _ledger_records(project_root: Path) -> dict[str, dict[str, Any]]:
    ledger = load_json(project_root / LEDGER_PATH)
    return {row["record_id"]: row for row in ledger["evidence_records"]}


def _target(records: dict[str, dict[str, Any]], record_id: str) -> float:
    value = records[record_id]["target_value_1070"]
    if not isinstance(value, (int, float)):
        raise InputValidationError(f"{record_id} has no numeric 1070-nm target")
    return float(value)


def _kothuri_values(project_root: Path) -> dict[tuple[str, str], float]:
    path = project_root / "literature/kothuri_2025_human_bone_1070_transcription.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        return {
            (row["source_component"], row["quantity"]): float(row["mean_mm-1"])
            for row in csv.DictReader(stream)
        }


def _row(
    tissue_id: int,
    tissue_name: str,
    *,
    mua: float,
    musp: float | None,
    g: float,
    n: float,
    citation: str,
    conversion: str,
    tissue_definition: str,
    uncertainty: str,
    notes: str,
    source_kind: str = "assumption",
    source_wavelengths_nm: list[float] | None = None,
    mus: float | None = None,
) -> dict[str, Any]:
    if mus is None:
        if musp is None:
            raise ValueError("musp is required when mus is not supplied")
        mus = musp / (1.0 - g)
    return {
        "citation": citation,
        "conversion": conversion,
        "g": g,
        "mua_mm-1": mua,
        "mus_mm-1": mus,
        "n": n,
        "notes": notes,
        "review_status": "single_reviewed",
        "source_kind": source_kind,
        "source_musp_mm-1": musp if musp is not None else "not_used",
        "source_wavelengths_nm": source_wavelengths_nm or [1070.0],
        "tissue_definition": tissue_definition,
        "tissue_id": tissue_id,
        "tissue_name": tissue_name,
        "uncertainty": uncertainty,
    }


def _central(
    records: dict[str, dict[str, Any]], kothuri: dict[tuple[str, str], float]
) -> dict[str, Any]:
    n_tissue = 1.4
    tissues = [
        _row(
            0,
            "background_air",
            mua=0.0,
            musp=None,
            mus=0.0,
            g=0.0,
            n=1.0,
            citation="literature/optical_properties_1070_source_ledger.json#air_boundary_convention",
            conversion="No conversion; MCX boundary-medium convention.",
            tissue_definition="Exterior background and atlas air cavities.",
            uncertainty="Idealized boundary convention, not a tissue measurement.",
            notes="Provisional only; frozen with the complete scenario rather than independently.",
        ),
        _row(
            1,
            "cerebrospinal_fluid",
            mua=_target(records, "hale_querry_1973_water_mua_interp"),
            musp=0.01,
            g=0.89,
            n=_target(records, "daimon_masumura_2007_water_n"),
            citation="ledger#hale_querry_1973_water_mua_interp; ledger#daimon_masumura_2007_water_n; Cassano et al. 2019 Table 1",
            conversion="Water mua is the documented 1060/1080-nm midpoint at 1070; n is the 21.5 C Sellmeier evaluation; musp=0.01 and g=0.89 are unchanged 1064-nm simulation assumptions. mus=musp/(1-g).",
            tissue_definition="Colin27 CSF represented by an explicit water-like optical proxy.",
            uncertainty="No physiological CSF scattering measurement; water temperature and 1064-nm scattering assumptions are tested separately.",
            notes="Proxy/assumption row. No component is represented as measured physiological CSF.",
            source_wavelengths_nm=[1060.0, 1064.0, 1070.0, 1080.0],
        ),
        _row(
            2,
            "gray_matter",
            mua=_target(records, "shapey_2022_gm_mua"),
            musp=_target(records, "shapey_2022_gm_musp"),
            g=0.85,
            n=n_tissue,
            citation="ledger#shapey_2022_gm_mua; ledger#shapey_2022_gm_musp; ledger#shapey_2022_fixed_g_085; ledger#shapey_2022_fixed_n_140",
            conversion="Exact 1070-nm mua and model-fitted musp; mus=musp/(1-0.85).",
            tissue_definition="Colin27 gray matter bound to ex vivo human cortical gray matter.",
            uncertainty="One frozen cadaver; g and n were fixed inversion inputs rather than measurements.",
            notes="Internally consistent reproduction of the Shapey inversion assumptions.",
        ),
        _row(
            3,
            "white_matter",
            mua=_target(records, "shapey_2022_wm_mua"),
            musp=_target(records, "shapey_2022_wm_musp"),
            g=0.85,
            n=n_tissue,
            citation="ledger#shapey_2022_wm_mua; ledger#shapey_2022_wm_musp; ledger#shapey_2022_fixed_g_085; ledger#shapey_2022_fixed_n_140",
            conversion="Exact 1070-nm mua and model-fitted musp; mus=musp/(1-0.85).",
            tissue_definition="Colin27 white matter bound to ex vivo human white matter.",
            uncertainty="One frozen cadaver; g and n were fixed inversion inputs; independent datasets conflict.",
            notes="Provisional Shapey central case; conflicts remain sensitivity questions.",
        ),
        _row(
            4,
            "fat",
            mua=_target(records, "bashkatov_2005_fat_mua_digitized"),
            musp=_target(records, "bashkatov_2005_fat_musp"),
            g=0.9,
            n=n_tissue,
            citation="ledger#bashkatov_2005_fat_mua_digitized; ledger#bashkatov_2005_fat_musp; ledger#bashkatov_2005_fixed_g",
            conversion="Exact-wavelength graph mua and evaluated musp model; mus=musp/(1-0.9).",
            tissue_definition="Colin27 fat bound to human subcutaneous/peritoneal adipose as a proxy.",
            uncertainty="Large absorption-method conflict; g was fixed and n is a project assumption.",
            notes="High-absorption central value is paired with an explicit low-absorption sensitivity.",
        ),
        _row(
            5,
            "muscles",
            mua=_target(records, "damagatla_2026_upper_arm_mua"),
            musp=_target(records, "damagatla_2026_upper_arm_musp"),
            g=0.9,
            n=n_tissue,
            citation="ledger#damagatla_2026_upper_arm_mua; ledger#damagatla_2026_upper_arm_musp; project g/n assumptions",
            conversion="Exact 1070-nm bulk upper-arm means; mus=musp/(1-0.9).",
            tissue_definition="Colin27 muscle bound to a muscle-rich but layered in vivo human upper-arm measurement.",
            uncertainty="Not isolated muscle; g=0.9 and n=1.4 are assumptions.",
            notes="Cortese human SCM and Mosca porcine cases are separate sensitivities.",
        ),
        _row(
            6,
            "skin_and_muscles",
            mua=_target(records, "damagatla_2026_forehead_mua"),
            musp=_target(records, "damagatla_2026_forehead_musp"),
            g=0.9,
            n=n_tissue,
            citation="ledger#damagatla_2026_forehead_mua; ledger#damagatla_2026_forehead_musp; project g/n assumptions",
            conversion="Exact 1070-nm bulk forehead means; mus=musp/(1-0.9).",
            tissue_definition="Native Colin27 composite skin-and-muscles label represented by bulk forehead tissue.",
            uncertainty="Atlas composition is unknown; g=0.9 and n=1.4 are assumptions.",
            notes="Pure-skin and pure-muscle bindings are separate one-at-a-time sensitivities.",
        ),
        _row(
            7,
            "skull",
            mua=_target(records, "bashkatov_2006_skull_mua_digitized"),
            musp=_target(records, "bashkatov_2006_skull_musp"),
            g=0.9,
            n=n_tissue,
            citation="ledger#bashkatov_2006_skull_mua_digitized; ledger#bashkatov_2006_skull_musp; ledger#bashkatov_2006_fixed_g",
            conversion="Intact-cranial graph mua and evaluated cortical-skull musp model; mus=musp/(1-0.9).",
            tissue_definition="Colin27 skull represented by intact human cortical cranial bone.",
            uncertainty="Cortical/trabecular composition is unknown; graph audit and n assumption remain.",
            notes="Tibial trabecular and cortical-powder cases remain separate sensitivities.",
        ),
        _row(
            9,
            "fat_2",
            mua=_target(records, "bashkatov_2005_fat_mua_digitized"),
            musp=_target(records, "bashkatov_2005_fat_musp"),
            g=0.9,
            n=n_tissue,
            citation="ledger#bashkatov_2005_fat_mua_digitized; ledger#bashkatov_2005_fat_musp; ledger#fat_label_identity_gap",
            conversion="Same adipose proxy as label 4 by declared shared_adipose_proxy_assumption; mus=musp/(1-0.9).",
            tissue_definition="Native Colin27 fat_2 label with undocumented distinction from fat.",
            uncertainty="Atlas identity is unresolved; shared numerical values do not establish equivalence.",
            notes="Explicit shared-adipose proxy assumption, never a silent copy.",
        ),
        _row(
            10,
            "dura",
            mua=_target(records, "shapey_2022_dura_mua"),
            musp=_target(records, "shapey_2022_dura_musp"),
            g=0.85,
            n=n_tissue,
            citation="ledger#shapey_2022_dura_mua; ledger#shapey_2022_dura_musp; ledger#shapey_2022_fixed_g_085; ledger#shapey_2022_fixed_n_140",
            conversion="Exact 1070-nm mua and model-fitted musp; mus=musp/(1-0.85).",
            tissue_definition="Colin27 dura bound to ex vivo human dura.",
            uncertainty="One frozen cadaver; g and n were fixed inversion inputs.",
            notes="Dura remains separate from skull.",
        ),
        _row(
            11,
            "marrow",
            mua=kothuri[("frozen_bone_marrow", "mua")],
            musp=kothuri[("frozen_bone_marrow", "musp")],
            g=0.9,
            n=n_tissue,
            citation="ledger#kothuri_2025_bone_table; project g/n assumptions",
            conversion="Mean of three exact 1070-nm frozen-marrow iterations; cm^-1 divided by 10; mus=musp/(1-0.9).",
            tissue_definition="Colin27 cranial-marrow label represented by frozen human tibial marrow.",
            uncertainty="One elderly donor, tibial site, frozen state, boundary effects, and assumed g/n.",
            notes="Material surrogate, not a claim of cranial equivalence.",
        ),
        _row(
            12,
            "vessels",
            mua=_target(records, "friebel_2006_blood_mua_oxy_hct42"),
            musp=_target(records, "friebel_2006_blood_musp_oxy_hct42"),
            g=_target(records, "friebel_2006_blood_g_oxy_hct42"),
            n=n_tissue,
            citation="ledger#friebel_2006_blood_mua_oxy_hct42; ledger#friebel_2006_blood_musp_oxy_hct42; ledger#friebel_2006_blood_g_oxy_hct42; project n assumption",
            conversion="Graph-digitized oxygenated hct-42.1 coefficients; mus=musp/(1-g).",
            tissue_definition="Native vessel class represented operationally as oxygenated intravascular whole blood.",
            uncertainty="Graph audit, n, lumen/wall partial volume, and arterial/venous composition remain unresolved.",
            notes="Effective-blood binding, not a claim that every vessel voxel is pure lumen.",
        ),
    ]
    return {
        "coefficient_unit": "mm^-1",
        "scenario_id": "provisional_1070_v1",
        "scientific_status": "provisional",
        "synthetic_test_only": False,
        "tissues": tissues,
        "wavelength_nm": 1070.0,
    }


def _tissue(scenario: dict[str, Any], tissue_id: int) -> dict[str, Any]:
    return next(row for row in scenario["tissues"] if row["tissue_id"] == tissue_id)


def _set_musp(row: dict[str, Any], musp: float, g: float | None = None) -> None:
    if g is not None:
        row["g"] = g
    row["source_musp_mm-1"] = musp
    row["mus_mm-1"] = musp / (1.0 - float(row["g"]))


def _variant(
    central: dict[str, Any],
    scenario_id: str,
    axis: str,
    case: str,
    rationale: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    scenario = copy.deepcopy(central)
    scenario["scenario_id"] = scenario_id
    metadata = {
        "axis": axis,
        "case": case,
        "path": f"{OUTPUT_ROOT.as_posix()}/sensitivities/{case}.json",
        "rationale": rationale,
        "scenario_id": scenario_id,
    }
    return scenario, metadata


def _variants(
    central: dict[str, Any],
    records: dict[str, dict[str, Any]],
    kothuri: dict[tuple[str, str], float],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    built: list[tuple[dict[str, Any], dict[str, Any]]] = []

    scenario, meta = _variant(central, "provisional_1070_n_tissue_137_v1", "refractive_index", "n_tissue_137", "Set every non-air, non-CSF tissue to the alternative uniform n=1.37 assumption.")
    for row in scenario["tissues"]:
        if row["tissue_id"] not in {0, 1}:
            row["n"] = 1.37
            row["notes"] += " Sensitivity override: uniform tissue n=1.37."
    meta["changed_tissue_ids"] = [row["tissue_id"] for row in scenario["tissues"] if row["tissue_id"] not in {0, 1}]
    meta["changed_fields"] = ["n"]
    built.append((scenario, meta))

    scenario, meta = _variant(central, "provisional_1070_csf_transparent_v1", "csf_scattering", "csf_transparent", "Set the CSF scattering coefficient to zero while retaining water absorption and refractive index.")
    row = _tissue(scenario, 1)
    _set_musp(row, 0.0, 0.0)
    row["citation"] = "ledger#hale_querry_1973_water_mua_interp; ledger#daimon_masumura_2007_water_n; transparent-CSF project assumption"
    row["conversion"] = "Water mua/n retained; mus=0 and g=0 implement a transparent non-scattering sensitivity."
    row["notes"] += " Sensitivity override: transparent CSF."
    meta.update(changed_tissue_ids=[1], changed_fields=["mus_mm-1", "source_musp_mm-1", "g"])
    built.append((scenario, meta))

    scenario, meta = _variant(central, "provisional_1070_fat_low_abs_1064_v1", "fat_absorption", "fat_low_abs_1064", "Use Cassano's much lower neighboring-1064 fat absorption only as a declared sensitivity assumption.")
    for tissue_id in (4, 9):
        row = _tissue(scenario, tissue_id)
        row["mua_mm-1"] = 0.0054
        row["citation"] += "; Cassano et al. 2019 Table 1 fat mua at 1064 nm"
        row["source_kind"] = "assumption"
        row["source_wavelengths_nm"] = [1064.0, 1070.0]
        row["conversion"] = "No wavelength transformation: 0.0054 mm^-1 at 1064 nm is carried unchanged only as a neighboring-wavelength sensitivity assumption; scattering remains central exact-1070 Bashkatov."
        row["notes"] += " This is not represented as a measured 1070-nm value."
    meta.update(changed_tissue_ids=[4, 9], changed_fields=["mua_mm-1"])
    built.append((scenario, meta))

    scenario, meta = _variant(central, "provisional_1070_muscle_cortese_scm_v1", "muscle_proxy", "muscle_cortese_scm", "Replace upper-arm scattering with the Cortese human SCM 20-nm extrapolation while holding exact-1070 Damagatla absorption fixed.")
    row = _tissue(scenario, 5)
    _set_musp(row, _target(records, "cortese_2023_scm_musp_extrap_1070"))
    row["citation"] = "ledger#damagatla_2026_upper_arm_mua; ledger#cortese_2023_scm_musp_extrap_1070; project g/n assumptions"
    row["source_kind"] = "extrapolation"
    row["source_wavelengths_nm"] = [1050.0, 1070.0]
    row["conversion"] = "Damgatla exact-1070 mua retained; Cortese power-law musp evaluated 20 nm beyond its 1050-nm endpoint; mus=musp/(1-0.9)."
    row["notes"] += " Factorized scattering-only sensitivity; it is not a source-supplied complete tuple."
    meta.update(changed_tissue_ids=[5], changed_fields=["mus_mm-1", "source_musp_mm-1"])
    built.append((scenario, meta))

    scenario, meta = _variant(central, "provisional_1070_muscle_mosca_porcine_v1", "muscle_proxy", "muscle_mosca_porcine", "Replace the human bulk proxy with exact-1070 ex vivo porcine muscle mua/musp.")
    row = _tissue(scenario, 5)
    row["mua_mm-1"] = _target(records, "mosca_2020_porcine_muscle_mua")
    _set_musp(row, _target(records, "mosca_2020_porcine_muscle_musp"))
    row["citation"] = "ledger#mosca_2020_porcine_muscle_mua; ledger#mosca_2020_porcine_muscle_musp; project g/n assumptions"
    row["conversion"] = "Exact 1070-nm porcine means; mus=musp/(1-0.9)."
    row["tissue_definition"] = "Colin27 human muscle represented by an ex vivo porcine-muscle sensitivity proxy."
    row["notes"] += " Species/state sensitivity only."
    meta.update(changed_tissue_ids=[5], changed_fields=["mua_mm-1", "mus_mm-1", "source_musp_mm-1"])
    built.append((scenario, meta))

    scenario, meta = _variant(central, "provisional_1070_composite_pure_skin_v1", "skin_muscle_composite", "composite_pure_skin", "Bind pure human skin coefficients to the composite label as an explicit endpoint sensitivity.")
    row = _tissue(scenario, 6)
    row["mua_mm-1"] = _target(records, "bashkatov_2005_skin_mua_digitized")
    _set_musp(row, _target(records, "bashkatov_2005_skin_musp"), 0.9)
    row["citation"] = "ledger#bashkatov_2005_skin_mua_digitized; ledger#bashkatov_2005_skin_musp; explicit composite-binding assumption"
    row["conversion"] = "Exact-wavelength skin graph/model values; mus=musp/(1-0.9)."
    row["tissue_definition"] = "Native composite label represented by a pure-skin endpoint assumption."
    row["notes"] += " Does not assert that the composite voxels are pure skin."
    meta.update(changed_tissue_ids=[6], changed_fields=["mua_mm-1", "mus_mm-1", "source_musp_mm-1"])
    built.append((scenario, meta))

    scenario, meta = _variant(central, "provisional_1070_composite_pure_muscle_v1", "skin_muscle_composite", "composite_pure_muscle", "Bind the bulk upper-arm muscle proxy to the composite label as the opposite endpoint sensitivity.")
    source = _tissue(central, 5)
    row = _tissue(scenario, 6)
    for field in ("mua_mm-1", "mus_mm-1", "source_musp_mm-1", "g", "n"):
        row[field] = source[field]
    row["citation"] = source["citation"] + "; explicit composite-binding assumption"
    row["conversion"] = source["conversion"]
    row["tissue_definition"] = "Native composite label represented by a pure-muscle endpoint assumption."
    row["notes"] += " Does not assert that the composite voxels are pure muscle."
    meta.update(changed_tissue_ids=[6], changed_fields=["mua_mm-1", "mus_mm-1", "source_musp_mm-1"])
    built.append((scenario, meta))

    for component, case, label in (
        ("trabecular_bone", "marrow_trabecular", "human tibial trabecular bone"),
        ("cortical_bone_powder", "marrow_skull_like", "human tibial cortical-bone powder"),
    ):
        scenario, meta = _variant(central, f"provisional_1070_{case}_v1", "marrow_proxy", case, f"Represent the cranial-marrow label using {label} as a material endpoint sensitivity.")
        row = _tissue(scenario, 11)
        row["mua_mm-1"] = kothuri[(component, "mua")]
        _set_musp(row, kothuri[(component, "musp")], 0.9)
        row["citation"] = "ledger#kothuri_2025_bone_table; project g/n assumptions"
        row["conversion"] = "Mean of three exact 1070-nm iterations; cm^-1 divided by 10; mus=musp/(1-0.9)."
        row["tissue_definition"] = f"Colin27 marrow represented by {label} as a sensitivity proxy."
        row["notes"] += " Site/preparation sensitivity, not a cranial-tissue identity claim."
        meta.update(changed_tissue_ids=[11], changed_fields=["mua_mm-1", "mus_mm-1", "source_musp_mm-1"])
        built.append((scenario, meta))

    for state, mua_id, mus_id, musp, case in (
        ("oxygenated", "friebel_2009_blood_mua_oxy_hct33", "friebel_2009_blood_mus_oxy_hct33", 1.5489361702, "blood_hct33_oxy"),
        ("deoxygenated", "friebel_2009_blood_mua_deoxy_hct33", "friebel_2009_blood_mus_deoxy_hct33", 1.4, "blood_hct33_deoxy"),
    ):
        scenario, meta = _variant(central, f"provisional_1070_{case}_v1", "blood_state", case, f"Use the Friebel 2009 hct-33.2 {state} state as a paired blood sensitivity.")
        row = _tissue(scenario, 12)
        row["mua_mm-1"] = _target(records, mua_id)
        row["mus_mm-1"] = _target(records, mus_id)
        row["source_musp_mm-1"] = musp
        row["g"] = _target(records, "friebel_2009_blood_g_oxy_deoxy_hct33")
        row["citation"] = f"ledger#{mua_id}; ledger#{mus_id}; ledger#friebel_2009_blood_g_oxy_deoxy_hct33; project n assumption"
        row["conversion"] = "Direct 1070-nm graph-digitized mus and g; saved musp curve retained as a consistency field."
        row["tissue_definition"] = f"Native vessel class represented operationally as {state} hct-33.2 whole blood."
        row["notes"] += " Oxygenation comparison is paired at one haematocrit."
        meta.update(changed_tissue_ids=[12], changed_fields=["mua_mm-1", "mus_mm-1", "source_musp_mm-1", "g"])
        built.append((scenario, meta))

    scenario, meta = _variant(central, "provisional_1070_brain_yaroslavsky_gray_v1", "brain_dataset", "brain_yaroslavsky_gray", "Replace gray matter only with the secondary Yaroslavsky interpolation; white matter remains Shapey because its transcription is conflicted.")
    row = _tissue(scenario, 2)
    row["mua_mm-1"] = _target(records, "yaroslavsky_2002_gm_mua_interp")
    row["mus_mm-1"] = _target(records, "yaroslavsky_2002_gm_mus_interp")
    row["g"] = _target(records, "yaroslavsky_2002_gm_g")
    row["source_musp_mm-1"] = row["mus_mm-1"] * (1.0 - row["g"])
    row["citation"] = "ledger#yaroslavsky_2002_gm_mua_interp; ledger#yaroslavsky_2002_gm_mus_interp; ledger#yaroslavsky_2002_gm_g; project n assumption"
    row["source_kind"] = "interpolation"
    row["source_wavelengths_nm"] = [1060.0, 1080.0]
    row["conversion"] = "Linear 1060/1080-nm interpolation to 1070; musp=mus*(1-g)."
    row["notes"] += " Gray-only dataset sensitivity; not a complete alternative brain table."
    meta.update(changed_tissue_ids=[2], changed_fields=["mua_mm-1", "mus_mm-1", "source_musp_mm-1", "g"])
    built.append((scenario, meta))

    for component, case, label in (
        ("trabecular_bone", "skull_trabecular", "human tibial trabecular bone"),
        ("cortical_bone_powder", "skull_cortical_powder", "human tibial cortical-bone powder"),
    ):
        scenario, meta = _variant(central, f"provisional_1070_{case}_v1", "skull_material", case, f"Replace intact cortical cranium with {label} as a bone-compartment sensitivity.")
        row = _tissue(scenario, 7)
        row["mua_mm-1"] = kothuri[(component, "mua")]
        _set_musp(row, kothuri[(component, "musp")], 0.9)
        row["citation"] = "ledger#kothuri_2025_bone_table; project g/n assumptions"
        row["conversion"] = "Mean of three exact 1070-nm iterations; cm^-1 divided by 10; mus=musp/(1-0.9)."
        row["tissue_definition"] = f"Colin27 skull represented by {label} as a sensitivity proxy."
        row["notes"] += " Bone-compartment/preparation sensitivity, not a cranial equivalence claim."
        meta.update(changed_tissue_ids=[7], changed_fields=["mua_mm-1", "mus_mm-1", "source_musp_mm-1"])
        built.append((scenario, meta))

    return built


def _field_provenance() -> list[dict[str, Any]]:
    return [
        {"tissue_id": 0, "mua": ["air_boundary_convention"], "musp": [], "g": ["air_boundary_convention"], "n": ["air_boundary_convention"], "assumptions": ["ideal boundary medium"]},
        {"tissue_id": 1, "mua": ["hale_querry_1973_water_mua_interp"], "musp": ["cassano_1064_compiled_table"], "g": ["cassano_1064_compiled_table"], "n": ["daimon_masumura_2007_water_n"], "assumptions": ["water proxy", "unchanged neighboring-1064 scattering precedent"]},
        {"tissue_id": 2, "mua": ["shapey_2022_gm_mua"], "musp": ["shapey_2022_gm_musp"], "g": ["shapey_2022_fixed_g_085"], "n": ["shapey_2022_fixed_n_140"], "assumptions": ["ex vivo to atlas binding", "fixed inversion g/n"]},
        {"tissue_id": 3, "mua": ["shapey_2022_wm_mua"], "musp": ["shapey_2022_wm_musp"], "g": ["shapey_2022_fixed_g_085"], "n": ["shapey_2022_fixed_n_140"], "assumptions": ["ex vivo to atlas binding", "fixed inversion g/n"]},
        {"tissue_id": 4, "mua": ["bashkatov_2005_fat_mua_digitized"], "musp": ["bashkatov_2005_fat_musp"], "g": ["bashkatov_2005_fixed_g"], "n": ["brain_n_assumption"], "assumptions": ["adipose to atlas binding", "uniform n=1.4"]},
        {"tissue_id": 5, "mua": ["damagatla_2026_upper_arm_mua"], "musp": ["damagatla_2026_upper_arm_musp"], "g": [], "n": ["brain_n_assumption"], "assumptions": ["bulk upper arm to muscle binding", "g=0.9", "uniform n=1.4"]},
        {"tissue_id": 6, "mua": ["damagatla_2026_forehead_mua"], "musp": ["damagatla_2026_forehead_musp"], "g": [], "n": ["brain_n_assumption"], "assumptions": ["bulk forehead to composite binding", "g=0.9", "uniform n=1.4"]},
        {"tissue_id": 7, "mua": ["bashkatov_2006_skull_mua_digitized"], "musp": ["bashkatov_2006_skull_musp"], "g": ["bashkatov_2006_fixed_g"], "n": ["brain_n_assumption"], "assumptions": ["intact cortical cranium to atlas skull", "uniform n=1.4"]},
        {"tissue_id": 9, "mua": ["bashkatov_2005_fat_mua_digitized"], "musp": ["bashkatov_2005_fat_musp"], "g": ["bashkatov_2005_fixed_g"], "n": ["brain_n_assumption"], "assumptions": ["shared_adipose_proxy_assumption", "uniform n=1.4"]},
        {"tissue_id": 10, "mua": ["shapey_2022_dura_mua"], "musp": ["shapey_2022_dura_musp"], "g": ["shapey_2022_fixed_g_085"], "n": ["shapey_2022_fixed_n_140"], "assumptions": ["ex vivo to atlas binding", "fixed inversion g/n"]},
        {"tissue_id": 11, "mua": ["kothuri_2025_bone_table"], "musp": ["kothuri_2025_bone_table"], "g": [], "n": ["brain_n_assumption"], "assumptions": ["tibial frozen marrow to cranial label", "g=0.9", "uniform n=1.4"]},
        {"tissue_id": 12, "mua": ["friebel_2006_blood_mua_oxy_hct42"], "musp": ["friebel_2006_blood_musp_oxy_hct42"], "g": ["friebel_2006_blood_g_oxy_hct42"], "n": ["brain_n_assumption"], "assumptions": ["effective intravascular blood binding", "uniform n=1.4"]},
    ]


def generate_provisional_optics(project_root: Path) -> dict[Path, dict[str, Any]]:
    """Return every generated payload keyed by project-relative output path."""

    project_root = project_root.resolve()
    records = _ledger_records(project_root)
    kothuri = _kothuri_values(project_root)
    central = _central(records, kothuri)
    variants = _variants(central, records, kothuri)
    payloads: dict[Path, dict[str, Any]] = {CENTRAL_PATH: central}
    for scenario, metadata in variants:
        payloads[Path(metadata["path"])] = scenario

    manifest = {
        "binding_policy": "inputs/anatomy/colin27_2008/optical_binding_policy_1070.md",
        "central_path": CENTRAL_PATH.as_posix(),
        "field_provenance": _field_provenance(),
        "generation_script": "src/mcx_project/provisional_optics.py",
        "production_eligible": False,
        "production_template": "inputs/optical_properties/production_1070_tbd.json",
        "scenario_set_id": "provisional_1070_v1",
        "scientific_status": "provisional",
        "status_note": "Runnable assumption-explicit research scenarios; not measured or production-nominal tissue tables.",
        "variant_count": len(variants),
        "variants": [metadata for _, metadata in variants],
        "wavelength_nm": 1070.0,
    }
    payloads[MANIFEST_PATH] = manifest
    return payloads


def build_provisional_optics(project_root: Path, *, check: bool = False) -> dict[str, Any]:
    """Write or freshness-check the provisional scenario set."""

    project_root = project_root.resolve()
    payloads = generate_provisional_optics(project_root)
    stale: list[str] = []
    for relative, payload in payloads.items():
        path = project_root / relative
        expected = _json_text(payload)
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                stale.append(relative.as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")

    if stale:
        raise InputValidationError(
            "provisional optical scenario outputs are stale or missing:\n- "
            + "\n- ".join(stale)
        )

    validate_json(project_root / MANIFEST_SCHEMA, project_root / MANIFEST_PATH, require_complete=True)
    for relative in payloads:
        if relative == MANIFEST_PATH:
            continue
        validate_json(project_root / OPTICAL_SCHEMA, project_root / relative, require_complete=True)

    return {
        "central": CENTRAL_PATH.as_posix(),
        "mode": "check" if check else "write",
        "production_eligible": False,
        "scenario_set_id": "provisional_1070_v1",
        "status": "valid",
        "variants": len(payloads) - 2,
    }
