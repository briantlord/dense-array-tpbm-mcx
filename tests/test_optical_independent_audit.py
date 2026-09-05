from pathlib import Path

from mcx_project.optical_independent_audit import (
    audit_provisional_1070,
    write_independent_audit,
)


ROOT = Path(__file__).resolve().parents[1]


def test_independent_quantity_unit_wavelength_audit_passes_mechanically() -> None:
    report = audit_provisional_1070(ROOT)
    assert report["mechanical_status"] == "pass"
    assert report["scientific_status"] == "blocked"
    assert report["production_launch_allowed"] is False
    assert report["errors"] == []
    assert len(report["tissues"]) == 12
    assert all(row["status"] == "pass" for row in report["tissues"])
    assert len(report["variants"]) == 14
    assert all(row["status"] == "pass" for row in report["variants"])


def test_independent_audit_artifacts_are_fresh() -> None:
    report = write_independent_audit(ROOT, check=True)
    assert len(report["scientific_blockers"]) >= 5
