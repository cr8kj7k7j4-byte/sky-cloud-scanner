import requests
from .config import FUGLE_API_KEY

BASE = "https://api.fugle.tw/marketdata/v1.0/stock"

def _headers():
    if not FUGLE_API_KEY:
        raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY": FUGLE_API_KEY, "User-Agent": "SkyCloudScanner/0.4"}

def _get(path, params=None):
    url = f"{BASE}{path}"
    r = requests.get(url, params=params, headers=_headers(), timeout=20)
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
