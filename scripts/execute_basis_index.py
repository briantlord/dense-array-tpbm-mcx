#!/usr/bin/env python3
"""Execute a prepared basis index sequentially with resumable manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mcx_project.basis import BasisExecutionError, execute_basis_run
from mcx_project.standalone import (
    probe_mcxcl,
    resolve_mcxcl_binary,
    standalone_field_from_config,
)
from mcx_project.validation import load_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--limit", type=int)
    parser.add_argument("--continue-on-error", action="store_true")
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    index_path = arguments.index.resolve()
    if not index_path.is_relative_to(root):
        raise SystemExit("index must be inside the project root")
    index = load_json(index_path)
    runs = index["runs"]
    if arguments.limit is not None:
        if arguments.limit < 1:
            raise SystemExit("--limit must be positive")
        runs = runs[: arguments.limit]
    binary = resolve_mcxcl_binary(root)
    identity = probe_mcxcl(binary)
    complete = 0
    skipped = 0
    failed = 0

    def execute(config: dict[str, Any], run_directory: Path):
        return standalone_field_from_config(
            config,
            run_directory,
            binary,
            project_root=root,
            expected_identity=identity,
        )

    for number, run in enumerate(runs, start=1):
        manifest_path = root / run["manifest_path"]
        try:
            status = execute_basis_run(manifest_path, root, execute, engine_probe=lambda: identity)
            complete += status == "complete"
            skipped += status == "skipped"
            print(
                json.dumps(
                    {
                        "basis_set_id": index["basis_set_id"],
                        "emitter_id": run["emitter_id"],
                        "number": number,
                        "status": status,
                        "total": len(runs),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        except BasisExecutionError as error:
            failed += 1
            print(
                json.dumps(
                    {
                        "basis_set_id": index["basis_set_id"],
                        "emitter_id": run["emitter_id"],
                        "error": str(error),
                        "number": number,
                        "status": "failed",
                        "total": len(runs),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            if not arguments.continue_on_error:
                raise SystemExit(2) from error
    print(
        json.dumps(
            {
                "basis_set_id": index["basis_set_id"],
                "complete": complete,
                "failed": failed,
                "skipped": skipped,
                "status": "complete" if failed == 0 else "completed_with_failures",
                "total": len(runs),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
