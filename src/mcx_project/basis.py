"""Immutable preparation and atomic execution of per-emitter basis runs."""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .hashing import sha256_file
from .preflight import preflight_manifest
from .validation import InputValidationError, load_json, validate_json


class BasisPreparationError(RuntimeError):
    """Raised when immutable basis requests cannot be prepared safely."""


class BasisExecutionError(RuntimeError):
    """Raised when a basis execution cannot start or complete safely."""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_immutable_json(path: Path, value: Any) -> str:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != rendered:
            raise BasisPreparationError(f"refusing to replace immutable file: {path}")
    else:
        _atomic_json(path, value)
    return sha256_file(path)


def _project_path(project_root: Path, raw_path: str) -> Path:
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise BasisPreparationError(f"unsafe project-relative path: {raw_path}")
    root = project_root.resolve()
    resolved = (root / Path(*relative.parts)).resolve()
    if not resolved.is_relative_to(root):
        raise BasisPreparationError(f"path escapes project root: {raw_path}")
    return resolved


def deterministic_seed(basis_set_id: str, emitter_id: str, replicate: int) -> int:
    """Derive a nonzero signed-int32-safe seed from immutable identifiers."""

    if replicate < 1:
        raise ValueError("replicate must be positive")
    payload = f"{basis_set_id}\0{emitter_id}\0{replicate}".encode()
    # PMCXCL's Python boundary is unreliable above INT32_MAX even though MCX
    # prints the value as an unsigned seed. Constrain before serialization.
    seed = int.from_bytes(sha256(payload).digest()[:4], "big") & 0x7FFFFFFF
    return seed or 1


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not slug:
        raise BasisPreparationError(f"identifier cannot form a path slug: {value!r}")
    return slug


def _transformed_source(
    emitter: dict[str, Any], registration: dict[str, Any], anatomy: dict[str, Any]
) -> tuple[list[float], list[float]]:
    transform = np.asarray(registration["matrix_4x4"], dtype=np.float64)
    affine = np.asarray(anatomy["affine"], dtype=np.float64)
    helmet_position = np.asarray([*emitter["position_mm"], 1.0], dtype=np.float64)
    head_position = transform @ helmet_position
    voxel_position = np.linalg.inv(affine) @ head_position

    direction = transform[:3, :3] @ np.asarray(emitter["normal"], dtype=np.float64)
    direction_norm = float(np.linalg.norm(direction))
    if not np.isfinite(direction_norm) or direction_norm <= 0:
        raise BasisPreparationError(f"invalid transformed normal for {emitter['emitter_id']}")
    direction /= direction_norm
    return voxel_position[:3].tolist(), direction.tolist()


