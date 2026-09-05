"""Command-line entry point for validation and engine checks."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from .basis import (
    BasisExecutionError,
    BasisPreparationError,
    execute_basis_run,
    prepare_basis_plan,
)
from .optical_ledger import audit_optical_ledger
from .preflight import preflight_manifest
from .provisional_optics import build_provisional_optics
from .provisional_pilot import build_provisional_pilot
from .standalone import probe_mcxcl, resolve_mcxcl_binary, standalone_field_from_config
from .surrogate_1070 import build_surrogate_1070, freeze_surrogate_basis_plan
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

    audit_optics = commands.add_parser(
        "audit-optical-ledger",
        help="cross-check the 1070-nm source ledger, anatomy labels, and production gate",
    )
    audit_optics.add_argument("--project-root", type=Path, default=Path.cwd())

    build_optics = commands.add_parser(
        "build-provisional-optics",
        help="build or freshness-check assumption-explicit 1070-nm scenarios",
    )
    build_optics.add_argument("--project-root", type=Path, default=Path.cwd())
    build_optics.add_argument("--check", action="store_true")

    build_pilot = commands.add_parser(
        "build-provisional-pilot",
        help="build or freshness-check the non-production Colin27 1070-nm pilot",
    )
    build_pilot.add_argument("--project-root", type=Path, default=Path.cwd())
    build_pilot.add_argument("--check", action="store_true")

    build_surrogate = commands.add_parser(
        "build-surrogate-1070",
        help="build or freshness-check the Yue-derived 277-source 1070-nm surrogate",
    )
    build_surrogate.add_argument("--project-root", type=Path, default=Path.cwd())
    build_surrogate.add_argument("--check", action="store_true")

    freeze_surrogate = commands.add_parser(
        "freeze-surrogate-basis-plan",
        help="freeze the 277-source surrogate plan after regional convergence passes",
    )
    freeze_surrogate.add_argument("--project-root", type=Path, default=Path.cwd())
    freeze_surrogate.add_argument("--check", action="store_true")

    preflight = commands.add_parser(
        "preflight", help="validate a run manifest and every referenced artifact"
    )
    preflight.add_argument("manifest", type=Path)
    preflight.add_argument("--project-root", type=Path, default=Path.cwd())

    prepare = commands.add_parser(
        "prepare-basis", help="generate immutable per-emitter configurations and manifests"
    )
    prepare.add_argument("plan", type=Path)
    prepare.add_argument("--project-root", type=Path, default=Path.cwd())

    execute = commands.add_parser(
        "execute-basis", help="execute one prepared synthetic basis run atomically"
    )
    execute.add_argument("manifest", type=Path)
    execute.add_argument("--project-root", type=Path, default=Path.cwd())

    commands.add_parser("probe-opencl", help="query the standalone MCX-CL engine")

    smoke = commands.add_parser(
        "smoke-opencl", help="preflight and run a manifest-locked synthetic smoke test"
    )
    smoke.add_argument("manifest", type=Path)
    smoke.add_argument("--project-root", type=Path, default=Path.cwd())
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

        if arguments.command == "audit-optical-ledger":
            report = audit_optical_ledger(arguments.project_root)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if arguments.command == "build-provisional-optics":
            report = build_provisional_optics(
                arguments.project_root, check=arguments.check
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if arguments.command == "build-provisional-pilot":
            report = build_provisional_pilot(
                arguments.project_root, check=arguments.check
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if arguments.command == "build-surrogate-1070":
            report = build_surrogate_1070(
                arguments.project_root, check=arguments.check
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if arguments.command == "freeze-surrogate-basis-plan":
            report = freeze_surrogate_basis_plan(
                arguments.project_root, check=arguments.check
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if arguments.command == "prepare-basis":
            index = prepare_basis_plan(arguments.plan, arguments.project_root)
            print(json.dumps(index, indent=2, sort_keys=True))
            return 0

        if arguments.command == "execute-basis":
            binary = resolve_mcxcl_binary(arguments.project_root)
            identity = probe_mcxcl(binary)

            def run_standalone(config: dict[str, Any], run_directory: Path):
                return standalone_field_from_config(
                    config,
                    run_directory,
                    binary,
                    project_root=arguments.project_root,
                    expected_identity=identity,
                )

            status = execute_basis_run(
                arguments.manifest,
                arguments.project_root,
                run_standalone,
                engine_probe=lambda: identity,
            )
            print(json.dumps({"status": status}, indent=2, sort_keys=True))
            return 0

        if arguments.command == "probe-opencl":
            payload = probe_mcxcl(resolve_mcxcl_binary(Path.cwd()))
        else:
            preflight_manifest(arguments.manifest, arguments.project_root)
            manifest = load_json(arguments.manifest)
            configuration_path = (
                arguments.project_root
                / manifest["inputs"]["engine_configuration"]["path"]
            )
            binary = resolve_mcxcl_binary(arguments.project_root)
            with tempfile.TemporaryDirectory(prefix="mcx-smoke-") as temporary:
                field, engine_summary = standalone_field_from_config(
                    load_json(configuration_path), Path(temporary), binary
                )
            engine_summary.pop("_artifacts", None)
            payload = {
                "backend": "mcxcl_cli",
                "configuration_id": load_json(configuration_path)["configuration_id"],
                "shape": list(field.shape),
                "minimum": float(field.min()),
                "maximum": float(field.max()),
                "standard_deviation": float(field.std(dtype="float64")),
                "sum": float(field.sum(dtype="float64")),
                "engine": engine_summary,
            }

        rendered = json.dumps(payload, indent=2, sort_keys=True, default=_json_default)
        print(rendered)
        return 0
    except (
        BasisExecutionError,
        BasisPreparationError,
        InputValidationError,
        RuntimeError,
        ValueError,
    ) as error:
        print(f"error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
