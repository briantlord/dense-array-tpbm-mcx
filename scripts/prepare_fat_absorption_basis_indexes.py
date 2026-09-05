#!/usr/bin/env python3
"""Prepare the three immutable 277-source fat-absorption basis indexes."""

from __future__ import annotations

import json
from pathlib import Path

from mcx_project.basis import prepare_basis_plan


ROOT = Path(__file__).resolve().parents[1]
PLANS = (
    Path("configs/surrogate_yue277_1070_windows_rtx3080ti_fat_abs_005065_basis_v1.json"),
    Path("configs/surrogate_yue277_1070_windows_rtx3080ti_fat_abs_010_basis_v1.json"),
    Path("configs/surrogate_yue277_1070_windows_rtx3080ti_fat_abs_030_basis_v1.json"),
)


def main() -> int:
    reports = []
    for plan in PLANS:
        index = prepare_basis_plan(ROOT / plan, ROOT)
        reports.append(
            {
                "plan": plan.as_posix(),
                "basis_set_id": index["basis_set_id"],
                "run_count": len(index["runs"]),
            }
        )
    print(json.dumps({"status": "prepared_not_executed", "bases": reports}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
