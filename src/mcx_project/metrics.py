"""Numerically guarded multisource contribution metrics."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _validated_contributions(contributions: ArrayLike) -> NDArray[np.float64]:
    values = np.asarray(contributions, dtype=np.float64)
    if values.ndim < 1 or values.shape[0] < 1:
        raise ValueError("contributions must have a non-empty source axis")
    if not np.all(np.isfinite(values)):
        raise ValueError("contributions must be finite")
    if np.any(values < 0):
        raise ValueError("contributions must be nonnegative")
    return values


def contribution_metrics(
    contributions: ArrayLike, *, threshold: float = 0.0
) -> dict[str, NDArray[np.float64]]:
    """Compute EF_dom, non-dominant fraction, and inverse-Simpson N_eff.

    The first array axis indexes sources. Results are NaN where the dominant
    contribution does not exceed ``threshold``.
    """

    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError("threshold must be finite and nonnegative")

    values = _validated_contributions(contributions)
    total = np.sum(values, axis=0, dtype=np.float64)
    dominant = np.max(values, axis=0)
    squared_sum = np.sum(np.square(values), axis=0, dtype=np.float64)
    valid_dominant = dominant > threshold
    valid_total = total > threshold

    enhancement = np.full(total.shape, np.nan, dtype=np.float64)
    non_dominant_fraction = np.full(total.shape, np.nan, dtype=np.float64)
    effective_sources = np.full(total.shape, np.nan, dtype=np.float64)

    np.divide(total, dominant, out=enhancement, where=valid_dominant)
    np.divide(total - dominant, total, out=non_dominant_fraction, where=valid_total)
    np.divide(np.square(total), squared_sum, out=effective_sources, where=valid_total)

    return {
        "total": total,
        "dominant": dominant,
        "ef_dom": enhancement,
        "non_dominant_contribution_fraction": non_dominant_fraction,
        "n_eff": effective_sources,
        "valid_mask": valid_dominant,
        "ef_dom_valid_mask": valid_dominant,
        "total_valid_mask": valid_total,
    }


def reference_source_enhancement(
    contributions: ArrayLike, reference_source: int, *, threshold: float = 0.0
) -> NDArray[np.float64]:
    """Compute the Yue-style total/reference-source enhancement."""

    values = _validated_contributions(contributions)
    if not 0 <= reference_source < values.shape[0]:
        raise IndexError("reference_source is outside the source axis")
    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError("threshold must be finite and nonnegative")

    total = np.sum(values, axis=0, dtype=np.float64)
    reference = values[reference_source]
    valid = reference > threshold
    enhancement = np.full(total.shape, np.nan, dtype=np.float64)
    np.divide(total, reference, out=enhancement, where=valid)
    return enhancement
