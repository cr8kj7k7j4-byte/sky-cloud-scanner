"""Prototype for an atomic GitHub-ref claim: offline by default.

Unlike Action Artifact indexes, GitHub's create-ref endpoint rejects the
second creation of an identical ref. No live ref is created by this module
unless a caller explicitly supplies a write-enabled transport. Until
permissions, lifecycle, and cross-run tests pass this is RESEARCH_ONLY.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime

PREFIX = "refs/tags/sky-research-fugle-claim/"
HEX = re.compile(r"^[0-9a-f]{32}$")


def claim_ref(canonical_scope: str, slot: int) -> str:
    if not isinstance(canonical_scope, str) or not canonical_scope.startswith("sky:fugle:endpoint:v1:"):
        raise ValueError("CANONICAL_ENDPOINT_SCOPE_REQUIRED")
    if not HEX.fullmatch(canonical_scope.rsplit(":", 1)[-1]):
        raise ValueError("INVALID_ENDPOINT_DIGEST")
    if type(slot) is not int or slot < 1:
        raise ValueError("INVALID_SLOT")
    return PREFIX + hashlib.sha256(canonical_scope.encode("ascii")).hexdigest()[:32] + "-" + str(slot)


def try_claim(ref: str, sha: str, create_ref) -> bool:
    """create_ref(ref, sha) -> {'status':201} or {'status':422,'existing':True}.

    The only success condition is an actual 201 create-ref result. HTTP 422
    without a separately verified same-name existing ref must fail closed.
    """
    if not ref.startswith(PREFIX) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("INVALID_ATOMIC_CLAIM_ARGUMENTS")
    result = create_ref(ref, sha)
    if not isinstance(result, dict):
        raise RuntimeError("INVALID_CLAIM_API_RESPONSE")
    if result.get("status") == 201 and result.get("ref") == ref:
        return True
    if result.get("status") == 422 and result.get("existing") is True:
        return False
    raise RuntimeError("ATOMIC_CLAIM_UNVERIFIED")
