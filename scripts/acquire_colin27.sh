#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
atlas_root="$project_root/inputs/anatomy/colin27_2008"
archive="$atlas_root/raw/mni_colin27_2008_nifti.zip"
source_dir="$atlas_root/source"
source_url="https://packages.bic.mni.mcgill.ca/mni-models/colin27/mni_colin27_2008_nifti.zip"
expected_archive_sha256="462bae01973d15672769e3b7363e90956c0d3fb16a65ea51753fe9154d973d01"

mkdir -p "$(dirname "$archive")" "$source_dir"

if [[ ! -f "$archive" ]]; then
  curl --fail --location --retry 3 --continue-at - --output "$archive" "$source_url"
fi

actual_archive_sha256="$(shasum -a 256 "$archive" | awk '{print $1}')"
if [[ "$actual_archive_sha256" != "$expected_archive_sha256" ]]; then
  echo "Colin27 archive checksum mismatch" >&2
  echo "expected: $expected_archive_sha256" >&2
  echo "actual:   $actual_archive_sha256" >&2
  exit 1
fi

unzip -q -o "$archive" -d "$source_dir"
(
  cd "$project_root"
  shasum -a 256 -c inputs/anatomy/colin27_2008/checksums.sha256
)

echo "Colin27 2008 source acquired and checksum-verified at $source_dir"
