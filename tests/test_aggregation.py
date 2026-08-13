import numpy as np

from mcx_project.aggregation import chunked_sum, roi_attribution


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
