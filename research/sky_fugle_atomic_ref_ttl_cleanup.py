"""Fail-closed, bounded expiry cleanup of Sky *research-only* atomic tags.

No provider calls. Only exact namespace + syntax tags may be removed. Active
and future slots are preserved; the Git transport is checked after deletion.
The caller must use a research-governed GitHub Actions job with contents:write.
"""
from __future__ import annotations

import re
import subprocess
import time
from research.sky_fugle_atomic_ref_claim import PREFIX

REF_RE = re.compile(r"^refs/tags/sky-research-fugle-claim/[0-9a-f]{32}-([0-9]{1,16})$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SECONDS_PER_SLOT = 300
MIN_AGE_SECONDS = 48 * 3600
MAX_DELETIONS = 200


def eligible_refs(stdout: str, *, now: int, ttl: int = MIN_AGE_SECONDS) -> list[tuple[str, str]]:
    if type(now) is not int or ttl < MIN_AGE_SECONDS:
        raise ValueError("UNSAFE_TAG_TTL")
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            raise RuntimeError("MALFORMED_GIT_REMOTE_TAG_ROW")
        sha, ref = parts
        match = REF_RE.fullmatch(ref)
        if not match or not SHA_RE.fullmatch(sha):
            raise RuntimeError("UNEXPECTED_ATOMIC_TAG_NAMESPACE_OR_SHA")
        if ref in seen:
            raise RuntimeError("DUPLICATE_REMOTE_REF_ROW")
        seen.add(ref)
        slot = int(match.group(1))
        age = now - slot * SECONDS_PER_SLOT
        if age < 0:  # Future timestamp is unsafe, never delete.
            continue
        if age >= ttl:
            rows.append((ref, sha))
    if len(rows) > MAX_DELETIONS:
        raise RuntimeError("ATOMIC_TAG_CLEANUP_CAP_EXCEEDED")
    return rows


def remote_tags(git=subprocess.run) -> dict[str, str]:
    command = ["git", "ls-remote", "--refs", "--tags",
               "origin", PREFIX + "*"]
    result = git(command, capture_output=True, text=True, check=True, timeout=30)
    records: dict[str, str] = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) != 2 or fields[1] in records:
            raise RuntimeError("INVALID_REMOTE_TAG_RESPONSE")
        records[fields[1]] = fields[0]
    return records


def prune(*, now: int, git=subprocess.run) -> dict:
    before = remote_tags(git)
    lines = "\n".join(f"{sha}\t{ref}" for ref, sha in before.items())
    targets = eligible_refs(lines, now=now)
    rows = []
    for ref, expected in targets:
        # Re-read the particular ref immediately before deletion.
        command = ["git", "ls-remote", "--refs", "origin", ref]
        result = git(command, capture_output=True, text=True, check=True, timeout=20)
        if result.stdout.strip() != f"{expected}\t{ref}":
            raise RuntimeError("REMOTE_TEST_REF_CHANGED_ABORT")
        git(["git", "push", "origin", ":" + ref],
            capture_output=True, text=True, check=True, timeout=30)
        verify = git(command, capture_output=True, text=True, check=True, timeout=20)
        if verify.stdout.strip():
            raise RuntimeError("EXPIRED_ATOMIC_TAG_STILL_PRESENT")
        rows.append({"ref": ref, "result": "DELETED_READBACK_VERIFIED"})
    return {"schema": "SKY_ATOMIC_REF_TTL_CLEANUP_V1",
            "deletion_count": len(rows), "rows": rows,
            "retention_hours_min": MIN_AGE_SECONDS // 3600,
            "max_deletions_per_run": MAX_DELETIONS,
            "no_market_calls": True, "no_orders": True,
            "research_only": True, "production_eligible": False}


def main() -> None:
    import json
    from pathlib import Path
    outcome = prune(now=int(time.time()))
    path = Path("output/fugle_api_guard/ttl_cleanup.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(outcome, indent=2) + "\n")
    print("SKY_ATOMIC_TTL_CLEANUP_PASS", outcome["deletion_count"])


if __name__ == "__main__":
    main()
