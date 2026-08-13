import numpy as np
import pytest

from mcx_project.benchmark import (
    masked_integrals,
    profile_convergence_summary,
    replicate_statistics,
    sample_axis_profile,
    symmetric_relative_change,
)


def test_axis_profile_samples_world_coordinates_trilinearly() -> None:
    field = np.indices((5, 5, 5), dtype=np.float64).sum(axis=0)
    profile = sample_axis_profile(
        field,
        np.eye(4),
        [1.0, 1.0, 1.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.5, 2.0, 5.0],
    )
    np.testing.assert_allclose(profile[:3], [3.0, 3.5, 5.0])
    assert np.isnan(profile[3])


def test_axis_profile_requires_unit_direction() -> None:
    with pytest.raises(ValueError, match="unit vector"):
        sample_axis_profile(np.ones((2, 2, 2)), np.eye(4), [0, 0, 0], [2, 0, 0], [0])


def test_masked_integrals_are_label_specific() -> None:
    field = np.arange(8, dtype=np.float64).reshape(2, 2, 2)
    labels = np.array([[[1, 1], [2, 2]], [[1, 2], [3, 3]]])
    result = masked_integrals(field, labels, {"one": [1], "brain": [2, 3]}, voxel_volume_mm3=2)
    assert result["one"] == 10.0
    assert result["brain"] == 46.0


def test_replicate_statistics_and_symmetric_change() -> None:
    stats = replicate_statistics([[1.0, 2.0], [2.0, 2.0], [3.0, 2.0]])
    np.testing.assert_allclose(stats["mean"], [2.0, 2.0])
    np.testing.assert_allclose(stats["sd"], [1.0, 0.0])
    np.testing.assert_allclose(stats["cv"], [0.5, 0.0])
    np.testing.assert_allclose(symmetric_relative_change([0, 1], [0, 3]), [0, 1])


def test_profile_convergence_uses_only_valid_points() -> None:
    summary = profile_convergence_summary(
        [1.0, 1.0, 0.0],
        [1.1, 0.9, 0.0],
        [0.05, 0.10, np.nan],
        valid_mask=[True, True, False],
    )
    assert summary["n_valid_depths"] == 2
    assert summary["median_current_cv"] == pytest.approx(0.075)