def prepare_basis_plan(plan_path: Path, project_root: Path) -> dict[str, Any]:
    """Create immutable per-emitter configurations and planned run manifests."""

    root = project_root.resolve()
    validate_json(root / "schemas/basis_plan.schema.json", plan_path, require_complete=True)
    plan = load_json(plan_path)
    if not plan["synthetic_test_only"]:
        raise BasisPreparationError(
            "basis preparation is currently enabled only for synthetic_test_only plans"
        )

    template_path = _project_path(root, plan["template_manifest_path"])
    if sha256_file(template_path) != plan["template_manifest_sha256"]:
        raise BasisPreparationError("template manifest checksum mismatch")
    preflight_manifest(template_path, root)
    template = load_json(template_path)
    if template["scenario_id"] != plan["scenario_id"]:
        raise BasisPreparationError("plan and template scenario IDs do not match")
    if template["scientific_status"] != "synthetic_test_only":
        raise BasisPreparationError("synthetic plan requires a synthetic template manifest")

    artifacts = {
        role: load_json(_project_path(root, reference["path"]))
        for role, reference in template["inputs"].items()
    }
    geometry = artifacts["emitter_geometry"]
    if plan["emitter_ids"] == "enabled":
        selected = [emitter for emitter in geometry["emitters"] if emitter["enabled"]]
    else:
        requested = set(plan["emitter_ids"])
        selected = [
            emitter
            for emitter in geometry["emitters"]
            if emitter["enabled"] and emitter["emitter_id"] in requested
        ]
        found = {emitter["emitter_id"] for emitter in selected}
        if found != requested:
            missing = ", ".join(sorted(requested - found))
            raise BasisPreparationError(f"requested emitters are missing or disabled: {missing}")
    if not selected:
        raise BasisPreparationError("basis plan selects no enabled emitters")

    timestamp = plan["created_at"].replace("-", "").replace(":", "")
    timestamp = timestamp.replace("T", "t").replace("Z", "z")
    base_config = artifacts["engine_configuration"]
    anatomy = artifacts["anatomy"]
    registration = artifacts["registration"]
    runs: list[dict[str, Any]] = []

    for emitter in selected:
        emitter_slug = _slug(emitter["emitter_id"])
        for replicate in range(1, plan["replicates"] + 1):
            seed = deterministic_seed(plan["basis_set_id"], emitter["emitter_id"], replicate)
            position, direction = _transformed_source(emitter, registration, anatomy)
            config = copy.deepcopy(base_config)
            config["configuration_id"] = (
                f"{plan['basis_set_id']}__{emitter_slug}__r{replicate:03d}"
            )
            config["nphoton"] = plan["photon_count"]
            config["seed"] = seed
            config["source"] = {
                "emitter_id": emitter["emitter_id"],
                "position_voxels": position,
                "direction": direction,
                "type": emitter["source_type"],
            }
            config_relative = (
                PurePosixPath(plan["config_root"])
                / emitter_slug
                / f"r{replicate:03d}.json"
            ).as_posix()
            config_path = _project_path(root, config_relative)
            config_hash = _write_immutable_json(config_path, config)
            validate_json(
                root / "schemas/engine_configuration.schema.json",
                config_path,
                require_complete=True,
            )

            manifest = copy.deepcopy(template)
            manifest["run_id"] = (
                f"{plan['scenario_id']}__{timestamp}__{config_hash[:8]}"
            )
            manifest["created_at"] = plan["created_at"]
            manifest["status"] = "planned"
            manifest["error"] = None
            manifest["code"] = {
                "repository": template["code"]["repository"],
                "revision": plan["code_revision"],
                "dirty": plan["code_dirty"],
            }
            manifest["source"] = {
                "emitter_id": emitter["emitter_id"],
                "source_model": emitter["source_type"],
                "normalization": template["source"]["normalization"],
            }
            manifest["execution"]["photon_count"] = plan["photon_count"]
            manifest["execution"]["seed"] = seed
            manifest["execution"]["replicate"] = replicate
            manifest["inputs"]["engine_configuration"] = {
                "artifact_id": config["configuration_id"],
                "id_field": "configuration_id",
                "path": config_relative,
                "schema_path": "schemas/engine_configuration.schema.json",
                "sha256": config_hash,
            }
            manifest["engine"]["configuration_sha256"] = config_hash
            manifest["outputs"] = []

            run_relative = (
                PurePosixPath(plan["run_root"])
                / emitter_slug
                / f"r{replicate:03d}"
            )
            manifest_relative = (run_relative / "manifest.json").as_posix()
            manifest_path = _project_path(root, manifest_relative)
            _write_immutable_json(manifest_path, manifest)
            preflight_manifest(manifest_path, root)
            runs.append(
                {
                    "emitter_id": emitter["emitter_id"],
                    "replicate": replicate,
                    "seed": seed,
                    "configuration_path": config_relative,
                    "configuration_sha256": config_hash,
                    "manifest_path": manifest_relative,
                    "run_id": manifest["run_id"],
                }
            )

    index = {
        "basis_set_id": plan["basis_set_id"],
        "plan_path": plan_path.resolve().relative_to(root).as_posix(),
        "plan_sha256": sha256_file(plan_path),
        "created_at": plan["created_at"],
        "runs": runs,
    }
    index_path = _project_path(root, PurePosixPath(plan["run_root"]).joinpath("index.json").as_posix())
    _write_immutable_json(index_path, index)
    return index


