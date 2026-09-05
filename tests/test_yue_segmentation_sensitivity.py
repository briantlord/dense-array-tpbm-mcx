import numpy as np
import pytest

from scripts.run_yue_segmentation_sensitivity import (
    _apply_operation,
    _axis_transitions,
)


def test_inner_scalp_operation_keeps_source_surface_and_changes_inner_scalp() -> None:
    labels = np.zeros((9, 9, 9), dtype=np.uint8)
    labels[1:8, 1:8, 1:8] = 1
    labels[3:6, 3:6, 3:6] = 2
    changed, record = _apply_operation(
        labels,
        {"operation": "inner_scalp_to_transparent", "thickness_mm": 1.0},
        affine=np.eye(4),
        source_world=np.asarray([4.0, 4.0, 7.0]),
        direction=np.asarray([0.0, 0.0, -1.0]),
    )
    assert record["changed_voxel_count"] > 0
    assert np.all(labels[changed != labels] == 1)
    assert np.all(changed[changed != labels] == 6)
    assert changed[4, 4, 7] == 1
    assert np.array_equal(changed[3:6, 3:6, 3:6], labels[3:6, 3:6, 3:6])


def test_inner_skull_operation_changes_only_skull_next_to_csf() -> None:
    labels = np.full((9, 9, 9), 2, dtype=np.uint8)
    labels[4, 4, 4] = 3
    changed, record = _apply_operation(
        labels,
        {"operation": "inner_skull_to_csf", "thickness_mm": 1.0},
        affine=np.eye(4),
        source_world=np.asarray([4.0, 4.0, 8.0]),
        direction=np.asarray([0.0, 0.0, -1.0]),
    )
    assert record["changed_voxel_count"] == 6
    assert np.count_nonzero(changed == 3) == 7


def test_axis_transition_output_preserves_order() -> None:
    depths = np.asarray([0.0, 0.1, 0.2, 0.3])
    labels = np.asarray([1, 1, 2, 2], dtype=np.uint8)
    transitions = _axis_transitions(depths, labels)
    assert [row["tissue"] for row in transitions] == ["scalp", "skull"]
    assert transitions[0]["depth_stop_mm"] == pytest.approx(0.15)
