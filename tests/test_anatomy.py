import numpy as np
import pytest

from mcx_project.anatomy import (
    block_center_affine,
    block_mean_downsample,
    block_mode_downsample,
    label_counts,
    rounded_discrete_labels,
)


def test_scaled_labels_are_rounded_not_truncated() -> None:
    scaled = np.array([0.0, 0.9882, 2.0235, 12.0001])
    decoded = rounded_discrete_labels(scaled, [0, 1, 2, 12])
    np.testing.assert_array_equal(decoded, [0, 1, 2, 12])


def test_scaled_labels_reject_non_discrete_values() -> None:
    with pytest.raises(ValueError, match="exceeding tolerance"):
        rounded_discrete_labels(np.array([1.2]), [1])


def test_block_mode_uses_declared_tie_priority() -> None:
    labels = np.array(
        [
            [[0, 0], [0, 1]],
            [[1, 1], [1, 0]],
        ],
        dtype=np.uint8,
    )
    output, ties = block_mode_downsample(labels, tie_priority=[1, 0])
    np.testing.assert_array_equal(output, [[[1]]])
    np.testing.assert_array_equal(ties, [[[2]]])


def test_block_mode_rejects_incomplete_priority() -> None:
    with pytest.raises(ValueError, match="exactly the labels"):
        block_mode_downsample(np.zeros((2, 2, 2), dtype=np.uint8), tie_priority=[0, 1])


def test_block_mean_and_center_affine() -> None:
    values = np.arange(8, dtype=np.float32).reshape(2, 2, 2)
    np.testing.assert_allclose(block_mean_downsample(values), [[[3.5]]])
    source_affine = np.array(
        [
            [0.5, 0.0, 0.0, -90.25],
            [0.0, 0.5, 0.0, -126.25],
            [0.0, 0.0, 0.5, -72.25],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    expected = np.array(
        [
            [1.0, 0.0, 0.0, -90.0],
            [0.0, 1.0, 0.0, -126.0],
            [0.0, 0.0, 1.0, -72.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    np.testing.assert_allclose(block_center_affine(source_affine), expected)


def test_label_counts_are_plain_integers() -> None:
    assert label_counts(np.array([[[0, 1], [1, 2]]])) == {0: 1, 1: 2, 2: 1}
