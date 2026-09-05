import copy

import nibabel as nib
import numpy as np
import pytest

from mcx_project.engine_identity import validate_engine_identity
from mcx_project.geometry import transformed_source, validate_engine_geometry, validate_volume_geometry, validate_tissue_intersection
from mcx_project.optics import validate_optical_table
from mcx_project.provenance import resolve_recorded_code, snapshot_source
from mcx_project.validation import InputValidationError


def test_direction_and_position_use_the_same_rotated_voxel_frame():
    affine = np.array([[0,-1,0,0],[1,0,0,0],[0,0,1,0],[0,0,0,1]])
    position, direction = transformed_source(
        {"position_mm": [1,0,0], "normal": [1,0,0]},
        {"matrix_4x4": np.eye(4).tolist()}, {"affine": affine.tolist()})
    np.testing.assert_allclose(position, [0,-1,0])
    np.testing.assert_allclose(direction, [0,-1,0])


def test_external_source_must_hit_tissue():
    labels = np.zeros((10,10,10), dtype=np.uint8)
    labels[3:7,3:7,3:7] = 1
    validate_tissue_intersection(labels, {"position_voxels": [-5,5,5], "direction": [1,0,0]})
    for source in ({"position_voxels": [-5,1,1], "direction": [1,0,0]},
                   {"position_voxels": [-5,5,5], "direction": [-1,0,0]},
                   {"position_voxels": [5,5,5], "direction": [0,0,0]}):
        with pytest.raises(InputValidationError):
            validate_tissue_intersection(labels, source)


def test_nonmillimeter_volume_and_unsupported_source_are_rejected():
    config = {"volume": {"shape_voxels": [5,5,5]}, "source": {"type": "gaussian"}}
    with pytest.raises(InputValidationError, match="only pencil"):
        validate_engine_geometry(config)
    image = nib.Nifti1Image(np.zeros((5,5,5)), np.diag([.5,.5,.5,1]))
    with pytest.raises(InputValidationError, match="1-mm"):
        validate_volume_geometry(image, config)


@pytest.mark.parametrize("key,value", [("mua_mm-1", -1), ("mus_mm-1", float('nan')),
    ("g", 1.1), ("n", .9), ("source_musp_mm-1", 3)])
def test_invalid_effective_optics_are_rejected(key, value):
    row = {"tissue_id": 1, "mua_mm-1": .1, "mus_mm-1": 2, "g": .9, "n": 1.4}
    row[key] = value
    with pytest.raises(InputValidationError):
        validate_optical_table({"coefficient_unit": "mm^-1", "tissues": [row]})


def test_full_optical_replacement_requires_every_tissue():
    with pytest.raises(InputValidationError, match="coverage"):
        validate_optical_table({"coefficient_unit": "mm^-1", "tissues": [
            {"tissue_id": 0, "mua_mm-1": 0, "mus_mm-1": 0, "g": 0, "n": 1}]},
            required_tissue_ids={0,1})


@pytest.mark.parametrize("key,value", [("executable_sha256", "0"*64),
    ("engine_version", "WRONG_ENGINE"), ("gpu", "OTHER_GPU"), ("selected_device", 2)])
def test_engine_binding_rejects_changed_identity(key, value):
    expected = {"executable_sha256": "1"*64, "engine_version": "v2025.10", "gpu": "GPU"}
    actual = {**expected, "selected_device": 1}
    validate_engine_identity(expected, actual)
    actual[key] = value
    with pytest.raises(InputValidationError):
        validate_engine_identity(expected, actual)


def test_historical_source_recovery_checks_bytes(tmp_path):
    source = tmp_path / "analyzer.py"
    source.write_bytes(b"print('original')\r\n")
    record = snapshot_source(tmp_path, source)
    source.write_bytes(b"print('new')\n")
    archived = resolve_recorded_code(tmp_path, record)
    assert archived.read_bytes() == b"print('original')\r\n"
    archived.write_bytes(b"corrupt")
    with pytest.raises(InputValidationError, match="no exact source"):
        resolve_recorded_code(tmp_path, record)
