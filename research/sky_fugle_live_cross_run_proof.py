"""Run a bounded, read-only Fugle quote probe through the atomic research guard."""
import json
import os
import time
from pathlib import Path
from unittest.mock import patch

from research.sky_fugle_atomic_ref_claim import claim_ref
from research.sky_fugle_request_identity import canonical_fugle_request
from src import fugle


def main():
    if os.environ["GITHUB_EVENT_NAME"] != "workflow_dispatch" or os.environ["GITHUB_REF"] != (
        "refs/heads/research/sky-536-531-guard-readback"
    ):
        raise SystemExit("RESEARCH_MANUAL_DISPATCH_REQUIRED")
    start = int(os.environ["SKY_PROOF_START_EPOCH"])
    now = time.time()
    if not now - 5 <= start <= now + 180:
        raise SystemExit("RENDEZVOUS_OUTSIDE_ALLOWED_WINDOW")
    if not fugle.FUGLE_API_KEY:
        raise SystemExit("FUGLE_API_KEY_REQUIRED")

    sha = os.environ["GITHUB_SHA"]
    # Isolate this one-time acceptance pair from rolling market scans and mock proofs.
    slot = ((1 << 48) + int(sha[:12], 16)) * (1 << 32) + start
    endpoint = "/intraday/quote/2317"
    scope = canonical_fugle_request("GET", endpoint)
    receipt = {
        "schema": "SKY_FUGLE_LIVE_CROSS_WORKFLOW_PROOF_V1",
        "workflow": os.environ["GITHUB_WORKFLOW"],
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "head_sha": sha,
        "scope": scope,
        "claim_ref": claim_ref(scope, slot),
        "start_epoch": start,
        "outcome": "FAILED_CLOSED",
        "real_http_attempts": 0,
    }
    if receipt["run_attempt"] != "1":
        raise SystemExit("START_A_FRESH_PAIR_INSTEAD_OF_RERUN")

    get = fugle.requests.get

    def counted_get(url, **kwargs):
        if url != fugle.BASE + endpoint or receipt["real_http_attempts"]:
            raise RuntimeError("UNEXPECTED_PROVIDER_REQUEST")
        receipt["real_http_attempts"] += 1
        response = get(url, allow_redirects=False, **kwargs)
        receipt["http_status"] = response.status_code
        return response

    time.sleep(max(0, start - time.time()))
    receipt["claim_started_epoch"] = time.time()
    try:
        with patch("research.sky_fugle_atomic_ref_claim.datetime") as clock, patch.object(
            fugle.requests, "get", counted_get
        ):
            clock.now.return_value.timestamp.return_value = slot * 300
            result = fugle.get_quote("2317")
        if (
            receipt.get("http_status") != 200
            or not isinstance(result, dict)
            or result.get("symbol") != "2317"
        ):
            raise RuntimeError("INVALID_PROVIDER_RESPONSE")
        receipt["outcome"] = "ATOMIC_WINNER"
    except RuntimeError as exc:
        if str(exc) != "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED" or receipt["real_http_attempts"]:
            raise
        receipt["outcome"] = "DUPLICATE_BLOCKED"
    finally:
        receipt["finished_epoch"] = time.time()
        path = Path("output/fugle_live_cross_run/receipt.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
