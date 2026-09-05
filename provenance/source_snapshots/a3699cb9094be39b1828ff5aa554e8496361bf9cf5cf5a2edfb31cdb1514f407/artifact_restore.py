"""Restore absent artifacts from a mirror without replacing local evidence."""

import os
from pathlib import Path
import shutil
import tempfile

from .hashing import sha256_file
from .provenance import project_path
from .validation import InputValidationError


def verify_or_restore(root: Path, records: list[dict], source_root: Path | None = None) -> dict:
    counts = {"verified": 0, "restored": 0, "missing": 0}
    for record in records:
        destination = project_path(root, record["path"])
        expected = record["sha256"]
        if destination.exists():
            if sha256_file(destination) != expected:
                raise InputValidationError(f"existing artifact checksum mismatch; not overwritten: {record['path']}")
            counts["verified"] += 1
            continue
        if source_root is None:
            counts["missing"] += 1
            continue
        source = project_path(source_root, record["path"])
        if not source.is_file() or sha256_file(source) != expected:
            raise InputValidationError(f"restore source missing or checksum mismatch: {record['path']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".restore-", dir=destination.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            shutil.copyfile(source, temporary)
            if sha256_file(temporary) != expected:
                raise InputValidationError("restored bytes do not match expected checksum")
            # Hard-link publication is atomic and refuses an existing destination.
            os.link(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        counts["restored"] += 1
    return counts
