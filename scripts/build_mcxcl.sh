#!/bin/sh
set -eu

MCXCL_COMMIT="bf695e81e239359f92a8fdd845bcdcacc50a7c31"
MCXCL_BUILD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mcxcl-build.XXXXXX")"
MCXCL_TARGET=".local/bin/mcxcl"
trap 'rm -rf "$MCXCL_BUILD_DIR"' EXIT HUP INT TERM

git clone --quiet https://github.com/fangq/mcxcl.git "$MCXCL_BUILD_DIR/source"
git -C "$MCXCL_BUILD_DIR/source" checkout --quiet "$MCXCL_COMMIT"
# The upstream Makefile has a generated-header dependency that is not safe
# under parallel make, so this build intentionally remains sequential.
make -C "$MCXCL_BUILD_DIR/source/src"
mkdir -p "$(dirname "$MCXCL_TARGET")"
install -m 0755 "$MCXCL_BUILD_DIR/source/bin/mcxcl" "$MCXCL_TARGET"
echo "installed $MCXCL_TARGET from MCX-CL commit $MCXCL_COMMIT"
shasum -a 256 "$MCXCL_TARGET"
