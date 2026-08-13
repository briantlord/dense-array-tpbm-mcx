"""Command-line entry point for validation and engine checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .opencl import (
    engine_version,
    gpuinfo,
    package_version,
    synthetic_smoke_from_config,
)
from .preflight import preflight_manifest
from .validation import InputValidationError, load_json, validate_json


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "__dict__"):
        return vars(value)
    return repr(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcx-project")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate one JSON input")
    validate.add_argument("schema", type=Path)
    validate.add_argument("instance", type=Path)
    validate.add_argument("--require-complete", action="store_true")

    preflight = commands.add_parser(
        "preflight", help="validate a run manifest and every referenced artifact"
    )
    preflight.add_argument("manifest", type=Path)
    preflight.add_argument("--project-root", type=Path, default=Path.cwd())

    commands.add_parser("probe-opencl", help="list PMCXCL OpenCL devices")

    smoke = commands.add_parser(
        "smoke-opencl", help="preflight and run a manifest-locked synthetic smoke test"
    )
    smoke.add_argument("manifest", type=Path)
    smoke.add_argument("--project-root", type=Path, default=Path.cwd())
    smoke.add_argument("--output", type=Path)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    try:
        if arguments.command == "validate":
            validate_json(
                arguments.schema,
                arguments.instance,
                require_complete=arguments.require_complete,
            )
            print(f"valid: {arguments.instance}")
            return 0

        if arguments.command == "preflight":
            report = preflight_manifest(arguments.manifest, arguments.project_root)
            print(
                json.dumps(
                    {
                        "status": "valid",
                        "run_id": report.run_id,
                        "manifest": str(report.manifest),
                        "artifacts_validated": report.artifacts_validated,
                        "checksums_verified": report.checksums_verified,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if arguments.command == "probe-opencl":
            payload = {
                "pmcxcl_version": package_version(),
                "mcxcl_engine_version": engine_version(),
                "devices": gpuinfo(),
            }
        else:
            preflight_manifest(arguments.manifest, arguments.project_root)
            manifest = load_json(arguments.manifest)
            configuration_path = (
                arguments.project_root
                / manifest["inputs"]["engine_configuration"]["path"]
            )
            payload = synthetic_smoke_from_config(load_json(configuration_path))

        rendered = json.dumps(payload, indent=2, sort_keys=True, default=_json_default)
        print(rendered)
        if arguments.command == "smoke-opencl" and arguments.output:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(rendered + "\n", encoding="utf-8")
        return 0
    except (InputValidationError, RuntimeError, ValueError) as error:
        print(f"error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
