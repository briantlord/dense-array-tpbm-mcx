"""Published-benchmark sampling and Monte Carlo convergence utilities."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import ndimage


def sample_axis_profile(
    field: ArrayLike,
    affine: ArrayLike,
    source_world_mm: ArrayLike,
    inward_direction_world: ArrayLike,
    depths_mm: ArrayLike,
) -> NDArray[np.float64]:
    """Trilinearly sample a 3-D field along a source axis in world millimeters."""

    values = np.asarray(field, dtype=np.float64)
    if values.ndim == 4 and values.shape[-1] == 1:
        values = values[..., 0]
    if values.ndim != 3 or not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("field must be a finite, nonnegative 3-D array")
    transform = np.asarray(affine, dtype=np.float64)
    if transform.shape != (4, 4) or not np.all(np.isfinite(transform)):
        raise ValueError("affine must be a finite 4 x 4 matrix")
    source = np.asarray(source_world_mm, dtype=np.float64)
    direction = np.asarray(inward_direction_world, dtype=np.float64)
    depths = np.asarray(depths_mm, dtype=np.float64)
    if source.shape != (3,) or direction.shape != (3,) or depths.ndim != 1:
        raise ValueError("source/direction must be triplets and depths must be one-dimensional")
    if not np.all(np.isfinite(source)) or not np.all(np.isfinite(direction)):
        raise ValueError("source and direction must be finite")
    if not np.all(np.isfinite(depths)) or np.any(depths < 0):
        raise ValueError("depths must be finite and nonnegative")
    norm = float(np.linalg.norm(direction))
    if not np.isclose(norm, 1.0, rtol=0.0, atol=1e-8):
        raise ValueError("inward direction must be a unit vector")

    world = source[None, :] + depths[:, None] * direction[None, :]
    homogeneous = np.c_[world, np.ones(len(world), dtype=np.float64)]
    voxel = (np.linalg.inv(transform) @ homogeneous.T)[:3]
    inside = np.all((voxel >= 0) & (voxel <= (np.asarray(values.shape) - 1)[:, None]), axis=0)
    result = np.full(len(depths), np.nan, dtype=np.float64)
    result[inside] = ndimage.map_coordinates(
        values,
        voxel[:, inside],
        order=1,
        mode="constant",
        cval=np.nan,
        prefilter=False,
    )
    return result


def masked_integrals(
    field: ArrayLike,
    labels: ArrayLike,
    label_groups: dict[str, Sequence[int]],
    *,
    voxel_volume_mm3: float = 1.0,
) -> dict[str, float]:
    """Integrate a field over named tissue-label groups."""

    values = np.asarray(field, dtype=np.float64)
    if values.ndim == 4 and values.shape[-1] == 1:
        values = values[..., 0]
    tissue = np.asarray(labels)
    if values.shape != tissue.shape:
        raise ValueError("field and labels must have the same 3-D shape")
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("field must be finite and nonnegative")
    if not np.isfinite(voxel_volume_mm3) or voxel_volume_mm3 <= 0:
        raise ValueError("voxel_volume_mm3 must be finite and positive")
    output: dict[str, float] = {}
    for name, group in label_groups.items():
        if not name or not group:
            raise ValueError("label groups require a name and at least one label")
        mask = np.isin(tissue, group)
        if not np.any(mask):
            raise ValueError(f"label group {name!r} is empty")
        output[name] = float(np.sum(values[mask], dtype=np.float64) * voxel_volume_mm3)
    return output


def replicate_statistics(values: ArrayLike) -> dict[str, NDArray[np.float64]]:
    """Compute replicate mean, sample SD, CV, and a normal 95% CI."""

    samples = np.asarray(values, dtype=np.float64)
    if samples.ndim < 1 or samples.shape[0] < 2:
        raise ValueError("at least two replicates are required")
    if not np.all(np.isfinite(samples)) or np.any(samples < 0):
        raise ValueError("replicate values must be finite and nonnegative")
    mean = np.mean(samples, axis=0, dtype=np.float64)
    sd = np.std(samples, axis=0, ddof=1, dtype=np.float64)
    cv = np.full(mean.shape, np.nan, dtype=np.float64)
    np.divide(sd, mean, out=cv, where=mean > 0)
    half_width = 1.96 * sd / np.sqrt(samples.shape[0])
    return {
        "mean": mean,
        "sd": sd,
        "cv": cv,
        "ci95_low": np.maximum(mean - half_width, 0.0),
        "ci95_high": mean + half_width,
    }


def symmetric_relative_change(previous: ArrayLike, current: ArrayLike) -> NDArray[np.float64]:
    """Return absolute symmetric relative change with a guarded zero case."""

    first = np.asarray(previous, dtype=np.float64)
    second = np.asarray(current, dtype=np.float64)
    if first.shape != second.shape:
        raise ValueError("comparison arrays must have the same shape")
    if not np.all(np.isfinite(first)) or not np.all(np.isfinite(second)):
        raise ValueError("comparison values must be finite")
    denominator = (np.abs(first) + np.abs(second)) / 2.0
    change = np.zeros(first.shape, dtype=np.float64)
    np.divide(np.abs(second - first), denominator, out=change, where=denominator > 0)
    return change


def profile_convergence_summary(
    previous_mean: ArrayLike,
    current_mean: ArrayLike,
    current_cv: ArrayLike,
    *,
    valid_mask: ArrayLike,
) -> dict[str, float | int]:
    """Summarize profile convergence only over a prespecified valid mask."""

    previous = np.asarray(previous_mean, dtype=np.float64)
    current = np.asarray(current_mean, dtype=np.float64)
    cv = np.asarray(current_cv, dtype=np.float64)
    mask = np.asarray(valid_mask, dtype=bool)
    if previous.shape != current.shape or current.shape != cv.shape or cv.shape != mask.shape:
        raise ValueError("profile arrays and valid mask must have the same shape")
    finite = mask & np.isfinite(previous) & np.isfinite(current) & np.isfinite(cv)
    if not np.any(finite):
        raise ValueError("profile convergence mask selects no finite values")
    change = symmetric_relative_change(previous[finite], current[finite])
    return {
        "n_valid_depths": int(np.count_nonzero(finite)),
        "median_symmetric_relative_change": float(np.median(change)),
        "maximum_symmetric_relative_change": float(np.max(change)),
        "median_current_cv": float(np.median(cv[finite])),
        "maximum_current_cv": float(np.max(cv[finite])),
    }
