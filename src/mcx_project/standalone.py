"""File-based adapter for the official standalone MCX-CL executable."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from .hashing import sha256_file
from .validation import InputValidationError


def parse_absorbed_energy_percent(log: str) -> float | None:
    plain = re.sub(r"\x1b\[[0-9;]*m", "", log)
    match = re.search(r"absorbed:\s*([0-9.]+)%", plain)
    return float(match.group(1)) if match else None


def resolve_mcxcl_binary(project_root: Path) -> Path:
    configured = os.environ.get("MCXCL_BINARY")
    binary = Path(configured) if configured else project_root / ".local/bin/mcxcl"
    binary = binary.expanduser().resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError(
            f"standalone MCX-CL executable is unavailable at {binary}; "
            "run ./scripts/build_mcxcl.sh"
        )
    return binary


def probe_mcxcl(binary: Path) -> dict[str, Any]:
    version = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    devices = subprocess.run(
        [str(binary), "--listgpu"],
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "engine_version": version,
        "executable": str(binary),
        "executable_sha256": sha256_file(binary),
        "device_report": devices.stdout + devices.stderr,
    }


def render_mcxcl_input(config: dict[str, Any], session_id: str) -> dict[str, Any]:
    volume = config["volume"]
    if volume["generator"] != "homogeneous_cube":
        raise InputValidationError(
            "standalone synthetic adapter only supports homogeneous_cube"
        )
    output_type = {"flux": "x", "fluence": "f", "energy": "e"}[
        config["outputtype"]
    ]
    return {
        "Session": {
            "ID": session_id,
            "Photons": config["nphoton"],
            "RNGSeed": config["seed"],
            "DoSaveVolume": True,
            "DoNormalize": bool(config["isnormalize"]),
            "DoAutoThread": True,
            "DoPartialPath": False,
            "OutputFormat": "jnii",
            "OutputType": output_type,
        },
        "Forward": {
            "T0": config["time_gates_s"]["start"],
            "T1": config["time_gates_s"]["end"],
            "Dt": config["time_gates_s"]["step"],
        },
        "Domain": {
            "MediaFormat": "byte",
            "LengthUnit": 1.0,
            "Dim": volume["shape_voxels"],
            "OriginType": 1,
            "Media": [
                {"mua": row[0], "mus": row[1], "g": row[2], "n": row[3]}
                for row in config["properties_mm"]
            ],
        },
        "Optode": {
            "Source": {
                "Type": config["source"]["type"],
                "Pos": config["source"]["position_voxels"],
                "Dir": config["source"]["direction"],
            },
            "Detector": [],
        },
        "Shapes": [
            {
                "Grid": {
                    "Tag": volume["label"],
                    "Size": volume["shape_voxels"],
                }
            }
        ],
    }


def load_jnii_field(path: Path) -> np.ndarray:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    data = document.get("NIFTIData", {})
    if data.get("_ArrayType_") != "single":
        raise RuntimeError("MCX-CL JNIfTI output is not float32")
    if data.get("_ArrayZipType_") != "base64":
        raise RuntimeError("MCX-CL JNIfTI output does not use uncompressed base64")
    shape = tuple(int(item) for item in data["_ArraySize_"])
    raw = base64.b64decode(data["_ArrayZipData_"], validate=True)
    expected_bytes = int(np.prod(shape, dtype=np.int64)) * np.dtype("<f4").itemsize
    if len(raw) != expected_bytes:
        raise RuntimeError(
            f"MCX-CL JNIfTI byte count {len(raw)} does not match {expected_bytes}"
        )
    order = "C" if data.get("_ArrayOrder_", "c").lower() == "c" else "F"
    field = np.frombuffer(raw, dtype="<f4").reshape(shape, order=order)
    while field.ndim > 4 and field.shape[-1] == 1:
        field = field[..., 0]
    return np.asarray(field, dtype=np.float64)


def standalone_field_from_config(
    config: dict[str, Any], run_directory: Path, binary: Path
) -> tuple[np.ndarray, dict[str, Any]]:
    """Run one synthetic config using file-based MCX-CL output."""

    session_id = "mcx_field"
    input_path = run_directory / "mcx_input.json"
    log_path = run_directory / "mcxcl.log"
    output_path = run_directory / f"{session_id}.jnii"
    input_path.write_text(
        json.dumps(render_mcxcl_input(config, session_id), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [str(binary), "-f", input_path.name, "-Z", "2"],
        cwd=run_directory,
        capture_output=True,
        text=True,
        check=False,
    )
    combined_log = completed.stdout + completed.stderr
    log_path.write_text(combined_log, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"MCX-CL exited with status {completed.returncode}")
    if not output_path.is_file():
        raise RuntimeError("MCX-CL did not create the expected JNIfTI field")
    field = load_jnii_field(output_path)
    if field.size == 0 or not np.all(np.isfinite(field)) or np.any(field < 0):
        raise RuntimeError("standalone MCX-CL returned an invalid field")
    if float(np.max(field)) <= 0 or float(np.std(field, dtype=np.float64)) <= 0:
        raise RuntimeError("standalone MCX-CL returned a nonpositive or uniform field")

    version = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return field, {
        "backend": "mcxcl_cli",
        "engine_version": version,
        "executable_sha256": sha256_file(binary),
        "input_sha256": sha256_file(input_path),
        "jnifti_sha256": sha256_file(output_path),
        "log_sha256": sha256_file(log_path),
        "absorbed_energy_percent": parse_absorbed_energy_percent(combined_log),
        "_artifacts": [
            {"kind": "qc", "path": input_path.name},
            {"kind": "log", "path": log_path.name},
            {"kind": "fluence", "path": output_path.name, "primary_field": True},
        ],
    }
