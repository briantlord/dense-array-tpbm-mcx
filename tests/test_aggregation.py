import numpy as np

from mcx_project.aggregation import (
    chunked_sum,
    finalize_streaming_metrics,
    roi_attribution,
    stream_contribution_statistics,
)
from mcx_project.metrics import contribution_metrics, reference_source_enhancement


def test_chunked_sum_matches_in_memory_float64_sum() -> None:
    fields = [
        np.arange(24, dtype=np.float32).reshape(2, 3, 4),
        np.full((2, 3, 4), 0.25, dtype=np.float32),
        np.full((2, 3, 4), 1e-7, dtype=np.float64),
    ]
    expected = np.sum(np.stack(fields).astype(np.float64), axis=0, dtype=np.float64)
    actual = chunked_sum(fields, chunk_voxels=5)
    np.testing.assert_array_equal(actual, expected)


def test_field_first_and_metric_first_roi_are_distinct_and_hand_computable() -> None:
    contributions = np.array(
        [
            [[9.0, 1.0], [0.0, 50.0]],
            [[1.0, 1.0], [0.0, 50.0]],
        ]
    )
    mask = np.array([[True, True], [False, False]])
    result = roi_attribution(contributions, mask, voxel_volume_mm3=2.0)

    np.testing.assert_allclose(result["integrated_source_contributions"], [20.0, 4.0])
    assert result["field_first"]["ef_dom"] == 1.2
    assert result["metric_first_mean"]["ef_dom"] == 14.0 / 9.0
    assert result["field_first"]["ef_dom"] != result["metric_first_mean"]["ef_dom"]


def test_streaming_statistics_match_source_stack_metrics() -> None:
    fields = {
        "SRC_A": np.array([[4.0, 0.0], [1.0, 2.0]]),
        "SRC_B": np.array([[1.0, 0.0], [3.0, 2.0]]),
        "SRC_C": np.array([[2.0, 0.0], [1.0, 6.0]]),
    }
    roi = np.array([[True, False], [True, False]])
    summary = stream_contribution_statistics(
        iter(fields.items()),
        expected_shape=(2, 2),
        roi_masks={"cortex": roi},
        reference_source_id="SRC_B",
        voxel_volume_mm3=2.0,
    )
    actual = finalize_streaming_metrics(summary, threshold=1e-12)
    stack = np.stack(list(fields.values()))
    expected = contribution_metrics(stack, threshold=1e-12)

    np.testing.assert_array_equal(summary.total, expected["total"])
    np.testing.assert_array_equal(summary.dominant, expected["dominant"])
    np.testing.assert_array_equal(actual["ef_dom"], expected["ef_dom"])
    np.testing.assert_array_equal(
        actual["non_dominant_contribution_fraction"],
        expected["non_dominant_contribution_fraction"],
    )
    np.testing.assert_array_equal(actual["n_eff"], expected["n_eff"])
    np.testing.assert_array_equal(
        actual["ef_ref"],
        reference_source_enhancement(stack, 1, threshold=1e-12),
    )
    np.testing.assert_array_equal(summary.roi_integrals["cortex"], [10.0, 8.0, 6.0])
    np.testing.assert_array_equal(summary.dominant_source_index, [[0, -1], [1, 2]])


def test_streaming_statistics_reject_missing_reference_and_bad_shape() -> None:
    with np.testing.assert_raises_regex(ValueError, "reference source"):
        stream_contribution_statistics(
            [("SRC_A", np.ones((2, 2)))],
            expected_shape=(2, 2),
            reference_source_id="SRC_B",
        )
    with np.testing.assert_raises_regex(ValueError, "shape"):
        stream_contribution_statistics(
            [("SRC_A", np.ones((2, 3)))], expected_shape=(2, 2)
        )
