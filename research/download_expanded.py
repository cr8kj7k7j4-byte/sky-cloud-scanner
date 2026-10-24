
from __future__ import annotations
import argparse, json, os, time
from datetime import date, timedelta
from pathlib import Path
import requests

BASE = "https://api.fugle.tw/marketdata/v1.0/stock"
UA = "SkyCloudScanner-ExpandedResearch/0.5"
MIN_INTERVAL = 1.25
MAX_429_RETRIES = 5
BACKOFF_SECONDS = (5, 10, 20, 40, 60)

def headers():
    key = os.getenv("FUGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY": key, "User-Agent": UA}

def chunks(start: date, end: date, max_days=330):
    cur = start
    while cur <= end:
        nxt = min(end, cur + timedelta(days=max_days))
        yield cur, nxt
        cur = nxt + timedelta(days=1)

def _request_chunk(symbol, a, b, *, request_get=requests.get, sleep_fn=time.sleep):
    url = f"{BASE}/historical/candles/{symbol}"
    params = {
        "from": a.isoformat(),
        "to": b.isoformat(),
        "timeframe": "5",
        "fields": "open,high,low,close,volume,average",
        "sort": "asc",
    }

    for attempt in range(MAX_429_RETRIES + 1):
        r = request_get(url, params=params, headers=headers(), timeout=30)

        # A 404 for an older historical chunk can mean the symbol was not yet
        # listed / no bars exist for that interval. It should not invalidate
        # the entire symbol export; continue with later chunks.
        if r.status_code == 404:
            return []

        if r.status_code == 403:
            raise PermissionError(f"historical endpoint restricted for {symbol}")

        if r.status_code == 429:
            if attempt >= MAX_429_RETRIES:
                r.raise_for_status()
            retry_after = r.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after is not None else BACKOFF_SECONDS[attempt]
            except (TypeError, ValueError):
                wait = BACKOFF_SECONDS[attempt]
            wait = max(wait, BACKOFF_SECONDS[attempt])
            sleep_fn(wait)
            continue

        r.raise_for_status()
        payload = r.json()
        return payload.get("data", []) if isinstance(payload, dict) else []

    return []


def get_hist(symbol, start, end, *, request_get=requests.get, sleep_fn=time.sleep):
    all_data = []
    for a, b in chunks(start, end):
        t0 = time.time()
        data = _request_chunk(
            symbol, a, b,
            request_get=request_get,
            sleep_fn=sleep_fn,
        )
        all_data.extend(data)
        elapsed = time.time() - t0
        if elapsed < MIN_INTERVAL:
            sleep_fn(MIN_INTERVAL - elapsed)
    return all_data

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="research_data/universe_manifest.json")
    ap.add_argument("--from-date", required=True)
    ap.add_argument("--to-date", required=True)
    ap.add_argument("--out", default="research_data/history")
    args = ap.parse_args()
    start, end = date.fromisoformat(args.from_date), date.fromisoformat(args.to_date)
    sample = json.loads(Path(args.manifest).read_text(encoding="utf-8"))["sample"]
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    summary = []
    for i, item in enumerate(sample, 1):
        s = item["symbol"]
        try:
            data = get_hist(s, start, end)
            obj = {**item, "timeframe":"5", "from":args.from_date, "to":args.to_date, "data":data}
            (out/f"{s}_5.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            summary.append({"symbol":s,"ok":True,"bars":len(data)})
            print(f"[{i}/{len(sample)}] {s}: {len(data)} bars")
        except Exception as e:
            summary.append({"symbol":s,"ok":False,"error":f"{type(e).__name__}: {e}"})
            print(f"[{i}/{len(sample)}] {s}: ERROR {type(e).__name__}: {e}")
    (Path(args.manifest).parent/"download_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

if __name__ == "__main__":
    main()
