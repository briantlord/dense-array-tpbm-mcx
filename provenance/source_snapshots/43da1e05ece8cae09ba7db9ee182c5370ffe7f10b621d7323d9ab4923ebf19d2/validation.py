"""JSON Schema validation and fail-closed completeness checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


class InputValidationError(ValueError):
    """Raised when an input fails structural or completeness validation."""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        try:
            return json.load(stream)
        except json.JSONDecodeError as error:
            raise InputValidationError(f"invalid JSON in {path}: {error}") from error


def _tbd_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(_tbd_paths(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_tbd_paths(child, f"{path}[{index}]"))
    elif isinstance(value, str) and value.strip().upper() == "TBD":
        found.append(path)
    return found


def validate_json(
    schema_path: Path, instance_path: Path, *, require_complete: bool = False
) -> None:
    schema = load_json(schema_path)
    instance = load_json(instance_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        details = "\n".join(
            f"- ${''.join(f'[{part!r}]' for part in error.path)}: {error.message}"
            for error in errors
        )
        raise InputValidationError(f"schema validation failed:\n{details}")

    if require_complete:
        unresolved = _tbd_paths(instance)
        if unresolved:
            raise InputValidationError(
                "unresolved TBD values block complete validation:\n- "
                + "\n- ".join(unresolved)
            )
