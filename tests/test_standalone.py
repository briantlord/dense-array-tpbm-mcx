import base64
import json
from pathlib import Path

import numpy as np
import pytest

from mcx_project.standalone import (
    load_jnii_field,
    parse_absorbed_energy_percent,
    render_mcxcl_input,
)
from mcx_project.validation import InputValidationError
from mcx_project.validation import load_json


ROOT = Path(__file__).resolve().parents[1]


def test_rendered_mcxcl_input_preserves_engine_contract() -> None:
    config = load_json(ROOT / "configs/synthetic_smoke_opencl_v1.json")
    rendered = render_mcxcl_input(config, "test_session")

    assert rendered["Session"]["ID"] == "test_session"
    assert rendered["Session"]["RNGSeed"] == config["seed"]
    assert rendered["Session"]["OutputFormat"] == "jnii"
    assert rendered["Domain"]["Media"][0] == {
        "mua": 0.0,
        "mus": 0.0,
        "g": 1.0,
        "n": 1.0,
    }
    assert rendered["Optode"]["Source"]["Pos"] == [30.0, 30.0, 0.0]
    assert rendered["Shapes"][0]["Grid"]["Size"] == [60, 60, 60]


def test_label_volume_render_requires_prepared_binary() -> None:
    config = load_json(ROOT / "configs/yue2015_approx_v1_north_pole_fluence.json")
    with pytest.raises(InputValidationError, match="prepared volume"):
        render_mcxcl_input(config, "test_session")
    rendered = render_mcxcl_input(
        config, "test_session", volume_file="volume.uint8.bin"
    )
    assert rendered["Domain"]["VolumeFile"] == "volume.uint8.bin"
    assert "Shapes" not in rendered


def test_load_uncompressed_jnifti_field(tmp_path: Path) -> None:
    expected = np.arange(24, dtype="<f4").reshape(2, 3, 4, 1)
    document = {
        "NIFTIData": {
            "_ArrayType_": "single",
            "_ArraySize_": list(expected.shape),
            "_ArrayOrder_": "c",
            "_ArrayZipType_": "base64",
            "_ArrayZipSize_": expected.size,
            "_ArrayZipData_": base64.b64encode(expected.tobytes()).decode("ascii"),
        }
    }
    path = tmp_path / "field.jnii"
    path.write_text(json.dumps(document), encoding="utf-8")
    actual = load_jnii_field(path)

    assert actual.dtype == np.float64
    np.testing.assert_array_equal(actual, expected.astype(np.float64))


def test_absorbed_energy_parser_ignores_console_color_codes() -> None:
    log = "total energy: 100000.00\tabsorbed: \x1b[1m\x1b[34m27.17860%\x1b[0m"
    assert parse_absorbed_energy_percent(log) == 27.17860
