"""Research-only canonical quote claims with an isolated GitHub write job.

No Fugle access is performed. All symbols are validated before any claim.
If a claim is rejected, the downstream read-only paid Job must never start.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from research.sky_fugle_atomic_ref_claim import claim_ref, github_create_ref, try_claim
from research.sky_fugle_request_identity import canonical_fugle_request

SYMBOL_RE = re.compile(r"^[1-9][0-9]{3,5}$")


def validate_symbols(raw: str) -> list[str]:
    parts = [p.strip() for p in raw.split(",")] if isinstance(raw, str) else []
    if not 1 <= len(parts) <= 20 or any(not SYMBOL_RE.fullmatch(x) for x in parts):
        raise ValueError("INVALID_SELECTED_QUOTE_SYMBOLS")
    return list(dict.fromkeys(parts))


def claim_selected_quotes(raw: str, *, sha: str, slot: int, create_ref) -> dict:
    symbols = validate_symbols(raw)
    if not isinstance(slot, int) or slot <= 0:
        raise ValueError("INVALID_ATOMIC_SLOT")
    entries = []
    # Validate every URL before writing the first ref.
    refs = []
    for symbol in symbols:
        scope = canonical_fugle_request("GET", "/intraday/quote/" + symbol)
        refs.append((symbol, claim_ref(scope, slot)))
    for symbol, ref in refs:
        if not try_claim(ref, sha, create_ref):
            raise RuntimeError("DUPLICATE_SELECTED_QUOTE_REF_BLOCKED")
        entries.append({"symbol": symbol, "claim_ref": ref, "outcome": "ATOMIC_WINNER"})
    return {"schema": "SKY_SELECTED_QUOTE_ATOMIC_CLAIM_V1",
            "symbols": symbols, "claims": entries, "slot": slot, "head_sha": sha,
            "claims_verified": len(entries) == len(symbols),
            "no_paid_api": True, "no_orders": True,
            "research_only": True, "production_eligible": False}


def verify_selected_receipt(payload: dict, *, raw: str, sha: str, slot: int) -> None:
    """Consumer job must read the exact claim job's artifact before paid calls."""
    symbols = validate_symbols(raw)
    if not isinstance(payload, dict) or payload.get("schema") != "SKY_SELECTED_QUOTE_ATOMIC_CLAIM_V1":
        raise RuntimeError("INVALID_SELECTED_ATOMIC_RECEIPT_SCHEMA")
    if payload.get("head_sha") != sha or payload.get("slot") != slot:
        raise RuntimeError("STALE_SELECTED_ATOMIC_RECEIPT")
    if payload.get("symbols") != symbols or payload.get("claims_verified") is not True:
        raise RuntimeError("SELECTED_ATOMIC_RECEIPT_MISMATCH")
    rows = payload.get("claims")
    if not isinstance(rows, list) or len(rows) != len(symbols):
        raise RuntimeError("SELECTED_ATOMIC_CLAIM_COUNT_MISMATCH")
    for symbol, row in zip(symbols, rows):
        expected = claim_ref(canonical_fugle_request("GET", "/intraday/quote/" + symbol), slot)
        if row != {"symbol": symbol, "claim_ref": expected, "outcome": "ATOMIC_WINNER"}:
            raise RuntimeError("INVALID_SELECTED_ATOMIC_CLAIM")


def verify_remote_claims(payload: dict, *, git=subprocess.run) -> None:
    """Read-only remote-ref readback: a JSON receipt alone is not proof."""
    rows = payload.get("claims") if isinstance(payload, dict) else None
    sha = payload.get("head_sha") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows or not isinstance(sha, str):
        raise RuntimeError("INVALID_REMOTE_ATOMIC_RECEIPT")
    refs = [row["claim_ref"] for row in rows]
    result = git(["git", "ls-remote", "--refs", "origin", *refs],
                 capture_output=True, text=True, check=True, timeout=30)
    actual = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) != 2 or fields[1] in actual:
            raise RuntimeError("MALFORMED_REMOTE_ATOMIC_REF")
        actual[fields[1]] = fields[0]
    if actual != {ref: sha for ref in refs}:
        raise RuntimeError("REMOTE_ATOMIC_CLAIM_READBACK_MISMATCH")


def main() -> None:
    import sys
    raw = os.environ.get("SKY_SELECTED_SYMBOLS", "")
    sha = os.environ.get("GITHUB_SHA", "")
    slot = int(datetime.now(timezone.utc).timestamp()) // 300
    output = Path("output/fugle_api_guard/selected_quote_atomic.json")
    if "--verify" in sys.argv[1:]:
        receipt = json.loads(output.read_text(encoding="utf-8"))
        verify_selected_receipt(receipt, raw=raw, sha=sha, slot=slot)
        verify_remote_claims(receipt)
        print("SELECTED_QUOTE_ATOMIC_RECEIPT_VERIFIED")
        return
    create = github_create_ref(os.environ.get("GITHUB_REPOSITORY", ""),
                               os.environ.get("GH_TOKEN", ""))
    receipt = claim_selected_quotes(raw, sha=sha, slot=slot, create_ref=create)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("SELECTED_QUOTE_ATOMIC_REFS_PASS", len(receipt["claims"]))


if __name__ == "__main__":
    main()
