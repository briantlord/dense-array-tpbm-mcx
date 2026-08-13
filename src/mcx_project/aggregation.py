"""Memory-bounded field aggregation and explicit ROI attribution paths."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .metrics import contribution_metrics


def chunked_sum(
    fields: Sequence[ArrayLike], *, chunk_voxels: int = 1_000_000
) -> NDArray[np.float64]:
    """Sum identically shaped source fields in float64 using bounded flat chunks."""

    if not fields:
        raise ValueError("at least one field is required")
    if chunk_voxels < 1:
        raise ValueError("chunk_voxels must be positive")
    arrays = [np.asarray(field) for field in fields]
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays):
        raise ValueError("all fields must have the same shape")
    if any(not np.all(np.isfinite(array)) or np.any(array < 0) for array in arrays):
        raise ValueError("fields must be finite and nonnegative")

    result = np.empty(shape, dtype=np.float64)
    result_flat = result.reshape(-1)
    flattened = [array.reshape(-1) for array in arrays]
    for start in range(0, result_flat.size, chunk_voxels):
        stop = min(start + chunk_voxels, result_flat.size)
        block = np.zeros(stop - start, dtype=np.float64)
        for field in flattened:
            block += field[start:stop]
        result_flat[start:stop] = block
    return result


def roi_attribution(
    contributions: ArrayLike,
    roi_mask: ArrayLike,
    *,
    threshold: float = 0.0,
    voxel_volume_mm3: float = 1.0,
) -> dict[str, object]:
    """Compute separate field-first and metric-first ROI attribution results."""

    values = np.asarray(contributions, dtype=np.float64)
    mask = np.asarray(roi_mask, dtype=bool)
    if values.ndim < 2 or values.shape[1:] != mask.shape:
        raise ValueError("ROI mask must match the spatial contribution dimensions")
    if not np.isfinite(voxel_volume_mm3) or voxel_volume_mm3 <= 0:
        raise ValueError("voxel_volume_mm3 must be finite and positive")

    selected = values[:, mask]
    integrated = np.sum(selected, axis=1, dtype=np.float64) * voxel_volume_mm3
    field_first = contribution_metrics(integrated, threshold=threshold)
    voxelwise = contribution_metrics(selected, threshold=threshold)
    metric_first = {
        key: float(np.nanmean(voxelwise[key]))
        for key in ("ef_dom", "non_dominant_contribution_fraction", "n_eff")
    }
    return {
        "integrated_source_contributions": integrated,
        "field_first": field_first,
        "metric_first_mean": metric_first,
        "voxelwise": voxelwise,
    }
