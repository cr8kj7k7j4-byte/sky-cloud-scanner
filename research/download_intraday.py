
from __future__ import annotations
import argparse, json, os, time
from datetime import date
from pathlib import Path
import requests

BASE = "https://api.fugle.tw/marketdata/v1.0/stock"
UA = "SkyCloudScanner-Research/0.5"
MIN_INTERVAL = 1.05  # <= 60 calls/min

def headers():
    key = os.getenv("FUGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY": key, "User-Agent": UA}

def get_hist(symbol: str, start: str, end: str, timeframe: str = "5"):
    url = f"{BASE}/historical/candles/{symbol}"
    params = {
        "from": start,
        "to": end,
        "timeframe": timeframe,
        "fields": "open,high,low,close,volume,average",
        "sort": "asc",
    }
    r = requests.get(url, params=params, headers=headers(), timeout=30)
    if r.status_code == 404:
        return []
    if r.status_code == 403:
        raise PermissionError(f"historical endpoint restricted for {symbol}")
    if r.status_code == 429:
        time.sleep(10)
        r = requests.get(url, params=params, headers=headers(), timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", required=True)
    ap.add_argument("--from-date", required=True)
    ap.add_argument("--to-date", required=True)
    ap.add_argument("--out", default="research_data")
    args = ap.parse_args()

    # API requires each date range to be < 1 year.
    d0 = date.fromisoformat(args.from_date)
    d1 = date.fromisoformat(args.to_date)
    if (d1 - d0).days >= 365:
        raise ValueError("Pilot date range must be < 1 year")

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    summary = []
    for i, symbol in enumerate(symbols, 1):
        t0 = time.time()
        try:
            data = get_hist(symbol, args.from_date, args.to_date, "5")
            obj = {
                "symbol": symbol,
                "timeframe": "5",
                "from": args.from_date,
                "to": args.to_date,
                "data": data,
            }
            p = out / f"{symbol}_5.json"
            p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            print(f"[{i}/{len(symbols)}] {symbol}: {len(data)} bars")
            summary.append({"symbol": symbol, "ok": True, "bars": len(data)})
        except Exception as e:
            print(f"[{i}/{len(symbols)}] {symbol}: ERROR {type(e).__name__}: {e}")
            summary.append({"symbol": symbol, "ok": False, "error": f"{type(e).__name__}: {e}"})

        elapsed = time.time() - t0
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

    (out/"_download_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

if __name__ == "__main__":
    main()
