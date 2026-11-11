import os
from datetime import datetime, timezone
import requests
from .config import FUGLE_API_KEY

BASE = "https://api.fugle.tw/marketdata/v1.0/stock"

def _headers():
    if not FUGLE_API_KEY:
        raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY": FUGLE_API_KEY, "User-Agent": "SkyCloudScanner/0.4"}

def _atomic_research_paid_gate(path, params):
    """Optional research gate at the actual provider HTTP boundary.

    Never enable this as a Production entitlement by merely setting env vars;
    owner review of token scope, tag lifetime, and provider capacity is required.
    """
    if os.getenv("SKY_PAID_ATOMIC_ENFORCE") != "1":
        return
    from research.sky_fugle_request_identity import canonical_fugle_request
    from research.sky_fugle_atomic_ref_claim import (
        claim_ref, github_create_ref, try_claim,
    )
    scope = canonical_fugle_request("GET", BASE + path, parameters=params)
    slot = int(datetime.now(timezone.utc).timestamp()) // 300
    ref = claim_ref(scope, slot)
    token = os.getenv("GH_TOKEN", "")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    sha = os.getenv("GITHUB_SHA", "")
    allowed = try_claim(ref, sha, github_create_ref(repo, token))
    if not allowed:
        raise RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")


def _get(path, params=None):
    url = f"{BASE}{path}"
    headers = _headers()
    _atomic_research_paid_gate(path, params)
    r = requests.get(url, params=params, headers=headers, timeout=20)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        if r.status_code == 403:
            raise PermissionError(
                f"Fugle endpoint not available under current API plan: {path}"
            ) from e
        raise
    return r.json()

def get_tickers(market):
    return _get("/intraday/tickers", {"type": "EQUITY", "market": market})

def get_ticker(symbol):
    return _get(f"/intraday/ticker/{symbol}")

def get_quote(symbol):
    return _get(f"/intraday/quote/{symbol}")

def get_candles(symbol, timeframe="5"):
    return _get(
        f"/intraday/candles/{symbol}",
        {"timeframe": timeframe, "sort": "asc"},
    )

def snapshot_quotes(market):
    # Optional capability only. Snapshot is plan-dependent and must never be
    # required for the scanner to complete.
    return _get(f"/snapshot/quotes/{market}", {"type": "COMMONSTOCK"})
