# Public publication and privacy

The public repository contains reviewed simulation code, configurations, compact records, scientific reports and plots, citations, and source snapshots. Manufacturer information, device images, research-paper files, local runtimes, and large raw fields are excluded. Complete original research evidence remains in the private workspace.

The September 5, 2026 privacy cleanup removes personal directory prefixes from 46 published files and replaces personal commit emails with GitHub no-reply identities throughout public branch history. It preserves the sequence of research commits and numerical results. The project review uses repository-relative links.

See `publication_redactions_20260905.json` for original and redacted SHA-256 digests. Original scientific hashes and research revision identifiers still refer to original research records; they are not hashes of redacted copies or rewritten commits. Restore originals when reproduction requires original byte-for-byte inputs. Original records were not edited to make public hashes match.

## Future updates

1. Work in a reviewed publication checkout. Pushes from the private research checkout are blocked locally.
2. Use your GitHub-provided no-reply commit email and enable the hook with `git config core.hooksPath .githooks`.
3. Review text, metadata, and images for identifying or excluded material. Redact copies and record changes while preserving original research evidence.
4. Stage changes and run `uv run --frozen python scripts/check_publication.py`, then `uv run --frozen python scripts/check_software.py`.
5. Commit and run `uv run --frozen python scripts/check_publication.py --ref HEAD --history`. The pre-push hook checks outgoing history and CI repeats the scan.

Binary assets are pinned by path and SHA-256 in `publication_policy.json`; policy changes require reviewing the actual asset. Pattern checks supplement human review and cannot prove the absence of every kind of private information.

## Existing clones and older links

The cleanup changes commit IDs. Create a fresh clone before contributing, or carefully transplant reviewed changes onto the new history. Do not merge or push old branches back. Existing pull-request references, hosting caches, and copies made by others may retain earlier commits even after branch replacement; this cleanup cannot erase other people's copies.

This publication checkout is not a full research backup. See `RESTORE.md` for recovery requirements.
