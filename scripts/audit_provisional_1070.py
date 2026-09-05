#!/usr/bin/env python3
"""Generate the independent provisional-1070 audit artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcx_project.optical_independent_audit import write_independent_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = write_independent_audit(args.project_root, check=args.check)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
