import numpy as np
import pytest

from scripts.analyze_yue_basis import _normalized, _relative_sd
from scripts.run_yue_aggregate_equivalence import _relative_error


def test_normalized_uses_the_declared_depth_zero_reference() -> None:
    result = _normalized(np.asarray([2.0, 1.0, 0.5]))
    assert result.tolist() == [1.0, 0.5, 0.25]
    assert np.isnan(_normalized(np.asarray([0.0, 1.0]))).all()


def test_relative_sd_is_population_sd_over_mean() -> None:
    assert _relative_sd(np.asarray([1.0, 3.0])) == pytest.approx(0.5)
    assert np.isnan(_relative_sd(np.asarray([0.0, 0.0])))


def test_aggregate_relative_error_guards_a_zero_reference() -> None:
    result = _relative_error(
        np.asarray([2.0, 0.0]),
        np.asarray([2.2, 1.0]),
    )
    assert result[0] == pytest.approx(0.1)
    assert np.isnan(result[1])
