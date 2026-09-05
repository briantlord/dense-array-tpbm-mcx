"""Deterministic construction of the declared Yue-2015 benchmark approximation."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
from scipy import ndimage


YUE_LAYER_ELEVATIONS_RAD = np.array(
    [0.0, 0.157, 0.314, 0.471, 0.628, 0.785, 0.942, 1.100, 1.257, 1.414, 1.571],
    dtype=np.float64,
)
YUE_LAYER_COUNTS = np.array([40, 40, 36, 36, 32, 28, 24, 20, 12, 8, 1])
YUE_DENSITY_TIERS = (13, 53, 105, 181, 229, 277)


def collapse_native_to_yue_five_tissues(
    native_labels: np.ndarray,
) -> tuple[np.ndarray, dict[int, dict[int, int]]]:
    """Collapse Colin27 native labels into a spatially explicit five-tissue map.

    Native vessels occur both inside and outside the cranium. They are assigned
    to the nearest non-vessel anatomical tissue rather than by a global lookup.
    The returned transition table records every native-to-benchmark assignment.
    """

    native = np.asarray(native_labels)
    if native.ndim != 3:
        raise ValueError("native label volume must be three-dimensional")
    expected = {0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12}
    present = set(np.unique(native).tolist())
    if present != expected:
        raise ValueError(f"unexpected Colin27 native labels: {sorted(present)}")

    # 0 background; 1 scalp; 2 skull; 3 modified CSF; 4 GM; 5 WM.
    lookup = {0: 0, 1: 3, 2: 4, 3: 5, 4: 1, 5: 1, 6: 1, 7: 2, 9: 1, 10: 2, 11: 2}
    collapsed = np.zeros(native.shape, dtype=np.uint8)
    for source, target in lookup.items():
        collapsed[native == source] = target

    vessel_mask = native == 12
    nonvessel_tissue = (native != 0) & ~vessel_mask
    if np.any(vessel_mask):
        _, nearest = ndimage.distance_transform_edt(
            ~nonvessel_tissue, return_indices=True
        )
        collapsed[vessel_mask] = collapsed[tuple(nearest[:, vessel_mask])]
    if np.any(collapsed[vessel_mask] == 0):
        raise ValueError("at least one vessel voxel could not be spatially assigned")

    transitions: dict[int, dict[int, int]] = {}
    for source in sorted(expected):
        target_values, counts = np.unique(collapsed[native == source], return_counts=True)
        transitions[source] = {
            int(target): int(count)
            for target, count in zip(target_values, counts, strict=True)
        }
    return collapsed, transitions


def rotation_about_y(angle_rad: float) -> np.ndarray:
    """Return a right-handed active rotation matrix about +y."""

    cosine = float(np.cos(angle_rad))
    sine = float(np.sin(angle_rad))
    return np.array(
        [[cosine, 0.0, sine], [0.0, 1.0, 0.0], [-sine, 0.0, cosine]],
        dtype=np.float64,
    )


def yue277_directions(*, rotation_y_rad: float = 0.09) -> tuple[np.ndarray, list[dict[str, float | int]]]:
    """Generate the Table-1 277-source directions with a declared zero phase."""

    directions: list[np.ndarray] = []
    records: list[dict[str, float | int]] = []
    rotation = rotation_about_y(rotation_y_rad)
    for layer, (theta, count) in enumerate(
        zip(YUE_LAYER_ELEVATIONS_RAD, YUE_LAYER_COUNTS, strict=True), start=1
    ):
        if count == 1:
            phis: Iterable[float] = [0.0]
        else:
            phis = (2.0 * np.pi * np.arange(int(count)) / int(count)).tolist()
        for within_layer, phi in enumerate(phis, start=1):
            unrotated = np.array(
                [
                    np.cos(theta) * np.cos(phi),
                    np.cos(theta) * np.sin(phi),
                    np.sin(theta),
                ],
                dtype=np.float64,
            )
            direction = rotation @ unrotated
            direction /= np.linalg.norm(direction)
            directions.append(direction)
            records.append(
                {
                    "layer": layer,
                    "within_layer": within_layer,
                    "elevation_rad": float(theta),
                    "azimuth_rad": float(phi),
                }
            )
    result = np.asarray(directions, dtype=np.float64)
    if result.shape != (277, 3):
        raise RuntimeError(f"Yue direction generator produced {result.shape}")
    return result, records


def nested_farthest_point_tiers(
    directions: np.ndarray,
    counts: Sequence[int] = YUE_DENSITY_TIERS,
    *,
    north_index: int | None = None,
) -> dict[int, list[int]]:
    """Create deterministic nested, spatially balanced density subsets."""

    unit = np.asarray(directions, dtype=np.float64)
    if unit.ndim != 2 or unit.shape[1] != 3:
        raise ValueError("directions must have shape (n, 3)")
    norms = np.linalg.norm(unit, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=1e-10):
        raise ValueError("directions must be unit vectors")
    requested = tuple(int(count) for count in counts)
    if not requested or sorted(set(requested)) != list(requested):
        raise ValueError("counts must be unique and strictly increasing")
    if requested[-1] > len(unit):
        raise ValueError("density tier exceeds available directions")

    north = len(unit) - 1 if north_index is None else north_index
    if not 0 <= north < len(unit):
        raise ValueError("north_index is outside the direction array")
    selected = [north]
    available = np.ones(len(unit), dtype=bool)
    available[north] = False
    minimum_angle = np.full(len(unit), np.inf, dtype=np.float64)
    target_sizes = set(requested)
    tiers: dict[int, list[int]] = {}
    if 1 in target_sizes:
        tiers[1] = selected.copy()

    while len(selected) < requested[-1]:
        latest = unit[selected[-1]]
        angles = np.arccos(np.clip(unit @ latest, -1.0, 1.0))
        minimum_angle = np.minimum(minimum_angle, angles)
        candidates = np.flatnonzero(available)
        next_index = int(candidates[np.argmax(minimum_angle[candidates])])
        selected.append(next_index)
        available[next_index] = False
        if len(selected) in target_sizes:
            tiers[len(selected)] = sorted(selected)
    return tiers


def brain_center_world(
    labels: np.ndarray, affine: np.ndarray, *, brain_labels: Sequence[int] = (3, 4, 5)
) -> np.ndarray:
    """Return the world-coordinate centroid of the benchmark intracranial tissues."""

    volume = np.asarray(labels)
    mask = np.isin(volume, brain_labels)
    if not np.any(mask):
        raise ValueError("brain tissue mask is empty")
    center_voxel = np.asarray(ndimage.center_of_mass(mask), dtype=np.float64)
    return (np.asarray(affine, dtype=np.float64) @ np.r_[center_voxel, 1.0])[:3]


def project_directions_to_scalp(
    labels: np.ndarray,
    affine: np.ndarray,
    center_world: np.ndarray,
    directions: np.ndarray,
    *,
    step_mm: float = 0.25,
    inward_offset_mm: float = 0.75,
) -> np.ndarray:
    """Place sources just inside the outermost non-background voxel on each ray."""

    volume = np.asarray(labels)
    inverse = np.linalg.inv(np.asarray(affine, dtype=np.float64))
    center = np.asarray(center_world, dtype=np.float64)
    unit = np.asarray(directions, dtype=np.float64)
    diagonal_mm = float(
        np.linalg.norm(np.asarray(volume.shape) * np.linalg.norm(affine[:3, :3], axis=0))
    )
    radii = np.arange(0.0, diagonal_mm, step_mm, dtype=np.float64)
    positions: list[np.ndarray] = []

    for direction in unit:
        points = center[None, :] + radii[:, None] * direction[None, :]
        homogeneous = np.c_[points, np.ones(len(points))]
        voxel = (inverse @ homogeneous.T).T[:, :3]
        indices = np.rint(voxel).astype(np.int64)
        inside = np.all((indices >= 0) & (indices < np.asarray(volume.shape)), axis=1)
        occupied = np.zeros(len(radii), dtype=bool)
        valid = indices[inside]
        occupied[inside] = volume[valid[:, 0], valid[:, 1], valid[:, 2]] != 0
        hits = np.flatnonzero(occupied)
        if not len(hits):
            raise ValueError("source ray did not intersect the head")
        radius = max(0.0, radii[hits[-1]] - inward_offset_mm)
        position = center + radius * direction
        for _ in range(20):
            index = np.rint((inverse @ np.r_[position, 1.0])[:3]).astype(int)
            if np.all((index >= 0) & (index < np.asarray(volume.shape))) and volume[
                tuple(index)
            ] != 0:
                break
            radius = max(0.0, radius - step_mm)
            position = center + radius * direction
        else:
            raise ValueError("could not place a source inside the scalp boundary")
        positions.append(position)
    return np.asarray(positions, dtype=np.float64)
