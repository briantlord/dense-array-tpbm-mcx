#!/usr/bin/env python3
"""Run the shared streaming atlas analysis for the refined 810-nm basis."""

from pathlib import Path

import analyze_surrogate_1070_windows_basis as shared


shared.INDEX_PATH = Path(
    "runs/surrogate_yue277_810_windows_rtx3080ti_opencl_basis_v3/index.json"
)
shared.INVENTORY_PATH = Path(
    "results/surrogate_yue277_810_windows_rtx3080ti_opencl_v3/post_run_inventory.json"
)
shared.ANALYSIS_PATH = Path("configs/surrogate_yue277_810_v2_analysis.json")
shared.OPTICAL_PATH = Path(
    "inputs/optical_properties/provisional_810_v2/central_refined_primary.json"
)
shared.GEOMETRY_PATH = Path(
    "inputs/emitters/surrogate_yue277_810_v1/emitter_geometry.json"
)
shared.CONVERGENCE_PROTOCOL_PATH = Path(
    "configs/surrogate_yue277_810_v2_regional_convergence_inheritance.json"
)
shared.OUTPUT_DIR = Path(
    "results/surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_v2"
)
shared.SOURCE_PREFIX = "SUR810"
shared.WAVELENGTH_NM = 810
shared.RESULT_ID = "surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_v2"
shared.MANIFEST_ID = (
    "surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_manifest_v2"
)
shared.REGIONAL_EMITTERS = {
    "anterior": "SUR810_011",
    "left temporal": "SUR810_022",
    "posterior": "SUR810_031",
    "right temporal": "SUR810_040",
    "superior": "SUR810_275",
}


if __name__ == "__main__":
    shared.main()
