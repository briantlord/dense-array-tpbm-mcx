"""Coordinate and launch checks shared by preparation and execution."""

from typing import Any

import numpy as np

from .validation import InputValidationError


def transformed_source(emitter: dict[str, Any], registration: dict[str, Any],
                       anatomy: dict[str, Any]) -> tuple[list[float], list[float]]:
    transform = np.asarray(registration["matrix_4x4"], dtype=np.float64)
    affine = np.asarray(anatomy["affine"], dtype=np.float64)
    for name, matrix in (("registration", transform), ("anatomy affine", affine)):
        if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
            raise InputValidationError(f"{name} must be a finite 4 x 4 matrix")
        if not np.allclose(matrix[3], [0, 0, 0, 1], rtol=0, atol=1e-9):
            raise InputValidationError(f"{name} has an invalid homogeneous row")
    rotation = transform[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(rotation), 1):
        raise InputValidationError("registration must be a rigid right-handed transform")
    try:
        inverse = np.linalg.inv(affine)
    except np.linalg.LinAlgError as error:
        raise InputValidationError("anatomy affine is singular") from error
    position = (inverse @ transform @ np.asarray([*emitter["position_mm"], 1.0]))[:3]
    direction = inverse[:3, :3] @ rotation @ np.asarray(emitter["normal"], dtype=np.float64)
    norm = float(np.linalg.norm(direction))
    if not np.isfinite(position).all() or not np.isfinite(norm) or norm <= 0:
        raise InputValidationError("transformed source must be finite with a nonzero normal")
    return position.tolist(), (direction / norm).tolist()


def ray_box_interval(position, direction, shape) -> tuple[float, float]:
    position = np.asarray(position, dtype=np.float64)
    direction = np.asarray(direction, dtype=np.float64)
    shape = np.asarray(shape, dtype=np.float64)
    if position.shape != (3,) or direction.shape != (3,) or shape.shape != (3,):
        raise InputValidationError("source position, direction and grid require three components")
    if not np.isfinite(position).all() or not np.isfinite(direction).all():
        raise InputValidationError("source position and direction must be finite")
    if not np.isclose(np.linalg.norm(direction), 1, rtol=0, atol=1e-6):
        raise InputValidationError("engine source direction must be a unit vector")
    near, far = 0.0, float("inf")
    for origin, delta, size in zip(position, direction, shape):
        if abs(delta) < 1e-15:
            if not 0 <= origin < size:
                raise InputValidationError("source ray misses the volume")
        else:
            a, b = sorted((-origin / delta, (size - origin) / delta))
            near, far = max(near, a), min(far, b)
    if far <= near:
        raise InputValidationError("source ray misses the volume")
    return near, far


def validate_engine_geometry(config: dict[str, Any]) -> None:
    if config["source"]["type"] != "pencil":
        raise InputValidationError("only pencil sources are implemented; measured beam models require a new adapter")
    ray_box_interval(config["source"]["position_voxels"], config["source"]["direction"], config["volume"]["shape_voxels"])
    gates = config["time_gates_s"]
    values = [gates[key] for key in ("start", "end", "step")]
    if not np.isfinite(values).all() or not 0 <= values[0] < values[1] or not 0 < values[2] <= values[1] - values[0]:
        raise InputValidationError("time gates require finite start < end and a positive step within the window")


def validate_volume_geometry(image, config: dict[str, Any]) -> None:
    if not np.allclose(image.header.get_zooms()[:3], [1, 1, 1], rtol=0, atol=1e-6):
        raise InputValidationError("standalone adapter requires 1-mm isotropic voxels")
    spatial = np.asarray(image.affine[:3, :3])
    if not np.allclose(spatial.T @ spatial, np.eye(3), rtol=0, atol=1e-6):
        raise InputValidationError("standalone adapter requires orthogonal 1-mm voxel axes")
    if image.shape != tuple(config["volume"]["shape_voxels"]):
        raise InputValidationError("label volume shape does not match configuration")


def validate_tissue_intersection(labels: np.ndarray, source: dict[str, Any]) -> None:
    position = np.asarray(source["position_voxels"], dtype=float)
    direction = np.asarray(source["direction"], dtype=float)
    near, far = ray_box_interval(position, direction, labels.shape)
    # Exact voxel traversal: include every boundary crossing, even a grazed voxel.
    crossings = [near, far]
    for axis in range(3):
        if abs(direction[axis]) > 1e-15:
            times = (np.arange(labels.shape[axis] + 1) - position[axis]) / direction[axis]
            crossings.extend(times[(times > near) & (times < far)].tolist())
    times = np.unique(crossings)
    midpoints = (times[:-1] + times[1:]) / 2
    voxels = np.floor(position + midpoints[:, None] * direction).astype(int)
    voxels = np.clip(voxels, 0, np.asarray(labels.shape) - 1)
    if not np.any(labels[tuple(voxels.T)] > 0):
        raise InputValidationError("source ray does not intersect labeled head tissue")
