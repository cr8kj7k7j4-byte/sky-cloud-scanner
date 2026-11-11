"""Prototype for an atomic GitHub-ref claim: offline by default.

Unlike Action Artifact indexes, GitHub's create-ref endpoint rejects the
second creation of an identical ref. No live ref is created by this module
unless a caller explicitly supplies a write-enabled transport. Until
permissions, lifecycle, and cross-run tests pass this is RESEARCH_ONLY.
"""
from __future__ import annotations

import hashlib
import re
import json
import os
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from datetime import datetime, timezone

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

def guard_fugle_request(url: str, params: dict | None = None) -> None:
    """Optional endpoint claim immediately before a real Fugle HTTP request.

    This guard is research-only and defaults to OFF. Unknown URLs or GitHub
    write errors fail closed when enabled. Tests must mock provider transport.
    """
    if os.getenv("SKY_PAID_ATOMIC_ENFORCE") != "1":
        return
    from research.sky_fugle_request_identity import canonical_fugle_request

    scope = canonical_fugle_request("GET", url, parameters=params)
    slot = int(datetime.now(timezone.utc).timestamp()) // 300
    ref = claim_ref(scope, slot)
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GH_TOKEN", "")
    sha = os.getenv("GITHUB_SHA", "")
    if not try_claim(ref, sha, github_create_ref(repo, token)):
        raise RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")


def github_create_ref(repo: str, token: str):
    """Return an atomic GitHub create-ref transport. 403/timeout fail closed."""
    if not token or len(repo.split("/")) != 2:
        raise RuntimeError("MISSING_ATOMIC_GITHUB_WRITE_ACCESS")
    base = "https://api.github.com/repos/" + repo
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Sky-Research-Atomic-Claim",
    }
    def create(ref: str, sha: str):
        body = json.dumps({"ref": ref, "sha": sha}).encode("utf-8")
        request = Request(base + "/git/refs", headers=headers, data=body, method="POST")
        try:
            with urlopen(request, timeout=12) as response:
                result = json.load(response)
                return {"status": response.status, "ref": result.get("ref")}
        except HTTPError as error:
            if error.code != 422:
                raise
            # A generic HTTP 422 is NOT evidence of an existing ref.
            # Only a verified exact-name GitHub ref may block as duplicate.
            name = quote(ref.removeprefix("refs/"), safe="/")
            with urlopen(Request(base + "/git/ref/" + name, headers=headers),
                         timeout=12) as response:
                existing = json.load(response)
            valid = (existing.get("ref") == ref
                     and existing.get("object", {}).get("type") in ("commit", "tag")
                     and bool(re.fullmatch(r"[0-9a-f]{40}",
                                           existing.get("object", {}).get("sha", ""))))
            return {"status": 422, "existing": valid}
    return create
