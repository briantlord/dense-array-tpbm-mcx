"""Run portable checks without a GPU, downloaded anatomy, or raw fields."""

from pathlib import Path
import subprocess
import sys


TEST_MODULES = (
    "metrics", "optics", "aggregation", "standalone", "execution_guards",
    "uncertainty", "targeted_tally_optical_override", "basis", "preflight",
    "artifact_restore", "analysis_configuration", "regional_reporting",
)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    raise SystemExit(subprocess.call(
        [sys.executable, "-m", "pytest", *[f"tests/test_{name}.py" for name in TEST_MODULES], "-q"],
        cwd=root,
    ))
