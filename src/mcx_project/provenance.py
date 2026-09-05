"""Content-addressed source recovery and provenance for new analyses.

Historical records keep their original hashes. A snapshot is usable only when
its bytes match that recorded hash; its mere existence is insufficient.
"""

from __future__ import annotations

import importlib.metadata
import re
import subprocess
from pathlib import Path

from .hashing import sha256_file
from .validation import InputValidationError


def project_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise InputValidationError(f"provenance path escapes project: {relative}")
    return path


def resolve_recorded_code(root: Path, record: dict) -> Path:
    expected = record["sha256"]
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise InputValidationError("invalid recorded source checksum")
    current = project_path(root, record["path"])
    archived = root / "provenance/source_snapshots" / expected / current.name
    for path in (current, archived):
        if path.is_file() and sha256_file(path) == expected:
            return path
    raise InputValidationError(f"no exact source matches recorded checksum: {record['path']}")


def snapshot_source(root: Path, path: Path) -> dict:
    path = path.resolve()
    relative = path.relative_to(root.resolve()).as_posix()
    digest = sha256_file(path)
    snapshot = root / "provenance/source_snapshots" / digest / path.name
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.exists():
        if sha256_file(snapshot) != digest:
            raise InputValidationError(f"source snapshot was modified: {snapshot}")
    else:
        with snapshot.open("xb") as stream:
            stream.write(path.read_bytes())
    return {"path": relative, "sha256": digest,
            "snapshot": snapshot.relative_to(root).as_posix()}


def capture_code(root: Path, entrypoint: Path, arguments: list[str], *, shared: tuple[Path, ...] = ()) -> dict:
    root = root.resolve()
    # Capture all small project modules, avoiding an incomplete imported-module list.
    paths = sorted({entrypoint.resolve(), *(p.resolve() for p in shared),
                    *[p.resolve() for p in (root / "src/mcx_project").glob("*.py")]})
    sources = [snapshot_source(root, path) for path in paths]
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
    return {
        "contract_version": 1,
        "entrypoint": entrypoint.resolve().relative_to(root).as_posix(),
        "arguments": arguments,
        "sources": sources,
        "git_revision": revision.stdout.strip() if revision.returncode == 0 else None,
        "git_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
        "environment_lock": {"path": "uv.lock", "sha256": sha256_file(root / "uv.lock")},
        "installed_versions": {name: importlib.metadata.version(name)
                               for name in ("numpy", "scipy", "nibabel", "pillow", "jsonschema")},
    }
