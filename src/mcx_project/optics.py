"""Explicit optical-coefficient conversions with quantity guards."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _nonnegative_finite(value: ArrayLike, name: str) -> NDArray[np.float64]:
    result = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(result)) or np.any(result < 0):
        raise ValueError(f"{name} must be finite and nonnegative")
    return result


def per_cm_to_per_mm(value: ArrayLike) -> NDArray[np.float64]:
    """Convert an inverse-length coefficient from cm^-1 to mm^-1."""

    return _nonnegative_finite(value, "coefficient") / 10.0


def per_mm_to_per_cm(value: ArrayLike) -> NDArray[np.float64]:
    """Convert an inverse-length coefficient from mm^-1 to cm^-1."""

    return _nonnegative_finite(value, "coefficient") * 10.0


def musp_from_mus(mus: ArrayLike, g: ArrayLike) -> NDArray[np.float64]:
    """Compute reduced scattering: musp = mus * (1 - g)."""

    mus_value = _nonnegative_finite(mus, "mus")
    g_value = np.asarray(g, dtype=np.float64)
    if not np.all(np.isfinite(g_value)) or np.any((g_value < 0) | (g_value >= 1)):
        raise ValueError("g must be finite and satisfy 0 <= g < 1")
    return mus_value * (1.0 - g_value)


def mus_from_musp(musp: ArrayLike, g: ArrayLike) -> NDArray[np.float64]:
    """Recover scattering: mus = musp / (1 - g)."""

    musp_value = _nonnegative_finite(musp, "musp")
    g_value = np.asarray(g, dtype=np.float64)
    if not np.all(np.isfinite(g_value)) or np.any((g_value < 0) | (g_value >= 1)):
        raise ValueError("g must be finite and satisfy 0 <= g < 1")
    return musp_value / (1.0 - g_value)
