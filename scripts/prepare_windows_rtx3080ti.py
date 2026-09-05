#!/usr/bin/env python3
"""Bind the surrogate basis plan to a probed Windows RTX 3080 Ti runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcx_project.windows_handoff import prepare_windows_rtx3080ti_opencl_handoff


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    report = prepare_windows_rtx3080ti_opencl_handoff(
        arguments.project_root, arguments.binary
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
