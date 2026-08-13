"""File-based adapter for the official standalone MCX-CL executable."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import nibabel as nib
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


def render_mcxcl_input(
    config: dict[str, Any], session_id: str, *, volume_file: str | None = None
) -> dict[str, Any]:
    volume = config["volume"]
    if volume["generator"] == "label_volume_nifti" and volume_file is None:
        raise InputValidationError("label_volume_nifti requires a prepared volume file")
    output_type = {"flux": "x", "fluence": "f", "energy": "e"}[
        config["outputtype"]
    ]
    domain = {
        "MediaFormat": "byte",
        "LengthUnit": 1.0,
        "Dim": volume["shape_voxels"],
        "OriginType": 1,
        "Media": [
            {"mua": row[0], "mus": row[1], "g": row[2], "n": row[3]}
            for row in config["properties_mm"]
        ],
    }
    document = {
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
        "Domain": domain,
        "Optode": {
            "Source": {
                "Type": config["source"]["type"],
                "Pos": config["source"]["position_voxels"],
                "Dir": config["source"]["direction"],
            },
            "Detector": [],
        },
    }
    if volume["generator"] == "homogeneous_cube":
        document["Shapes"] = [
            {
                "Grid": {
                    "Tag": volume["label"],
                    "Size": volume["shape_voxels"],
                }
            }
        ]
    elif volume["generator"] == "label_volume_nifti":
        domain["VolumeFile"] = volume_file
    else:
        raise InputValidationError(
            f"unsupported volume generator: {volume['generator']}"
        )
    return document


def _prepare_label_volume(
    config: dict[str, Any], run_directory: Path, project_root: Path
) -> tuple[str, str]:
    volume = config["volume"]
    source = (project_root / volume["path"]).resolve()
    if not source.is_relative_to(project_root.resolve()) or not source.is_file():
        raise InputValidationError("label volume path is missing or escapes project root")
    if sha256_file(source) != volume["sha256"]:
        raise InputValidationError("label volume checksum mismatch")

    image = nib.load(source)
    labels = np.asarray(image.dataobj)
    if labels.shape != tuple(volume["shape_voxels"]):
        raise InputValidationError("label volume shape does not match configuration")
    if not np.all(np.isfinite(labels)) or not np.all(labels == np.rint(labels)):
        raise InputValidationError("label volume must contain finite integer labels")
    if float(np.min(labels)) < 0 or float(np.max(labels)) >= len(config["properties_mm"]):
        raise InputValidationError("label volume contains an undefined medium index")

    prepared = run_directory / "volume.uint8.bin"
    prepared.write_bytes(np.asarray(labels, dtype=np.uint8).tobytes(order="F"))
    return prepared.name, sha256_file(prepared)


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
    config: dict[str, Any],
    run_directory: Path,
    binary: Path,
    *,
    project_root: Path | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Run one configuration using file-based MCX-CL output."""

    session_id = "mcx_field"
    input_path = run_directory / "mcx_input.json"
    log_path = run_directory / "mcxcl.log"
    output_path = run_directory / f"{session_id}.jnii"
    prepared_volume: tuple[str, str] | None = None
    if config["volume"]["generator"] == "label_volume_nifti":
        if project_root is None:
            raise InputValidationError(
                "project_root is required for label_volume_nifti"
            )
        prepared_volume = _prepare_label_volume(config, run_directory, project_root)
    input_path.write_text(
        json.dumps(
            render_mcxcl_input(
                config,
                session_id,
                volume_file=prepared_volume[0] if prepared_volume else None,
            ),
            indent=2,
            sort_keys=True,
        )
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
    artifacts = [
        {"kind": "qc", "path": input_path.name},
        {"kind": "log", "path": log_path.name},
        {"kind": "fluence", "path": output_path.name, "primary_field": True},
    ]
    if prepared_volume is not None:
        artifacts.insert(0, {"kind": "qc", "path": prepared_volume[0]})
    return field, {
        "backend": "mcxcl_cli",
        "engine_version": version,
        "executable_sha256": sha256_file(binary),
        "input_sha256": sha256_file(input_path),
        "jnifti_sha256": sha256_file(output_path),
        "log_sha256": sha256_file(log_path),
        "absorbed_energy_percent": parse_absorbed_energy_percent(combined_log),
        "prepared_volume_sha256": prepared_volume[1] if prepared_volume else None,
        "_artifacts": artifacts,
    }
