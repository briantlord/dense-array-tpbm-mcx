from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_targeted_penetration_tallies",
    ROOT / "scripts" / "run_targeted_penetration_tallies.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_optical_scenario_replaces_media_without_mutating_basis() -> None:
    basis = {
        "properties_mm": [
            [0.0, 0.0, 1.0, 1.0],
            [0.1, 1.0, 0.9, 1.4],
            [0.2, 2.0, 0.8, 1.4],
        ]
    }
    scenario = {
        "coefficient_unit": "mm^-1",
        "tissues": [
            {"tissue_id": 0, "mua_mm-1": 0.0, "mus_mm-1": 0.0, "g": 0.0, "n": 1.0},
            {"tissue_id": 1, "mua_mm-1": 0.1, "mus_mm-1": 1.0, "g": 0.9, "n": 1.4},
            {
                "tissue_id": 2,
                "mua_mm-1": 0.02,
                "mus_mm-1": 8.0,
                "g": 0.89,
                "n": 1.37,
            }
        ],
    }

    updated = MODULE.apply_optical_properties(basis, scenario)

    assert updated["properties_mm"][2] == [0.02, 8.0, 0.89, 1.37]
    assert updated["properties_mm"][1] == basis["properties_mm"][1]
    assert basis["properties_mm"][2] == [0.2, 2.0, 0.8, 1.4]


def test_sensitivity_overlay_changes_only_declared_tissue() -> None:
    scenario = {
        "scenario_id": "central",
        "tissues": [
            {"tissue_id": 6, "mua_mm-1": 0.04, "notes": "fixed"},
            {"tissue_id": 7, "mua_mm-1": 0.02, "notes": "central"},
        ],
    }

    updated = MODULE.apply_tissue_overrides(
        scenario,
        [
            {
                "tissue_id": 7,
                "mua_mm-1": 0.004,
                "notes": "low attenuation",
            }
        ],
    )

    assert updated["tissues"][0] == scenario["tissues"][0]
    assert updated["tissues"][1]["mua_mm-1"] == 0.004
    assert updated["tissues"][1]["notes"] == "low attenuation"
    assert scenario["tissues"][1]["mua_mm-1"] == 0.02


def test_optical_scenario_fails_closed_on_unresolved_value() -> None:
    with pytest.raises(ValueError, match="unresolved"):
        MODULE.apply_optical_properties(
            {"properties_mm": [[0.0, 0.0, 1.0, 1.0]]},
            {
                "coefficient_unit": "mm^-1",
                "tissues": [
                    {
                        "tissue_id": 0,
                        "mua_mm-1": "TBD",
                        "mus_mm-1": 0.0,
                        "g": 0.0,
                        "n": 1.0,
                    }
                ],
            },
        )
