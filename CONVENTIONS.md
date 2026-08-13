# Repository Conventions

## Immutable identifiers

- Scenario IDs use lowercase snake case and end in `_vN`, for example `synthetic_test_only_v1` or `nominal_1070_v1`.
- Run IDs use `<scenario>__<UTC timestamp>__<8-hex configuration prefix>`, for example `synthetic_test_only_v1__20260813t120000z__a1b2c3d4`.
- Artifact IDs are immutable. A material content change creates a new versioned ID rather than silently replacing a frozen artifact.
- Emitter IDs are stable within a geometry lineage and must be unique.

## Coordinate frames and transforms

- Positions and transforms are stored in millimeters.
- Frames are explicit and right-handed unless their metadata says otherwise.
- Transforms are named `T_target_from_source`; ambiguous names such as `transform.json` are prohibited.

## Paths and checksums

- Manifest paths are POSIX-style and relative to the repository root.
- Absolute paths, parent traversal, and paths resolving outside the repository are rejected.
- Input and output checksums are lowercase SHA-256 values computed over exact file bytes.
- Large fields remain outside Git; their manifests, checksums, summaries, and compact QC artifacts remain tracked.

## Status and scientific scope

- `synthetic_test_only`, `benchmark`, and `production` are distinct scientific statuses.
- A structurally valid file containing `TBD` is incomplete and fails preflight.
- `complete` means all declared output files exist and match their manifest checksums. It does not imply scientific validation.
