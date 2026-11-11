"""Research-only canonical quote claims with an isolated GitHub write job.

No Fugle access is performed. All symbols are validated before any claim.
If a claim is rejected, the downstream read-only paid Job must never start.
"""
from __future__ import annotations

import json
import os
import re
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
            "symbols": symbols, "claims": entries, "slot": slot,
            "claims_verified": len(entries) == len(symbols),
            "no_paid_api": True, "no_orders": True,
            "research_only": True, "production_eligible": False}


def main() -> None:
    raw = os.environ.get("SKY_SELECTED_SYMBOLS", "")
    sha = os.environ.get("GITHUB_SHA", "")
    slot = int(datetime.now(timezone.utc).timestamp()) // 300
    create = github_create_ref(os.environ.get("GITHUB_REPOSITORY", ""),
                               os.environ.get("GH_TOKEN", ""))
    receipt = claim_selected_quotes(raw, sha=sha, slot=slot, create_ref=create)
    output = Path("output/fugle_api_guard/selected_quote_atomic.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("SELECTED_QUOTE_ATOMIC_REFS_PASS", len(receipt["claims"]))


if __name__ == "__main__":
    main()
