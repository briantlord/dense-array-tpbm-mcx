"""Produce a matched, qualified comparison from immutable numerical results."""

import csv
import json
from pathlib import Path
import sys

from mcx_project.hashing import sha256_file
from mcx_project.provenance import capture_code
from mcx_project.validation import load_json


def main():
    root = Path(__file__).resolve().parents[1]
    audit_path = root / "results/two_wavelength_mc_audit_20260904_v1/result_summary.json"
    protocol_path = audit_path.parent / "protocol.json"
    corrected_path = root / "results/corrected_1070_overlap_20260904_v1/result_summary.json"
    refined_path = root / "results/surrogate_yue277_810_windows_rtx3080ti_opencl_analysis_v2/result_summary.json"
    result, protocol = load_json(audit_path), load_json(protocol_path)
    corrected, refined = load_json(corrected_path), load_json(refined_path)
    output = root / "results/review_comparison_public_20260905_v1"
    output.mkdir(parents=True, exist_ok=False)
    lines = ["# Qualified wavelength comparison — 4 September 2026", "",
        "This audit independently samples the same 277-source equal-total-launch surrogate at refined 810 nm and corrected-fat 1070 nm. It checks numerical variation under fixed model assumptions; it does not validate target-device hardware or establish clinical effects.", "",
        "## Whole-tissue absorption", "",
        "Values are percentages of total launched energy. Brackets are marginal 95% Student-t intervals for the mean of three independent high-count simulations.", "",
        "| Tissue | 810 mean [interval] | 1070 mean [interval] | Qualified 810/1070 |", "|---|---:|---:|---:|"]
    for name in ("gray_matter", "white_matter", "brain"):
        cells = []
        for wave in ("810", "1070"):
            s = result["results"][wave]["high"][name]
            cells.append(f"{100*s['mean']:.5f}% [{100*s['ci95_low']:.5f}, {100*s['ci95_high']:.5f}]")
        ratio = result["ratios_810_over_1070"][name]
        lines.append(f"| {name} | {cells[0]} | {cells[1]} | " + (f"{ratio['ratio']:.4g}x" if ratio['qualified'] else "not qualified") + " |")
    lines += ["", "## Depth endpoints and signal qualification", "",
        "Absolute values below are joules absorbed per 100 J total launched. A missing ratio is a failed reporting gate, not zero absorption or equal wavelengths. These depth shells are geometric distances to exterior-connected background, not named target regions.", "",
        "| Endpoint | 810 J/100 J | 1070 J/100 J | 810/1070 | Failed gates |", "|---|---:|---:|---:|---|"]
    table = []
    for name, ratio in result["ratios_810_over_1070"].items():
        failures = [wave + ": " + key for wave in ("810", "1070") for key, passed in result["gates"][wave][name]["checks"].items() if not passed]
        row = {"endpoint": name, "absorbed_J_per_100J_810": 100*ratio['numerator_mean'],
               "absorbed_J_per_100J_1070": 100*ratio['denominator_mean'], "qualified": ratio['qualified'],
               "ratio_810_over_1070": ratio['ratio'], "failed_gates": "; ".join(failures)}
        table.append(row)
        if "__depth" in name:
            lines.append(f"| {name} | {row['absorbed_J_per_100J_810']:.4e} | {row['absorbed_J_per_100J_1070']:.4e} | " + (f"{ratio['ratio']:.3g}x" if ratio['qualified'] else "not qualified") + f" | {row['failed_gates'] or 'none'} |")
    lines += ["", "## Audit design and limits", "",
        "- Eighteen direct aggregate runs: two wavelengths, three independent seeds, 27.7 million versus 277 million total photons, then 277 million at a 10-ns rather than 5-ns window. Counts are total across 277 emitters, not per emitter.",
        "- Frozen screening criteria: absorbed fraction at least 1e-8; replicate CV at most 5%; mean interval excluding zero; at most 10% mean change with photon count, time window, and relative to the saved basis. The engineering signal threshold is not a biological threshold.",
        "- Criteria were frozen before these runs, after seeing the earlier review. They are a bounded numerical screen, not an independently preregistered hypothesis test. Three replicates provide limited interval precision and normality evidence.",
        "- Ratios use independently sampled wavelength means. Ranges saved in JSON are constructed from separate marginal mean intervals, not joint 95% ratio confidence intervals. No multiple-endpoint coverage guarantee is asserted.",
        "- Optical, segmentation, source and coupling uncertainty is excluded. The established fat sensitivity and water counterfactual remain controlling evidence that parameter assumptions matter. Formal parameter-uncertainty intervals are still absent.",
        "- ROI qualification does not qualify individual voxels. The revised regional report suppresses voxel ratio maps. The old 1,054-fold deepest-white-matter value remains an unqualified historical point estimate.", "",
        "## Corrected overlap comparison", "",
        "These are field-first summaries from the existing per-emitter bases. They describe source contribution overlap within whole tissue masks; they are not cortical coverage or uncertainty-qualified spatial targeting metrics.", "",
        "| Tissue | 1070 EF_dom | 810 EF_dom | 1070 N_eff | 810 N_eff |", "|---|---:|---:|---:|---:|"]
    for name in ("gray_matter", "white_matter", "brain_total"):
        a, b = corrected["roi_results"][name]["field_first"], refined["roi_results"][name]["field_first"]
        lines.append(f"| {name} | {a['ef_dom']:.3f} | {b['ef_dom']:.3f} | {a['n_eff']:.3f} | {b['n_eff']:.3f} |")
    lines += ["", "The corrected-1070 analysis reverified all 277 native fields and reproduces the saved corrected-fat aggregate exactly. Historical high-fat overlap maps are not used in this matched table.", "",
        "## Device and remaining evidence", "",
        "Device-specific details are omitted. A device pilot needs measured source geometry, spectral weights, beam profile, and coupling evidence. The quantitative external benchmark and production optical gates remain unresolved.", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    with (output / "endpoint_qualification.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0])); writer.writeheader(); writer.writerows(table)
    manifest = {"provenance": capture_code(root, Path(__file__), sys.argv[1:]),
        "inputs": [{"path": p.relative_to(root).as_posix(), "sha256": sha256_file(p)} for p in (audit_path, protocol_path, corrected_path, refined_path)],
        "outputs": [{"path": p.relative_to(root).as_posix(), "sha256": sha256_file(p)} for p in sorted(output.iterdir())]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
