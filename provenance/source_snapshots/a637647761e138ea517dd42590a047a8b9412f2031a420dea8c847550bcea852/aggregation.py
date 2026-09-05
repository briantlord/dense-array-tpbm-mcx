"""Memory-bounded field aggregation and explicit ROI attribution paths."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .metrics import contribution_metrics


@dataclass(frozen=True)
class StreamingContributionSummary:
    """Sufficient statistics accumulated while holding one source field at a time."""

    source_ids: tuple[str, ...]
    total: NDArray[np.float64]
    dominant: NDArray[np.float64]
    dominant_source_index: NDArray[np.int32]
    squared_sum: NDArray[np.float64]
    roi_integrals: dict[str, NDArray[np.float64]]
    reference_source_id: str | None
    reference: NDArray[np.float64] | None


def stream_contribution_statistics(
    fields: Iterable[tuple[str, ArrayLike]],
    *,
    expected_shape: tuple[int, ...],
    roi_masks: Mapping[str, ArrayLike] | None = None,
    reference_source_id: str | None = None,
    voxel_volume_mm3: float = 1.0,
) -> StreamingContributionSummary:
    """Accumulate multisource statistics without retaining the source stack.

    ``fields`` may be a generator that loads one on-disk field per iteration.
    Only the total, dominant field/source, squared sum, optional reference field,
    and scalar ROI integrals are retained.
    """

    if not expected_shape or any(size < 1 for size in expected_shape):
        raise ValueError("expected_shape must contain positive dimensions")
    if not np.isfinite(voxel_volume_mm3) or voxel_volume_mm3 <= 0:
        raise ValueError("voxel_volume_mm3 must be finite and positive")

    masks = {
        name: np.asarray(mask, dtype=bool) for name, mask in (roi_masks or {}).items()
    }
    if any(mask.shape != expected_shape for mask in masks.values()):
        raise ValueError("every ROI mask must match expected_shape")

    total = np.zeros(expected_shape, dtype=np.float64)
    dominant = np.zeros(expected_shape, dtype=np.float64)
    dominant_index = np.full(expected_shape, -1, dtype=np.int32)
    squared_sum = np.zeros(expected_shape, dtype=np.float64)
    square_scratch = np.empty(expected_shape, dtype=np.float64)
    source_ids: list[str] = []
    seen: set[str] = set()
    roi_rows = {name: [] for name in masks}
    reference: NDArray[np.float64] | None = None

    for source_index, (source_id, field) in enumerate(fields):
        if not source_id or source_id in seen:
            raise ValueError("source IDs must be non-empty and unique")
        values = np.asarray(field, dtype=np.float64)
        if values.shape != expected_shape:
            raise ValueError(
                f"field {source_id} has shape {values.shape}, expected {expected_shape}"
            )
        if not np.all(np.isfinite(values)) or np.any(values < 0):
            raise ValueError(f"field {source_id} must be finite and nonnegative")

        seen.add(source_id)
        source_ids.append(source_id)
        total += values
        np.square(values, out=square_scratch)
        squared_sum += square_scratch
        replace = values > dominant
        dominant[replace] = values[replace]
        dominant_index[replace] = source_index
        for name, mask in masks.items():
            roi_rows[name].append(
                float(np.sum(values[mask], dtype=np.float64) * voxel_volume_mm3)
            )
        if source_id == reference_source_id:
            reference = np.array(values, dtype=np.float64, copy=True)

    if not source_ids:
        raise ValueError("at least one field is required")
    if reference_source_id is not None and reference is None:
        raise ValueError(f"reference source was not present: {reference_source_id}")

    return StreamingContributionSummary(
        source_ids=tuple(source_ids),
        total=total,
        dominant=dominant,
        dominant_source_index=dominant_index,
        squared_sum=squared_sum,
        roi_integrals={
            name: np.asarray(values, dtype=np.float64)
            for name, values in roi_rows.items()
        },
        reference_source_id=reference_source_id,
        reference=reference,
    )


def finalize_streaming_metrics(
    summary: StreamingContributionSummary, *, threshold: float = 0.0
) -> dict[str, NDArray[np.float64] | NDArray[np.bool_]]:
    """Derive guarded overlap metrics from streaming sufficient statistics."""

    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError("threshold must be finite and nonnegative")
    total = summary.total
    dominant = summary.dominant
    valid_dominant = dominant > threshold
    valid_total = total > threshold
    ef_dom = np.full(total.shape, np.nan, dtype=np.float64)
    ncf = np.full(total.shape, np.nan, dtype=np.float64)
    n_eff = np.full(total.shape, np.nan, dtype=np.float64)
    np.divide(total, dominant, out=ef_dom, where=valid_dominant)
    np.divide(total - dominant, total, out=ncf, where=valid_total)
    np.divide(np.square(total), summary.squared_sum, out=n_eff, where=valid_total)
    result: dict[str, NDArray[np.float64] | NDArray[np.bool_]] = {
        "ef_dom": ef_dom,
        "non_dominant_contribution_fraction": ncf,
        "n_eff": n_eff,
        "ef_dom_valid_mask": valid_dominant,
        "total_valid_mask": valid_total,
    }
    if summary.reference is not None:
        ef_ref = np.full(total.shape, np.nan, dtype=np.float64)
        np.divide(total, summary.reference, out=ef_ref, where=summary.reference > threshold)
        result["ef_ref"] = ef_ref
    return result


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
