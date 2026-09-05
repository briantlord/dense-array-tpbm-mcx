"""Check tracked publication content, commit identity, and reachable history.

Findings never print matched secret values. Binary assets require explicit review
and a pinned digest in the publication policy. This complements human review.
"""

from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "provenance/publication_policy.json"
EMAIL = re.compile(rb"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}")
USER_PATH = re.compile(rb"(?:[A-Za-z]:[\\/]+Users[\\/]+|/(?:Users|home)/)[^\\/\s\"']+")
TOKENS = re.compile(rb"[a-z0-9]+")
SECRETS = {
    "private key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "service token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{25,}|\bxox[baprs]-[A-Za-z0-9-]{20,})",
    "cloud access key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "URL credentials": rb"https?://[^/\s:@\"']+:[^/\s@\"']+@",
    "signed token": rb"\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{20,}",
    "secret assignment": rb"[\"']?(?:api[_-]?key|client[_-]?secret|access[_-]?token|password|passwd)[\"']?\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']",
}
SECRET_RE = {name: re.compile(value, re.I if name == "secret assignment" else 0) for name, value in SECRETS.items()}
FORBIDDEN_SUFFIXES = {".pdf", ".docx", ".xlsx", ".pem", ".pfx", ".key"}
ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".nii", ".zip", ".gz", ".bin", ".npy", ".npz", ".exe", ".dll"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_text(data, policy):
    issues = []
    if USER_PATH.search(data):
        issues.append("personal absolute path")
    blocked = set(policy["protected_token_sha256"])
    if any(digest(token) in blocked for token in set(TOKENS.findall(data.lower()))):
        issues.append("excluded device identifier")
    for name, pattern in SECRET_RE.items():
        if pattern.search(data):
            issues.append(name)
    allowed = set(policy["approved_contact_email_sha256"])
    for match in EMAIL.finditer(data):
        address = match.group().lower()
        if not address.endswith(b"@users.noreply.github.com") and digest(address) not in allowed:
            issues.append("unapproved email address")
            break
    return issues


def check_file(path, data, policy):
    issues = check_text(path.encode(), policy)
    suffix = Path(path).suffix.lower()
    if suffix in FORBIDDEN_SUFFIXES or data.startswith(b"%PDF-"):
        return issues + ["excluded document or key file"]
    if path.split('/')[0] in {"tmp", "private", ".venv", ".venv-win", ".local"} or Path(path).name == ".env":
        issues.append("private/local directory or environment file")
    binary = suffix in ASSET_SUFFIXES or b"\0" in data[:2048] or data.startswith(b"PK\x03\x04")
    if binary:
        if policy["approved_binary_sha256"].get(path) != digest(data):
            issues.append("unreviewed binary or image asset")
        return issues
    if len(data) > 8_000_000:
        return issues + ["oversized unreviewed text file"]
    return issues + check_text(data, policy)


def git(*args, input=None):
    return subprocess.check_output(["git", *args], cwd=ROOT, input=input)


def check_repository(ref=None, history=False):
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if ref:
        rows = git("ls-tree", "-rz", ref).split(b"\0")
    else:
        rows = git("ls-files", "--stage", "-z").split(b"\0")
    records = []
    failures = []
    for row in rows:
        if not row:
            continue
        meta, path = row.split(b"\t", 1)
        parts = meta.split()
        oid = parts[2] if ref else parts[1]
        if parts[0] not in (b"100644", b"100755"):
            failures.append((path.decode(), "symlink, submodule, or unresolved index entry"))
            continue
        records.append((oid.decode(), path.decode()))
    if history:
        revision = ref or "HEAD"
        objects = git("rev-list", "--objects", revision).decode().splitlines()
        candidates = [line.split(" ", 1) for line in objects if " " in line]
        typed = git("cat-file", "--batch-check=%(objectname) %(objecttype)", input=("\n".join(x[0] for x in candidates)+"\n").encode()).decode().splitlines()
        blobs = {line.split()[0] for line in typed if line.endswith(" blob")}
        records.extend((oid, path) for oid, path in candidates if oid in blobs)
        for commit in git("rev-list", revision).decode().splitlines():
            raw = git("cat-file", "commit", commit)
            for line in raw.splitlines():
                if line.startswith((b"author ", b"committer ")):
                    match = re.search(rb"<([^>]+)>", line)
                    if not match or not match[1].endswith(b"@users.noreply.github.com"):
                        failures.append((commit[:12], "commit identity must use GitHub no-reply"))
            failures.extend((commit[:12], issue) for issue in check_text(raw, policy))
    pipe = subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    unique = set(records)
    try:
        for oid, path in sorted(unique):
            pipe.stdin.write((oid+"\n").encode())
            pipe.stdin.flush()
            header = pipe.stdout.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                raise ValueError("Could not read tracked blob")
            size = int(header[2])
            data = pipe.stdout.read(size)
            pipe.stdout.read(1)
            failures.extend((path, issue) for issue in check_file(path, data, policy))
    finally:
        pipe.stdin.close()
        pipe.wait()
    for path, issue in failures:
        # A path can itself contain private text. Identify it without publishing it.
        print(f"FAIL {issue}; object/path fingerprint {digest(path.encode())[:12]}")
    print(f"Publication privacy: {len(unique)} file versions checked; {len(failures)} findings.")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", help="Check a commit/tree instead of the staged index")
    parser.add_argument("--history", action="store_true", help="Also check all reachable ancestors")
    parser.add_argument("--pre-push", action="store_true", help="Validate outgoing refs from Git hook input")
    args = parser.parse_args()
    if args.pre_push:
        private = subprocess.run(["git", "config", "--bool", "privacy.privateWorkspace"], cwd=ROOT, capture_output=True, text=True)
        if private.stdout.strip() == "true":
            print("Push blocked: private research checkout. Use the reviewed publication checkout.")
            return 1
        status = 0
        for line in sys.stdin:
            local_ref, local_oid, remote_ref, remote_oid = line.split()
            if set(local_oid) == {"0"}:
                continue
            if not remote_ref.startswith("refs/heads/"):
                print("Push blocked: non-branch references require separate publication review.")
                return 1
            status |= check_repository(local_oid, history=True)
        return status
    return check_repository(args.ref, args.history)


if __name__ == "__main__":
    raise SystemExit(main())
