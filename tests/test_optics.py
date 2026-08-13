import numpy as np
import pytest

from mcx_project.optics import (
    mus_from_musp,
    musp_from_mus,
    per_cm_to_per_mm,
    per_mm_to_per_cm,
)


def test_inverse_length_unit_conversion_round_trip() -> None:
    original_cm = np.array([0.0, 0.5, 12.0])
    np.testing.assert_allclose(per_cm_to_per_mm(original_cm), [0.0, 0.05, 1.2])
    np.testing.assert_allclose(per_mm_to_per_cm(per_cm_to_per_mm(original_cm)), original_cm)


def test_scattering_conversion_round_trip() -> None:
    mus = np.array([1.0, 12.0])
    g = np.array([0.0, 0.9])
    musp = musp_from_mus(mus, g)
    np.testing.assert_allclose(musp, [1.0, 1.2])
    np.testing.assert_allclose(mus_from_musp(musp, g), mus)


@pytest.mark.parametrize("g", [-0.1, 1.0, np.inf])
def test_scattering_conversion_rejects_illegal_anisotropy(g: float) -> None:
    with pytest.raises(ValueError, match="0 <= g < 1"):
        musp_from_mus(1.0, g)
