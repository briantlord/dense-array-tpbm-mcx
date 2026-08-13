import json
from pathlib import Path

import pytest

from mcx_project.validation import InputValidationError, validate_json


ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_emitter_geometry_is_complete() -> None:
    validate_json(
        ROOT / "schemas/emitter_geometry.schema.json",
        ROOT / "inputs/synthetic_test_only/emitter_geometry.json",
        require_complete=True,
    )


def test_synthetic_optical_properties_are_complete() -> None:
    validate_json(
        ROOT / "schemas/optical_properties.schema.json",
        ROOT / "inputs/synthetic_test_only/optical_properties.json",
        require_complete=True,
    )


def test_production_template_fails_closed() -> None:
    with pytest.raises(InputValidationError, match="TBD"):
        validate_json(
            ROOT / "schemas/optical_properties.schema.json",
            ROOT / "inputs/optical_properties/production_1070_tbd.json",
            require_complete=True,
        )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda value: value.update(position_unit="cm"), "'mm' was expected"),
        (
            lambda value: value["emitters"][0].update(duty_cycle=1.1),
            "greater than the maximum of 1",
        ),
        (
            lambda value: value["emitters"][0].pop("provenance"),
            "'provenance' is a required property",
        ),
    ],
)
def test_emitter_schema_rejects_units_duty_and_missing_provenance(
    tmp_path: Path, mutation, expected: str
) -> None:
    value = json.loads(
        (ROOT / "inputs/synthetic_test_only/emitter_geometry.json").read_text()
    )
    mutation(value)
    instance = tmp_path / "emitter.json"
    instance.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(InputValidationError, match=expected):
        validate_json(ROOT / "schemas/emitter_geometry.schema.json", instance)
