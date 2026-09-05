"""Inventory ignored artifacts referenced by controlling bases and result manifests."""

import json
from pathlib import Path
import subprocess

from mcx_project.hashing import sha256_file
from mcx_project.provenance import project_path
from mcx_project.validation import load_json


INDEXES = (
    "runs/surrogate_yue277_810_windows_rtx3080ti_opencl_basis_v3/index.json",
    "runs/surrogate_yue277_1070_windows_rtx3080ti_fat_abs_010_basis_v1/index.json",
    "runs/surrogate_yue277_1070_windows_rtx3080ti_water_whole_head_basis_v1/index.json",
)


def main():
    root = Path(__file__).resolve().parents[1]
    references, inputs = {}, []
    def add(record):
        if "path" not in record or "sha256" not in record:
            return
        path = project_path(root, record["path"])
        relative = path.relative_to(root).as_posix()
        if relative in references and references[relative] != record["sha256"]:
            raise ValueError(f"conflicting artifact checksums: {relative}")
        references[relative] = record["sha256"]
    for relative in INDEXES:
        path = root / relative
        inputs.append({"path": relative, "sha256": sha256_file(path)})
        for row in load_json(path)["runs"]:
            manifest = load_json(root / row["manifest_path"])
            for record in [*manifest["inputs"].values(), *manifest["outputs"]]:
                add(record)
            add(load_json(root / row["configuration_path"])["volume"])
    result_manifests = sorted({*(root / "results").glob("*/manifest.json"),
                               *(root / "results").glob("*/result_manifest.json")})
    for path in result_manifests:
        inputs.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)})
        manifest = load_json(path)
        for record in [*manifest.get("inputs", []), *manifest.get("outputs", [])]:
            add(record)
    ignored = subprocess.run(["git", "check-ignore", "--stdin", "-z"], cwd=root,
        input=("\0".join(sorted(references)) + "\0").encode("utf-8"), capture_output=True)
    if ignored.returncode not in (0,1):
        raise RuntimeError(ignored.stderr)
    artifacts = []
    for relative in ignored.stdout.decode("utf-8").split("\0"):
        if not relative:
            continue
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"referenced external artifact is absent: {relative}")
        artifacts.append({"path": relative, "sha256": references[relative], "bytes": path.stat().st_size})
    if not artifacts:
        raise ValueError("expected external fields but inventory is empty; inspect Git ignore detection")
    output = root / "provenance/external_artifacts_20260904_v1.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump({"inventory_id": "external_artifacts_20260904_v1", "date": "2026-09-04",
            "scope": "Ignored files referenced by the corrected-1070, refined-810 and water-counterfactual basis manifests/configurations and all first-level result manifests present at inventory creation. Not every historical raw field or publisher paper.",
            "verification": "Expected SHA-256 copied from controlling records; verify bytes using restore_artifacts.py without --source.",
            "inputs": inputs, "artifact_count": len(artifacts), "total_bytes": sum(r["bytes"] for r in artifacts),
            "artifacts": artifacts}, stream, indent=2)
        stream.write("\n")
    print(f"Inventoried {len(artifacts)} external artifacts")


if __name__ == "__main__":
    main()
