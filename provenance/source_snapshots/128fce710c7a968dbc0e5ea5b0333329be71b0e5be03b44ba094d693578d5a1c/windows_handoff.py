"""Environment-bound preparation for versioned Windows OpenCL handoffs."""

from __future__ import annotations

import copy
import json
import platform
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .standalone import probe_mcxcl
from .validation import InputValidationError, load_json, validate_json


SOURCE_PLAN = Path("configs/surrogate_yue277_1070_basis_v1.json")
SOURCE_TEMPLATE = Path("runs/surrogate_yue277_1070_v1/template_manifest.json")


@dataclass(frozen=True)
class WindowsOpenCLTarget:
    """Names and exact device identity for an immutable environment binding."""

    device: str
    environment_id: str
    environment_record: Path
    template_manifest: Path
    basis_plan: Path
    config_root: str
    run_root: str
    basis_set_id: str


RTX3080_TARGET = WindowsOpenCLTarget(
    device="NVIDIA GeForce RTX 3080",
    environment_id="windows_rtx3080_opencl_v1",
    environment_record=Path("environment/windows_rtx3080_opencl_v1.json"),
    template_manifest=Path(
        "runs/surrogate_yue277_1070_windows_opencl_v1/template_manifest.json"
    ),
    basis_plan=Path("configs/surrogate_yue277_1070_windows_opencl_basis_v1.json"),
    config_root="configs/generated/surrogate_yue277_1070_windows_opencl_basis_v1",
    run_root="runs/surrogate_yue277_1070_windows_opencl_basis_v1",
    basis_set_id="surrogate_yue277_1070_windows_opencl_basis_v1",
)

