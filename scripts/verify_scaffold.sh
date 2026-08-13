#!/bin/sh
set -eu

MCX_UV_CACHE_DIR="${TMPDIR:-/tmp}/mcx-project-uv-cache"
export UV_CACHE_DIR="$MCX_UV_CACHE_DIR"

uv sync --extra opencl --group dev
.venv/bin/pytest -q
.venv/bin/mcx-project preflight \
  runs/synthetic_smoke_m4pro/manifest.json \
  --project-root .
.venv/bin/mcx-project smoke-opencl \
  runs/synthetic_smoke_m4pro/manifest.json \
  --project-root .
