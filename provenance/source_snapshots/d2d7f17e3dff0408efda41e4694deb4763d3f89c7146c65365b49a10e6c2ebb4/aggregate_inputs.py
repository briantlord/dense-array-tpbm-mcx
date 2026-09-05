"""Validate the single-source records used for a direct equal-weight aggregate."""

from pathlib import Path

import nibabel as nib
import numpy as np

from .geometry import validate_tissue_intersection, validate_volume_geometry
from .hashing import sha256_file
from .preflight import preflight_manifest
from .provenance import project_path
from .validation import InputValidationError, load_json


def load_aggregate_inputs(root: Path, index_path: Path) -> tuple[list[dict], np.ndarray]:
    index = load_json(index_path)
    configurations = []
    emitters = set()
    for number, row in enumerate(index["runs"], 1):
        path = project_path(root, row["configuration_path"])
        if sha256_file(path) != row["configuration_sha256"]:
            raise InputValidationError("aggregate configuration checksum mismatch")
        manifest_path = project_path(root, row["manifest_path"])
        preflight_manifest(manifest_path, root)
        manifest = load_json(manifest_path)
        if manifest["inputs"]["engine_configuration"]["sha256"] != row["configuration_sha256"]:
            raise InputValidationError("basis index and manifest configuration disagree")
        config = load_json(path)
        emitter = config["source"]["emitter_id"]
        if emitter in emitters or emitter != row["emitter_id"]:
            raise InputValidationError("aggregate requires one record per unique emitter")
        emitters.add(emitter)
        if configurations:
            for key in ("volume", "properties_mm", "time_gates_s", "isnormalize", "outputtype"):
                if config[key] != configurations[0][key]:
                    raise InputValidationError(f"aggregate source configurations differ in {key}")
        configurations.append(config)
        if number == 1 or number % 50 == 0:
            print(f"validated aggregate source {number}/{len(index['runs'])}", flush=True)
    if not configurations:
        raise InputValidationError("empty aggregate")
    base = configurations[0]
    image = nib.load(project_path(root, base["volume"]["path"]))
    validate_volume_geometry(image, base)
    raw = np.asarray(image.dataobj)
    if not np.isfinite(raw).all() or np.any(raw != np.floor(raw)) or raw.min() < 0 or raw.max() > 255:
        raise InputValidationError("volume must contain integer labels in [0,255]")
    labels = raw.astype(np.uint8)
    for config in configurations:
        validate_tissue_intersection(labels, config["source"])
    return configurations, labels
