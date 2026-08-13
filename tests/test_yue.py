from pathlib import Path

import numpy as np

from mcx_project.validation import validate_json
from mcx_project.yue import (
    YUE_DENSITY_TIERS,
    YUE_LAYER_COUNTS,
    collapse_native_to_yue_five_tissues,
    nested_farthest_point_tiers,
    project_directions_to_scalp,
    yue277_directions,
)


ROOT = Path(__file__).resolve().parents[1]


def test_yue_reported_input_artifacts_validate() -> None:
    cases = (
        ("schemas/optical_properties.schema.json", "inputs/optical_properties/yue2015_850_approx_v1.json"),
        ("schemas/emitter_geometry.schema.json", "inputs/emitters/yue2015_approx_v1/emitter_geometry.json"),
        ("schemas/calibration.schema.json", "inputs/emitters/yue2015_approx_v1/calibration.json"),
        ("schemas/registration.schema.json", "inputs/registration/yue2015_approx_v1.json"),
        ("schemas/analysis_configuration.schema.json", "configs/yue2015_approx_v1_analysis.json"),
        ("schemas/engine_configuration.schema.json", "configs/yue2015_approx_v1_north_pole_fluence.json"),
        ("schemas/basis_plan.schema.json", "configs/yue2015_approx_v1_basis_plan.json"),
    )
    for schema, instance in cases:
        validate_json(ROOT / schema, ROOT / instance, require_complete=True)


def test_yue_table1_generator_has_reported_layer_counts_and_north_pole() -> None:
    directions, records = yue277_directions()
    assert directions.shape == (277, 3)
    np.testing.assert_allclose(np.linalg.norm(directions, axis=1), 1.0, atol=1e-12)
    assert [sum(row["layer"] == layer for row in records) for layer in range(1, 12)] == YUE_LAYER_COUNTS.tolist()
    np.testing.assert_allclose(directions[-1], [np.sin(0.09), 0.0, np.cos(0.09)], atol=5e-4)


def test_density_tiers_are_nested_and_include_north_pole() -> None:
    directions, _ = yue277_directions()
    tiers = nested_farthest_point_tiers(directions)
    assert tuple(tiers) == YUE_DENSITY_TIERS
    previous: set[int] = set()
    for count, members in tiers.items():
        assert len(members) == count
        assert len(set(members)) == count
        assert 276 in members
        assert previous.issubset(members)
        previous = set(members)


def test_five_tissue_collapse_uses_spatial_vessel_assignment() -> None:
    native = np.zeros((4, 4, 4), dtype=np.uint8)
    for index, label in enumerate([1, 2, 3, 4, 5, 6, 7, 9, 10, 11]):
        native.flat[index] = label
    native[2, 2, 2] = 2
    native[2, 2, 3] = 12
    collapsed, transitions = collapse_native_to_yue_five_tissues(native)
    assert set(np.unique(collapsed)) == {0, 1, 2, 3, 4, 5}
    assert collapsed[2, 2, 3] == 4
    assert transitions[12] == {4: 1}


def test_source_projection_places_points_inside_spherical_head() -> None:
    coordinates = np.indices((21, 21, 21)).astype(np.float64)
    radius = np.sqrt(np.sum((coordinates - 10.0) ** 2, axis=0))
    labels = np.zeros((21, 21, 21), dtype=np.uint8)
    labels[radius <= 8.0] = 1
    positions = project_directions_to_scalp(
        labels,
        np.eye(4),
        np.array([10.0, 10.0, 10.0]),
        np.eye(3),
    )
    indices = np.rint(positions).astype(int)
    assert np.all(labels[indices[:, 0], indices[:, 1], indices[:, 2]] == 1)
    assert np.all(np.linalg.norm(positions - 10.0, axis=1) > 6.0)
