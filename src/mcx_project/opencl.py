"""Thin, testable adapter around the PMCXCL native binding."""

from __future__ import annotations

from importlib.metadata import version
from typing import Any

import numpy as np


def _module():
    try:
        import _pmcxcl as pmcxcl
    except ImportError as error:
        raise RuntimeError(
            f"PMCXCL's native extension is unavailable; install the project with "
            f"the opencl extra and verify its architecture: {error}"
        ) from error
    return pmcxcl


def package_version() -> str:
    return version("pmcxcl")


def engine_version() -> str:
    return str(_module().version())


def gpuinfo() -> Any:
    return _module().gpuinfo()


def synthetic_field_from_config(
    config_record: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Run a validated homogeneous configuration and return its field and summary."""

    pmcxcl = _module()
    volume = config_record["volume"]
    if volume["generator"] != "homogeneous_cube":
        raise ValueError("the smoke runner only supports a homogeneous_cube volume")
    source = config_record["source"]
    gates = config_record["time_gates_s"]
    config = {
        "nphoton": int(config_record["nphoton"]),
        "vol": np.full(
            tuple(volume["shape_voxels"]), volume["label"], dtype=np.uint8
        ),
        "tstart": float(gates["start"]),
        "tend": float(gates["end"]),
        "tstep": float(gates["step"]),
        "srcpos": source["position_voxels"],
        "srcdir": source["direction"],
        "prop": np.asarray(config_record["properties_mm"], dtype=np.float64),
        "seed": int(config_record["seed"]),
        "issrcfrom0": 1,
        "isnormalize": int(config_record["isnormalize"]),
        "outputtype": config_record["outputtype"],
        "autopilot": 1,
    }
    # The native binding documents keyword arguments. Passing the entire mapping
    # positionally can appear to run but return a corrupted NumPy buffer on macOS.
    result = pmcxcl.run(**config)
    if not isinstance(result, dict) or "flux" not in result:
        raise RuntimeError("PMCXCL returned an unexpected result structure")

    flux = np.asarray(result["flux"], dtype=np.float64)
    if flux.size == 0 or not np.all(np.isfinite(flux)):
        raise RuntimeError("PMCXCL returned an invalid flux volume")
    raw_minimum = float(np.min(flux))
    if raw_minimum < -1e-20:
        raise RuntimeError(
            f"PMCXCL returned materially negative flux values (minimum {raw_minimum})"
        )
    tiny_negative_count = int(np.count_nonzero(flux < 0))
    flux = np.maximum(flux, 0.0)
    maximum = float(np.max(flux))
    standard_deviation = float(np.std(flux, dtype=np.float64))
    if maximum <= 0 or standard_deviation <= 0:
        raise RuntimeError("PMCXCL returned a nonpositive or spatially uniform flux volume")

    summary = {
        "backend": "pmcxcl",
        "backend_version": package_version(),
        "engine_version": engine_version(),
        "configuration_id": config_record["configuration_id"],
        "photons": int(config_record["nphoton"]),
        "seed": int(config_record["seed"]),
        "shape": list(flux.shape),
        "minimum": float(np.min(flux)),
        "raw_minimum": raw_minimum,
        "maximum": maximum,
        "standard_deviation": standard_deviation,
        "positive_voxels": int(np.count_nonzero(flux > 0)),
        "tiny_negative_voxels_clipped_for_summary": tiny_negative_count,
        "sum": float(np.sum(flux, dtype=np.float64)),
    }
    return flux, summary


def synthetic_smoke_from_config(config_record: dict[str, Any]) -> dict[str, Any]:
    """Run a validated homogeneous configuration and return its compact summary."""

    _, summary = synthetic_field_from_config(config_record)
    return summary


def synthetic_smoke(*, photons: int = 100_000, seed: int = 1_648_335_518) -> dict[str, Any]:
    """Backward-compatible programmatic smoke fixture."""

    if photons < 1:
        raise ValueError("photons must be positive")
    return synthetic_smoke_from_config(
        {
            "configuration_id": "programmatic_synthetic_smoke",
            "nphoton": photons,
            "volume": {
                "generator": "homogeneous_cube",
                "shape_voxels": [60, 60, 60],
                "label": 1,
            },
            "time_gates_s": {"start": 0.0, "end": 5e-9, "step": 5e-9},
            "source": {
                "position_voxels": [30.0, 30.0, 0.0],
                "direction": [0.0, 0.0, 1.0],
            },
            "properties_mm": [[0.0, 0.0, 0.0, 1.0], [0.005, 1.0, 0.01, 1.37]],
            "seed": seed,
            "outputtype": "flux",
            "isnormalize": 1,
        }
    )
