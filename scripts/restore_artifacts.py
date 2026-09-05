"""Check an artifact inventory, optionally restoring missing files from a mirror."""

import argparse
import json
from pathlib import Path

from mcx_project.artifact_restore import verify_or_restore
from mcx_project.validation import load_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--source", type=Path, help="Mirror with the same relative layout; omission is read-only")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = verify_or_restore(args.project_root.resolve(), load_json(args.inventory)["artifacts"],
                               args.source.resolve() if args.source else None)
    print(json.dumps(result, indent=2))
    return 1 if result["missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
