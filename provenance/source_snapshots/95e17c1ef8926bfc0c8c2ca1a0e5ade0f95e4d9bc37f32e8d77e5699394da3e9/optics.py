"""Explicit optical-coefficient conversions with quantity guards."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .validation import InputValidationError


def validate_optical_table(value: dict, *, required_tissue_ids: set[int] | None = None) -> None:
    if value.get("coefficient_unit") != "mm^-1":
        raise InputValidationError("optical scenario coefficients must use mm^-1")
    seen: set[int] = set()
    for row in value.get("tissues", []):
        tissue = row.get("tissue_id")
        if type(tissue) is not int or tissue < 0 or tissue in seen:
            raise InputValidationError("optical table contains invalid or duplicate tissue IDs")
        seen.add(tissue)
        keys = ("mua_mm-1", "mus_mm-1", "g", "n")
        numbers = [row.get(key) for key in keys]
        if any(type(number) not in (int, float) for number in numbers):
            raise InputValidationError(f"optical tissue {tissue} contains unresolved values")
        if not np.isfinite(numbers).all():
            raise InputValidationError(f"optical tissue {tissue} coefficients must be finite")
        mua, mus, g, n = numbers
        if mua < 0 or mus < 0 or not 0 <= g <= 1 or n < 1:
            raise InputValidationError(f"optical tissue {tissue} coefficient is outside its physical range")
        if g == 1 and mus != 0:
            raise InputValidationError("g=1 is supported only for nonscattering media")
        if row.get("source_musp_mm-1") not in (None, "not_used"):
            musp = row["source_musp_mm-1"]
            if type(musp) not in (int, float) or not np.isfinite(musp) or musp < 0:
                raise InputValidationError("reduced scattering must be finite and nonnegative")
            if not np.isclose(musp, mus * (1 - g), rtol=1e-6, atol=1e-9):
                raise InputValidationError(f"optical tissue {tissue} has inconsistent mus, musp and g")
    if not seen:
        raise InputValidationError("optical scenario contains no tissues")
    if required_tissue_ids is not None and seen != required_tissue_ids:
        raise InputValidationError(f"optical tissue coverage mismatch: missing={sorted(required_tissue_ids-seen)}, extra={sorted(seen-required_tissue_ids)}")


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
