#!/usr/bin/env python3
"""Run a frozen, bounded direct-aggregate audit; never overwrite a prior audit."""

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from mcx_project.aggregate_inputs import load_aggregate_inputs
from mcx_project.basis import deterministic_seed
from mcx_project.engine_identity import validate_engine_identity
from mcx_project.hashing import sha256_file
from mcx_project.provenance import capture_code
from mcx_project.standalone import probe_mcxcl, render_mcxcl_input, load_jnii_field, parse_absorbed_energy_percent
from mcx_project.uncertainty import depth_masks, replicate_summary, endpoint_gate, qualified_ratio
from mcx_project.validation import load_json


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol_path = (root / args.protocol).resolve()
    protocol = load_json(protocol_path)
    output = root / protocol["output_path"]
    output.mkdir(parents=True, exist_ok=False)
    code = capture_code(root, Path(__file__), sys.argv[1:])
    write_json(output / "protocol.json", protocol)
    write_json(output / "code_provenance.json", code)
    binary = root / protocol["binary_path"]
    identity = probe_mcxcl(binary)
    validate_engine_identity(load_json(root / protocol["environment_path"]), identity)
    results, configurations_by_wave, labels_by_wave, masks_by_wave, baseline_by_wave = {}, {}, {}, {}, {}
    for scenario in protocol["scenarios"]:
        wave = str(scenario["wavelength_nm"])
        index_path = root / scenario["basis_index_path"]
        if sha256_file(index_path) != scenario["basis_index_sha256"]:
            raise ValueError("frozen basis index changed")
        configs, labels = load_aggregate_inputs(root, index_path)
        if len(configs) != 277:
            raise ValueError("audit requires the complete 277-source surrogate")
        configurations_by_wave[wave], labels_by_wave[wave] = configs, labels
        masks_by_wave[wave] = depth_masks(labels)
        baseline_path = root / scenario["baseline_fluence_path"]
        if sha256_file(baseline_path) != scenario["baseline_fluence_sha256"]:
            raise ValueError("saved comparison field changed")
        fluence = np.load(baseline_path, mmap_mode="r")
        mua = np.array(configs[0]["properties_mm"])[:,0][labels]
        baseline_by_wave[wave] = {name: float(np.sum(fluence[mask] * mua[mask], dtype=np.float64))
                                  for name, mask in masks_by_wave[wave].items()}
    a, b = configurations_by_wave.values()
    if not np.array_equal(*labels_by_wave.values()):
        raise ValueError("wavelength anatomies differ")
    for first, second in zip(a,b):
        for key in ("position_voxels", "direction", "type"):
            if first["source"][key] != second["source"][key]:
                raise ValueError("wavelength source geometries differ")
    for wave, configs in configurations_by_wave.items():
        labels, masks = labels_by_wave[wave], masks_by_wave[wave]
        mua = np.array(configs[0]["properties_mm"])[:,0][labels]
        results[wave] = {}
        for setting in protocol["settings"]:
            stage = setting["name"]
            stage_results = []
            for replicate in range(1, protocol["replicates"] + 1):
                if sha256_file(binary) != identity["executable_sha256"]:
                    raise ValueError("MCX executable changed during audit")
                run_dir = output / f"nm{wave}_{stage}_r{replicate}"
                run_dir.mkdir()
                volume = run_dir / "volume.uint8.bin"
                volume.write_bytes(labels.tobytes(order="F"))
                config = copy.deepcopy(configs[0])
                config["nphoton"] = setting["total_photons"]
                config["seed"] = deterministic_seed(protocol["protocol_id"], f"{wave}_{stage}", replicate)
                config["time_gates_s"] = {"start": 0., "end": setting["end_s"], "step": setting["end_s"]}
                document = render_mcxcl_input(config, "audit", volume_file=volume.name)
                document["Optode"]["Source"]["Pos"] = [c["source"]["position_voxels"] for c in configs]
                document["Optode"]["Source"]["Dir"] = [c["source"]["direction"] for c in configs]
                input_path = run_dir / "mcx_input.json"
                write_json(input_path, document)
                started = time.perf_counter()
                command = [str(binary), "-f", input_path.name, "-Z", "2", "--srcid", "0", "-G", "1"]
                completed = subprocess.run(command, cwd=run_dir, capture_output=True, text=True)
                elapsed = time.perf_counter() - started
                log = completed.stdout + completed.stderr
                (run_dir / "mcxcl.log").write_text(log, encoding="utf-8")
                if completed.returncode:
                    raise RuntimeError(f"MCX failed; inspect {run_dir}")
                field_path = run_dir / "audit.jnii"
                field = np.asarray(load_jnii_field(field_path), dtype=np.float64).squeeze()
                if field.shape != labels.shape or not np.isfinite(field).all() or field.min() < 0:
                    raise ValueError("invalid fluence field")
                absorbed = field * mua
                total_percent = 100 * float(absorbed.sum(dtype=np.float64))
                log_percent = parse_absorbed_energy_percent(log)
                if log_percent is None or abs(total_percent - log_percent) > .05:
                    raise ValueError("aggregate absorbed-energy closure failed")
                row = {"seed": config["seed"], "replicate": replicate, "setting": setting,
                       "elapsed_seconds": elapsed, "engine": identity, "command": command,
                       "total_absorbed_percent": total_percent, "log_absorbed_percent": log_percent,
                       "endpoints": {name: float(absorbed[mask].sum(dtype=np.float64)) for name, mask in masks.items()},
                       "brain_integrated_fluence": float(field[masks["brain"]].sum(dtype=np.float64)),
                       "artifacts": [{"path": p.relative_to(root).as_posix(), "sha256": sha256_file(p)}
                                     for p in (volume, input_path, field_path, run_dir / "mcxcl.log")]}
                write_json(run_dir / "result.json", row)
                stage_results.append(row)
                print(json.dumps({"wavelength": wave, "stage": stage, "replicate": replicate,
                                  "seconds": elapsed, "brain_absorbed_fraction": row["endpoints"]["brain"]}), flush=True)
            results[wave][stage] = {name: replicate_summary([row["endpoints"][name] for row in stage_results]) for name in masks}
            results[wave][stage]["brain_integrated_fluence"] = replicate_summary([row["brain_integrated_fluence"] for row in stage_results])
    gates = {wave: {name: endpoint_gate(stages["low"][name], stages["high"][name], stages["extended"][name],
                                      baseline_by_wave[wave][name], protocol["criteria"])
                    for name in masks_by_wave[wave]} for wave, stages in results.items()}
    ratios = {name: qualified_ratio(results["810"]["high"][name], results["1070"]["high"][name],
                                   gates["810"][name], gates["1070"][name]) for name in masks_by_wave["810"]}
    summary = {"protocol_id": protocol["protocol_id"], "status": "complete", "estimator": "equal total launch across 277 sources",
               "scope": "Conditional Monte Carlo screening, not optical/anatomy/device uncertainty or voxelwise convergence.",
               "endpoint_unit": "absorbed fraction per unit total launched energy", "results": results,
               "saved_basis_endpoints": baseline_by_wave, "gates": gates, "ratios_810_over_1070": ratios}
    write_json(output / "result_summary.json", summary)
    write_json(output / "result_manifest.json", {"code": code,
        "inputs": [{"path": protocol_path.relative_to(root).as_posix(), "sha256": sha256_file(protocol_path)}],
        "outputs": [{"path": p.relative_to(root).as_posix(), "sha256": sha256_file(p)} for p in sorted(output.rglob("*")) if p.is_file()]})
    print(json.dumps({"status": "complete", "qualified_ratios": sum(r["qualified"] for r in ratios.values()), "endpoint_count": len(ratios)}))


if __name__ == "__main__":
    main()