def _atomic_npy(path: Path, value: NDArray[np.float64]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            np.save(stream, value, allow_pickle=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def execute_basis_run(
    manifest_path: Path,
    project_root: Path,
    executor: Callable[[dict[str, Any]], tuple[NDArray[np.float64], dict[str, Any]]],
) -> str:
    """Execute one planned run atomically; return ``complete`` or ``skipped``."""

    root = project_root.resolve()
    manifest = load_json(manifest_path)
    if manifest["status"] == "complete":
        preflight_manifest(manifest_path, root)
        return "skipped"
    if manifest["status"] == "failed":
        raise BasisExecutionError(
            "failed runs are immutable; prepare a replacement with a new run ID"
        )
    if manifest["status"] == "running":
        raise BasisExecutionError("run is marked running; inspect it before retrying")
    if manifest["status"] not in {"planned", "failed"}:
        raise BasisExecutionError(f"unsupported run status: {manifest['status']}")
    preflight_manifest(manifest_path, root)

    run_directory = manifest_path.parent
    lock_path = run_directory / "run.lock"
    try:
        lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as error:
        raise BasisExecutionError(f"run is locked: {lock_path}") from error
    os.close(lock_descriptor)

    try:
        for protected in ("fluence.npy", "summary.json", "execution.json", "failure.json"):
            if (run_directory / protected).exists():
                raise BasisExecutionError(
                    f"refusing to overwrite an existing run artifact: {protected}"
                )
        manifest["status"] = "running"
        manifest["error"] = None
        _atomic_json(manifest_path, manifest)

        config_reference = manifest["inputs"]["engine_configuration"]
        config = load_json(_project_path(root, config_reference["path"]))
        started_at = _utc_now()
        field, engine_summary = executor(config)
        field = np.asarray(field, dtype=np.float64)
        if field.size == 0 or not np.all(np.isfinite(field)) or np.min(field) < -1e-20:
            raise BasisExecutionError("executor returned an invalid field")
        expected_shape = tuple(manifest["grid"]["shape_voxels"])
        if field.ndim not in {3, 4} or field.shape[:3] != expected_shape:
            raise BasisExecutionError(
                f"executor returned shape {field.shape}; expected {expected_shape} plus "
                "an optional time-gate axis"
            )
        field = np.maximum(field, 0.0)

        field_path = run_directory / "fluence.npy"
        summary_path = run_directory / "summary.json"
        execution_path = run_directory / "execution.json"
        _atomic_npy(field_path, field)
        summary = {
            "run_id": manifest["run_id"],
            "shape": list(field.shape),
            "minimum": float(np.min(field)),
            "maximum": float(np.max(field)),
            "sum": float(np.sum(field, dtype=np.float64)),
            "standard_deviation": float(np.std(field, dtype=np.float64)),
            "engine": engine_summary,
        }
        _atomic_json(summary_path, summary)
        _atomic_json(
            execution_path,
            {
                "run_id": manifest["run_id"],
                "started_at": started_at,
                "completed_at": _utc_now(),
                "status": "complete",
            },
        )
        manifest["outputs"] = [
            {
                "kind": "fluence",
                "path": field_path.resolve().relative_to(root).as_posix(),
                "sha256": sha256_file(field_path),
            },
            {
                "kind": "summary",
                "path": summary_path.resolve().relative_to(root).as_posix(),
                "sha256": sha256_file(summary_path),
            },
            {
                "kind": "log",
                "path": execution_path.resolve().relative_to(root).as_posix(),
                "sha256": sha256_file(execution_path),
            },
        ]
        manifest["status"] = "complete"
        manifest["error"] = None
        _atomic_json(manifest_path, manifest)
        preflight_manifest(manifest_path, root)
        return "complete"
    except Exception as error:
        if isinstance(error, BasisExecutionError) and manifest.get("status") != "running":
            raise
        failure_path = run_directory / "failure.json"
        _atomic_json(
            failure_path,
            {
                "run_id": manifest["run_id"],
                "failed_at": _utc_now(),
                "error_type": type(error).__name__,
                "message": str(error),
            },
        )
        manifest["status"] = "failed"
        manifest["error"] = f"{type(error).__name__}: {error}"
        manifest["outputs"] = [
            {
                "kind": "log",
                "path": failure_path.resolve().relative_to(root).as_posix(),
                "sha256": sha256_file(failure_path),
            }
        ]
        _atomic_json(manifest_path, manifest)
        raise BasisExecutionError(manifest["error"]) from error
    finally:
        lock_path.unlink(missing_ok=True)
