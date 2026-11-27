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

# Monthly plans are billed by subscription, not per successful HTTP call.
# Maintain a conservative per-process pacing lane; the existing GitHub
# concurrency group serializes participating paid workflows across runs.
_MONTHLY_RATE_LOCK = threading.RLock()
_MONTHLY_LAST_REQUEST = {}
_MONTHLY_MIN_INTERVAL_SECONDS = {
    "intraday": 0.12,    # <= 500/min, below Fugle developer 600/min
    "snapshot": 0.12,    # <= 500/min, below Fugle developer 600/min
    "historical": 1.10,  # <= 55/min, below Fugle developer 60/min
    "technical": 1.10,
    "ownership": 1.10,
    "corporate-actions": 2.10,
}

def _monthly_pace(path):
    family = path.lstrip("/").split("/", 1)[0]
    if family not in _MONTHLY_MIN_INTERVAL_SECONDS:
        raise RuntimeError("UNSUPPORTED_MONTHLY_FUGLE_ENDPOINT")
    with _MONTHLY_RATE_LOCK:
        last = _MONTHLY_LAST_REQUEST.get(family)
        now = time.monotonic()
        interval = _MONTHLY_MIN_INTERVAL_SECONDS[family]
        if last is not None and now - last < interval:
            time.sleep(interval - (now - last))
        # Count attempts, including provider HTTP errors; never retry 429 here.
        _MONTHLY_LAST_REQUEST[family] = time.monotonic()


def _headers():
    if not FUGLE_API_KEY:
        raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY": FUGLE_API_KEY, "User-Agent": "SkyCloudScanner/0.4"}

def _get(path, params=None, *, session=None):
    url = f"{BASE}{path}"
    headers = _headers()
    from research.sky_fugle_atomic_ref_claim import guard_fugle_request
    enforced = os.getenv("SKY_PAID_ATOMIC_ENFORCE") == "1"
    monthly = os.getenv("SKY_FUGLE_MONTHLY_RATE_CONTROL") == "1"
    if monthly:
        if enforced:
            raise RuntimeError("CONFLICTING_FUGLE_BILLING_GUARDS")
        from research.sky_fugle_request_identity import canonical_fugle_request
        canonical_fugle_request("GET", url, parameters=params)
        _monthly_pace(path)
        if session is not None:
            return _fetch_json(url, params, headers, path, session=session)
        return _fetch_json(url, params, headers, path)
    if enforced:
        from research.sky_fugle_request_identity import canonical_fugle_request
        identity = canonical_fugle_request("GET", url, parameters=params)
        # Match the atomic GitHub-ref five-minute UTC slot exactly.
        slot = int(time.time()) // 300
        # Serialize same-process requests. A cached response is reused only
        # after a successful provider response; never cache errors or denials.
        with _ATOMIC_CACHE_LOCK:
            cached = _ATOMIC_CACHE.get(identity)
            if (cached is not None and cached[2] == slot
                    and time.monotonic() - cached[0] < _ATOMIC_CACHE_TTL_SECONDS):
                return copy.deepcopy(cached[1])
            guard_fugle_request(url, params)
            result = _fetch_json(url, params, headers, path)
            _ATOMIC_CACHE[identity] = (time.monotonic(), copy.deepcopy(result), slot)
            return result
    guard_fugle_request(url, params)
    return _fetch_json(url, params, headers, path)


def _fetch_json(url, params, headers, path, *, session=None):
    transport = requests if session is None else session
    r = transport.get(url, params=params, headers=headers, timeout=20)
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

def get_quote(symbol, *, session=None):
    path = f"/intraday/quote/{symbol}"
    if session is not None:
        return _get(path, session=session)
    return _get(path)

def get_candles(symbol, timeframe="5"):
    return _get(
        f"/intraday/candles/{symbol}",
        {"timeframe": timeframe, "sort": "asc"},
    )

def get_historical_candles_5m(symbol, trade_date):
    """Exactly one explicitly approved previous-session Fugle 5m history call.

    This wrapper does not authorize calls by itself. The caller MUST verify
    provider entitlement first; W0 conservatively defaults it off.
    """
    from datetime import date
    import re
    if not isinstance(symbol, str) or not re.fullmatch(r"[0-9]{4,6}", symbol):
        raise ValueError("INVALID_HISTORICAL_SYMBOL")
    if not isinstance(trade_date, str):
        raise ValueError("INVALID_HISTORICAL_DATE")
    try:
        day = date.fromisoformat(trade_date)
    except ValueError as exc:
        raise ValueError("INVALID_HISTORICAL_DATE") from exc
    if day.isoformat() != trade_date or day.weekday() >= 5:
        raise ValueError("INVALID_HISTORICAL_DATE")
    return _get(
        f"/historical/candles/{symbol}",
        {"from": trade_date, "to": trade_date,
         "timeframe": "5", "sort": "asc",
         "fields": "open,high,low,close,volume,average"},
    )


def get_trades(symbol, *, offset=0, limit=500):
    # Official intraday trades: bounded page request, no retries on 429.
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("INVALID_TRADES_PAGINATION")
    return _get(f"/intraday/trades/{symbol}", {"offset": offset, "limit": limit})

def snapshot_quotes(market):
    # Optional capability only. Snapshot is plan-dependent and must never be
    # required for the scanner to complete.
    return _get(f"/snapshot/quotes/{market}", {"type": "COMMONSTOCK"})
