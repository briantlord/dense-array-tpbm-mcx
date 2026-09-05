"""Deterministic categorical-volume utilities for anatomy preparation."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def rounded_discrete_labels(
    scaled_values: np.ndarray,
    allowed_labels: Sequence[int],
    *,
    tolerance: float = 0.05,
) -> np.ndarray:
    """Decode a scaled discrete NIfTI volume without unsafe float truncation."""
    values = np.asarray(scaled_values)
    if not np.all(np.isfinite(values)):
        raise ValueError("discrete label volume contains non-finite values")
    rounded = np.rint(values)
    maximum_error = float(np.max(np.abs(values - rounded)))
    if maximum_error > tolerance:
        raise ValueError(
            f"scaled labels deviate from integers by {maximum_error}, "
            f"exceeding tolerance {tolerance}"
        )
    labels = rounded.astype(np.uint8)
    unexpected = sorted(set(np.unique(labels).tolist()) - set(allowed_labels))
    if unexpected:
        raise ValueError(f"unexpected labels after scaling: {unexpected}")
    return labels


def block_mode_downsample(
    labels: np.ndarray,
    *,
    factor: int = 2,
    tie_priority: Sequence[int],
) -> tuple[np.ndarray, np.ndarray]:
    """Downsample categorical data by block mode with explicit tie resolution.

    Returns the downsampled labels and a uint8 volume recording the number of
    labels tied for the winning count in every output voxel.
    """
    volume = np.asarray(labels)
    if volume.ndim != 3:
        raise ValueError("label volume must be three-dimensional")
    if factor < 1:
        raise ValueError("factor must be a positive integer")
    if any(size % factor for size in volume.shape):
        raise ValueError("every label-volume dimension must be divisible by factor")
    present = set(np.unique(volume).tolist())
    priority = list(tie_priority)
    if len(priority) != len(set(priority)):
        raise ValueError("tie_priority contains duplicate labels")
    if present != set(priority):
        raise ValueError(
            "tie_priority must contain exactly the labels present in the volume"
        )

    nx, ny, nz = (size // factor for size in volume.shape)
    blocks = (
        volume.reshape(nx, factor, ny, factor, nz, factor)
        .transpose(0, 2, 4, 1, 3, 5)
        .reshape(nx, ny, nz, factor**3)
    )
    best_count = np.zeros((nx, ny, nz), dtype=np.uint8)
    tie_count = np.zeros((nx, ny, nz), dtype=np.uint8)
    output = np.zeros((nx, ny, nz), dtype=np.uint8)

    for label in priority:
        count = np.count_nonzero(blocks == label, axis=-1).astype(np.uint8)
        wins = count > best_count
        ties = (count == best_count) & (count > 0)
        output[wins] = label
        best_count[wins] = count[wins]
        tie_count[wins] = 1
        tie_count[ties] += 1

    return output, tie_count


def block_mean_downsample(values: np.ndarray, *, factor: int = 2) -> np.ndarray:
    """Downsample a three-dimensional scalar image by block averaging."""
    volume = np.asarray(values, dtype=np.float32)
    if volume.ndim != 3:
        raise ValueError("scalar volume must be three-dimensional")
    if factor < 1:
        raise ValueError("factor must be a positive integer")
    if any(size % factor for size in volume.shape):
        raise ValueError("every scalar-volume dimension must be divisible by factor")
    nx, ny, nz = (size // factor for size in volume.shape)
    blocks = volume.reshape(nx, factor, ny, factor, nz, factor)
    return blocks.mean(axis=(1, 3, 5), dtype=np.float32)


def block_center_affine(source_affine: np.ndarray, *, factor: int = 2) -> np.ndarray:
    """Map output voxel centers to centers of source voxel blocks."""
    affine = np.asarray(source_affine, dtype=np.float64)
    if affine.shape != (4, 4):
        raise ValueError("source affine must be 4 x 4")
    if factor < 1:
        raise ValueError("factor must be a positive integer")
    target_to_source = np.eye(4, dtype=np.float64)
    target_to_source[0, 0] = factor
    target_to_source[1, 1] = factor
    target_to_source[2, 2] = factor
    target_to_source[:3, 3] = (factor - 1) / 2
    return affine @ target_to_source


def label_counts(labels: np.ndarray) -> dict[int, int]:
    """Return deterministic integer label counts."""
    values, counts = np.unique(np.asarray(labels), return_counts=True)
    return {int(value): int(count) for value, count in zip(values, counts)}
