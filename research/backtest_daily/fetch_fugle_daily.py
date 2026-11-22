"""Fetch daily bars from the Fugle MarketData historical candles endpoint.

NOT EXECUTED in the authoring session. The endpoint, parameters and the
1-year range limit were taken from the official docs
(developer.fugle.tw/docs/data/http-api/historical/candles). Verify again
before the first real run.

Requirements:
- Environment variable FUGLE_API_KEY (store as a GitHub Secret or Secret Manager).
- Never print or log the key.

Usage:
    FUGLE_API_KEY=... python3 fetch_fugle_daily.py --symbols symbols.txt --out data/daily
"""

import argparse
import csv
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import json

BASE = "https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/{symbol}"

# Warm-up from 2024-09 so MA60 and the 20-day breakout window exist on 2025-01-01.
CHUNKS = [
    ("2024-09-01", "2024-12-31"),
    ("2025-01-01", "2025-12-31"),
    ("2026-01-01", "2026-10-22"),
]

MIN_INTERVAL_S = 1.1   # about 55 requests per minute, below the 60/min historical limit
MAX_RETRIES_429 = 3


def build_url(symbol: str, start: str, end: str) -> str:
    q = urllib.parse.urlencode({
        "from": start,
        "to": end,
        "timeframe": "D",
        "fields": "open,high,low,close,volume",
        "sort": "asc",
    })
    return f"{BASE.format(symbol=symbol)}?{q}"


def fetch_chunk(symbol: str, start: str, end: str, api_key: str) -> list[dict]:
    url = build_url(symbol, start, end)
    req = urllib.request.Request(url, headers={"X-API-KEY": api_key, "Accept": "application/json"})
    for attempt in range(MAX_RETRIES_429 + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload.get("data", [])
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES_429:
                time.sleep(60)
                continue
            raise RuntimeError(f"HTTP {e.code} for {symbol} {start}..{end}") from None
    return []


TICKERS_URL = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/tickers"


def parse_universe(payload: dict) -> list[str]:
    """Keep ordinary 4-digit common stocks. Excludes ETFs (00xx), warrants and odd lots."""
    out = []
    for item in payload.get("data", []):
        sym = str(item.get("symbol", ""))
        if item.get("type", "EQUITY") != "EQUITY":
            continue
        if len(sym) == 4 and sym.isdigit() and not sym.startswith("00"):
            out.append(sym)
    return sorted(set(out))


def list_universe(api_key: str) -> list[str]:
    """Normal (non-attention, non-disposition) listed and OTC common stocks."""
    symbols: list[str] = []
    for market in ("TSE", "OTC"):
        q = urllib.parse.urlencode({"type": "EQUITY", "market": market, "isNormal": "true"})
        req = urllib.request.Request(f"{TICKERS_URL}?{q}",
                                     headers={"X-API-KEY": api_key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        symbols.extend(parse_universe(payload))
        time.sleep(MIN_INTERVAL_S)
    return sorted(set(symbols))


def to_rows(data: list[dict]) -> list[dict]:
    rows = []
    for d in data:
        if d.get("open") is None or d.get("close") is None:
            continue   # skip suspended or incomplete days; never fabricate prices
        rows.append({"date": d["date"][:10], "open": d["open"], "high": d["high"],
                     "low": d["low"], "close": d["close"], "volume": d["volume"]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="", help="optional text file; default = full normal universe")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    api_key = os.environ.get("FUGLE_API_KEY")
    if not api_key:
        raise SystemExit("FUGLE_API_KEY is not set")

    os.makedirs(args.out, exist_ok=True)
    if args.symbols:
        with open(args.symbols, encoding="utf-8") as f:
            symbols = [s.strip() for s in f if s.strip()]
    else:
        symbols = list_universe(api_key)
        with open(os.path.join(args.out, "universe.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(symbols) + "\n")
    print(f"universe size: {len(symbols)}")

    for sym in symbols:
        seen = {}
        for start, end in CHUNKS:
            data = fetch_chunk(sym, start, end, api_key)
            for r in to_rows(data):
                seen[r["date"]] = r
            time.sleep(MIN_INTERVAL_S)
        path = os.path.join(args.out, f"{sym}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume"])
            w.writeheader()
            for d in sorted(seen):
                w.writerow(seen[d])
        print(f"{sym}: {len(seen)} rows")


if __name__ == "__main__":
    main()
