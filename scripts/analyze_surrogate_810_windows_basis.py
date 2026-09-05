#!/usr/bin/env python3
"""Run the shared streaming atlas analysis for the refined 810-nm basis."""

from pathlib import Path

import analyze_surrogate_1070_windows_basis as shared


SPEC = {}
SPEC["index_path"] = Path(
    "runs/surrogate_yue277_810_windows_rtx3080ti_opencl_basis_v3/index.json"
)
SPEC["inventory_path"] = Path(
    "results/surrogate_yue277_810_windows_rtx3080ti_opencl_v3/post_run_inventory.json"
)
SPEC["analysis_path"] = Path("configs/surrogate_yue277_810_v2_analysis.json")
SPEC["optical_path"] = Path(
    "inputs/optical_properties/provisional_810_v2/central_refined_primary.json"
)
SPEC["geometry_path"] = Path(
    "inputs/emitters/surrogate_yue277_810_v1/emitter_geometry.json"
)
SPEC["convergence_protocol_path"] = Path(
    "configs/surrogate_yue277_810_v2_regional_convergence_inheritance.json"
)
SPEC["output_dir"] = Path(
    "results/surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_v2"
)
SPEC["source_prefix"] = "SUR810"
SPEC["wavelength_nm"] = 810
SPEC["result_id"] = "surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_v2"
SPEC["manifest_id"] = (
    "surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_manifest_v2"
)
SPEC["regional_emitters"] = {
    "anterior": "SUR810_011",
    "left temporal": "SUR810_022",
    "posterior": "SUR810_031",
    "right temporal": "SUR810_040",
    "superior": "SUR810_275",
}


if __name__ == "__main__":
    shared.main(SPEC, entrypoint=Path(__file__))
