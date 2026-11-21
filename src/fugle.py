import requests
import copy
import os
import threading
import time
from .config import FUGLE_API_KEY

BASE = "https://api.fugle.tw/marketdata/v1.0/stock"

# Per-process only: never use an unverified result from another Workflow.
_ATOMIC_CACHE = {}
_ATOMIC_CACHE_LOCK = threading.RLock()
_ATOMIC_CACHE_TTL_SECONDS = 300

def _headers():
    if not FUGLE_API_KEY:
        raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY": FUGLE_API_KEY, "User-Agent": "SkyCloudScanner/0.4"}

def _get(path, params=None):
    url = f"{BASE}{path}"
    headers = _headers()
    from research.sky_fugle_atomic_ref_claim import guard_fugle_request
    enforced = os.getenv("SKY_PAID_ATOMIC_ENFORCE") == "1"
    if enforced:
        from research.sky_fugle_request_identity import canonical_fugle_request
        identity = canonical_fugle_request("GET", url, parameters=params)
        # Serialize same-process requests. A cached response is reused only
        # after a successful provider response; never cache errors or denials.
        with _ATOMIC_CACHE_LOCK:
            cached = _ATOMIC_CACHE.get(identity)
            if cached is not None and time.monotonic() - cached[0] < _ATOMIC_CACHE_TTL_SECONDS:
                return copy.deepcopy(cached[1])
            guard_fugle_request(url, params)
            result = _fetch_json(url, params, headers, path)
            _ATOMIC_CACHE[identity] = (time.monotonic(), copy.deepcopy(result))
            return result
    guard_fugle_request(url, params)
    return _fetch_json(url, params, headers, path)


def _fetch_json(url, params, headers, path):
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
