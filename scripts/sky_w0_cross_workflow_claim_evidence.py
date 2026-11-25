"""W0 research-only REAL GitHub atomic-ref conflict proof, no Fugle requests.

Two existing, separately named PR validation workflows call this script for
the exact same PR HEAD. Each tries the same *synthetic* historical-request
claim ref using the production GitHub create-ref transport. The first gets
HTTP 201, the second gets HTTP 422 with exact ref verified by independent
GET. Results remain separate immutable Actions Artifacts; a later W0 readback
must compare both workflows, HEADs, refs, and run identifiers.

Never calls api.fugle.tw or grants research/market/trading approval.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from research.sky_fugle_atomic_ref_claim import (
    claim_ref, github_create_ref, try_claim,
)
from research.sky_fugle_request_identity import canonical_fugle_request


def synthetic_claim(head_sha: str) -> tuple[str, str]:
    """Unique *non-stock*, immutable synthetic scope for each PR head."""
    if (not isinstance(head_sha, str) or len(head_sha) != 40 or
            any(c not in "0123456789abcdef" for c in head_sha)):
        raise ValueError("INVALID_EXACT_HEAD_SHA")
    symbol = "99" + str(int(hashlib.sha256(head_sha.encode("ascii")).hexdigest()[:12], 16) % 100_000_000).zfill(8)
    scope = canonical_fugle_request(
        "GET", f"/historical/candles/{symbol}",
        parameters={"from": "1900-01-01", "to": "1900-01-02", "timeframe": "5"},
    )
    return scope, claim_ref(scope, 1)


def main() -> None:
    output = Path("output/w0_claim_race") / "claim_result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "SKY_W0_REAL_CROSS_WORKFLOW_ATOMIC_CLAIM_V1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": os.getenv("GITHUB_REPOSITORY"),
        "workflow_name": os.getenv("GITHUB_WORKFLOW"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "event_name": os.getenv("GITHUB_EVENT_NAME"),
        "head_sha": None,
        "claim_ref": None,
        "status": "HOLD_UNVERIFIED_REAL_RACE",
        "claim_request_started_at_utc": None,
        "claim_request_finished_at_utc": None,
        "no_fugle_api_requests": True,
        "paid_calls": 0,
        "research_only": True,
        "production_eligible": False,
        "automatic_order": False,
    }
    try:
        if record["event_name"] != "pull_request":
            raise RuntimeError("PR_EVENT_REQUIRED")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        pull = event.get("pull_request", {})
        head = pull.get("head", {})
        repository = record["repository"]
        if (pull.get("base", {}).get("ref") != "main" or
                head.get("repo", {}).get("full_name") != repository or
                not repository or not record["run_id"] or
                not record["workflow_name"]):
            raise RuntimeError("SAME_REPOSITORY_PR_TO_MAIN_REQUIRED")
        sha = head.get("sha", "")
        scope, ref = synthetic_claim(sha)
        record["head_sha"] = sha
        record["claim_ref"] = ref
        record["scope_sha256"] = hashlib.sha256(scope.encode()).hexdigest()
        token = os.getenv("GH_TOKEN", "")
        if not token:
            raise RuntimeError("GITHUB_TOKEN_REQUIRED")
        # REAL GitHub POST git/refs; 422 is accepted only after exact GET
        # verifies the same ref. No retries and NO Fugle HTTP calls.
        record["claim_request_started_at_utc"] = datetime.now(timezone.utc).isoformat()
        try:
            won = try_claim(ref, sha, github_create_ref(repository, token))
        finally:
            record["claim_request_finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        record["status"] = "CREATED_201_WINNER" if won else "EXISTS_422_VERIFIED_LOSER"
    except Exception as exc:
        record["error_type"] = type(exc).__name__
        record["error_code"] = str(exc)[:120] if type(exc) in (ValueError, RuntimeError) else "EXTERNAL_GITHUB_ERROR"
    finally:
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("W0_CROSS_WORKFLOW_GITHUB_ATOMIC_CLAIM:", json.dumps(record, ensure_ascii=False))
    if record["status"] == "HOLD_UNVERIFIED_REAL_RACE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
