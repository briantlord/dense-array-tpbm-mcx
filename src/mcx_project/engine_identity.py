"""Enforce the executable and selected GPU recorded by a frozen run."""

import re
from typing import Any

from .validation import InputValidationError


def validate_engine_identity(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    match = re.search(r"executable_sha256=([a-f0-9]{64})", expected.get("build", ""))
    expected_hash = expected.get("executable_sha256") or (match.group(1) if match else None)
    if expected_hash is None:
        raise InputValidationError("new execution requires an explicit frozen executable SHA-256; prepare a versioned environment binding")
    if actual.get("executable_sha256") != expected_hash:
        raise InputValidationError("MCX executable checksum does not match frozen engine identity")
    expected_version = expected.get("engine_version")
    actual_version = actual.get("engine_version", "")
    if expected_version != actual_version:
        # Older bindings record only the release tag; the hash still fixes the binary.
        if not (expected_version and re.fullmatch(r"v\d{4}\.\d+", expected_version)
                and re.search(r"(?<!\w)" + re.escape(expected_version) + r"(?![\w.])", actual_version)):
            raise InputValidationError("MCX version does not match frozen engine identity")
    expected_gpu = expected.get("gpu") or expected.get("device")
    if not expected_gpu or actual.get("gpu") != expected_gpu:
        raise InputValidationError("selected GPU does not match frozen engine identity")
    if actual.get("selected_device") != 1:
        raise InputValidationError("standalone execution must explicitly select device 1")