RTX3080TI_TARGET = WindowsOpenCLTarget(
    device="NVIDIA GeForce RTX 3080 Ti",
    environment_id="windows_rtx3080ti_opencl_v1",
    environment_record=Path("environment/windows_rtx3080ti_opencl_v1.json"),
    template_manifest=Path(
        "runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_v1/template_manifest.json"
    ),
    basis_plan=Path(
        "configs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1.json"
    ),
    config_root=(
        "configs/generated/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1"
    ),
    run_root="runs/surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1",
    basis_set_id="surrogate_yue277_1070_windows_rtx3080ti_opencl_basis_v1",
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _payload_sha256(value: Any) -> str:
    return sha256(_json_bytes(value)).hexdigest()


def _write_immutable(path: Path, value: Any) -> None:
    rendered = _json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != rendered:
        raise RuntimeError(f"refusing to replace environment-bound artifact: {path}")
    if not path.exists():
        path.write_bytes(rendered)


def _device_pattern(device: str) -> re.Pattern[str]:
    tokens = [re.escape(token) for token in device.split()]
    pattern = r"\s+".join(tokens)
    if device == RTX3080_TARGET.device:
        # A substring check would incorrectly bind an RTX 3080 Ti as an RTX 3080.
        pattern += r"(?!\s+Ti\b)"
    return re.compile(pattern, re.IGNORECASE)


def _require_supported_probe(
    probe: dict[str, Any], target: WindowsOpenCLTarget
) -> None:
    required = {
        "engine_version",
        "executable",
        "executable_sha256",
        "device_report",
        "platform",
    }
    missing = required - probe.keys()
    if missing:
        raise InputValidationError(
            "Windows engine probe is missing: " + ", ".join(sorted(missing))
        )
    if not re.fullmatch(r"[a-f0-9]{64}", str(probe["executable_sha256"])):
        raise InputValidationError("Windows MCX-CL executable hash is invalid")
    if "2025.10" not in str(probe["engine_version"]):
        raise InputValidationError(
            "Windows handoff requires MCX-CL v2025.10 to match the M4 checkpoint"
        )
    if not _device_pattern(target.device).search(str(probe["device_report"])):
        raise InputValidationError(
            "MCX-CL --listgpu did not identify the exact target device "
            f"{target.device}; do not bind the run plan"
        )
    if "windows" not in str(probe["platform"]).lower():
        raise InputValidationError("Windows handoff probe does not report Windows")


def build_windows_opencl_payloads(
    project_root: Path,
    probe: dict[str, Any],
    *,
    code_revision: str,
    created_at: str,
    target: WindowsOpenCLTarget = RTX3080_TARGET,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build, but do not write, the environment record, template, and basis plan."""

    root = project_root.resolve()
    _require_supported_probe(probe, target)
    if not re.fullmatch(r"[a-f0-9]{40,64}", code_revision):
        raise InputValidationError("code revision must be a full hexadecimal Git hash")

    source_template = load_json(root / SOURCE_TEMPLATE)
    source_plan = load_json(root / SOURCE_PLAN)
    template = copy.deepcopy(source_template)
    template["created_at"] = created_at
    template["code"] = {
        "repository": source_template["code"]["repository"],
        "revision": code_revision,
        "dirty": False,
    }
    template["engine"] = copy.deepcopy(source_template["engine"])
    template["engine"].update(
        {
            "backend": "opencl",
            "binding": "mcxcl_cli",
            "binding_version": str(probe["engine_version"]),
            "build": (
                "official Windows MCX-CL v2025.10 binary; executable_sha256="
                + str(probe["executable_sha256"])
            ),
            "engine_version": str(probe["engine_version"]),
            "gpu": target.device,
            "runtime": str(probe["platform"]),
        }
    )
    timestamp = created_at.replace("-", "").replace(":", "")
    timestamp = timestamp.replace("T", "t").replace("Z", "z")
    template["run_id"] = (
        f"{template['scenario_id']}__{timestamp}__"
        f"{template['engine']['configuration_sha256'][:8]}"
    )

    plan = copy.deepcopy(source_plan)
    plan.update(
        {
            "basis_set_id": target.basis_set_id,
            "code_dirty": False,
            "code_revision": code_revision,
            "config_root": target.config_root,
            "created_at": created_at,
            "engine_binding": "mcxcl_cli",
            "engine_build": template["engine"]["build"],
            "engine_version": str(probe["engine_version"]),
            "run_root": target.run_root,
            "template_manifest_path": target.template_manifest.as_posix(),
            "template_manifest_sha256": _payload_sha256(template),
        }
    )

    environment = {
        "environment_id": target.environment_id,
        "captured_at": created_at,
        "backend": "opencl",
        "binding": "mcxcl_cli",
        "device": target.device,
        "device_report": str(probe["device_report"]),
        "engine_version": str(probe["engine_version"]),
        "executable": str(probe["executable"]),
        "executable_sha256": str(probe["executable_sha256"]),
        "platform": str(probe["platform"]),
        "code_revision": code_revision,
        "source_plan": SOURCE_PLAN.as_posix(),
        "source_plan_sha256": _payload_sha256(source_plan),
        "scientific_status": "provisional_yue_derived_surrogate_not_target_hardware",
    }
    return environment, template, plan


def prepare_windows_opencl_handoff(
    project_root: Path,
    binary: Path,
    *,
    target: WindowsOpenCLTarget = RTX3080_TARGET,
) -> dict[str, Any]:
    """Probe a real Windows MCX-CL install and write a distinct immutable plan."""

    root = project_root.resolve()
    if platform.system() != "Windows":
        raise RuntimeError("the Windows OpenCL handoff generator must run on Windows")
    binary = binary.expanduser().resolve()
    if not binary.is_file():
        raise RuntimeError(f"MCX-CL executable is missing: {binary}")

    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if status:
        raise RuntimeError(
            "the repository must be clean before binding the Windows execution plan"
        )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    probe = probe_mcxcl(binary)
    probe["platform"] = platform.platform()
    created_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    environment, template, plan = build_windows_opencl_payloads(
        root,
        probe,
        code_revision=revision,
        created_at=created_at,
        target=target,
    )

    _write_immutable(root / target.environment_record, environment)
    _write_immutable(root / target.template_manifest, template)
    _write_immutable(root / target.basis_plan, plan)
    validate_json(
        root / "schemas/run_manifest.schema.json", root / target.template_manifest
    )
    validate_json(
        root / "schemas/basis_plan.schema.json",
        root / target.basis_plan,
        require_complete=True,
    )
    return {
        "status": "prepared_not_executed",
        "environment_record": target.environment_record.as_posix(),
        "template_manifest": target.template_manifest.as_posix(),
        "basis_plan": target.basis_plan.as_posix(),
        "next_gate": "prepare manifests, then run the one-source backend-equivalence check",
    }


def prepare_windows_rtx3080ti_opencl_handoff(
    project_root: Path, binary: Path
) -> dict[str, Any]:
    """Bind the versioned RTX 3080 Ti replacement plan."""

    return prepare_windows_opencl_handoff(
        project_root, binary, target=RTX3080TI_TARGET
    )
