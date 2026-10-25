from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import requests

BASE = "https://api.fugle.tw/marketdata/v1.0/stock"
UA = "SkyCloudScanner-PITUniverse/1.0"
MIN_INTERVAL = 1.10
MAX_429_RETRIES = 5
BACKOFF_SECONDS = (5, 10, 20, 40, 60)


def headers():
    key = os.getenv("FUGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY": key, "User-Agent": UA}


def chunks(start: date, end: date, max_days: int = 330):
    cur = start
    while cur <= end:
        nxt = min(end, cur + timedelta(days=max_days))
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def load_pit_union(interval_json: str, from_date: str, to_date: str) -> list[dict]:
    payload = json.loads(Path(interval_json).read_text(encoding="utf-8"))
    intervals = payload.get("intervals") if isinstance(payload, dict) else payload
    if not isinstance(intervals, list):
        raise ValueError("PIT interval payload missing intervals")

    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    out = {}
    for row in intervals:
        symbol = str(row.get("symbol") or "")
        exchange = str(row.get("exchange") or "")
        if not symbol or exchange not in {"TWSE", "TPEx"}:
            continue
        a = date.fromisoformat(str(row.get("listed_from"))[:10])
        b_raw = row.get("listed_to")
        b = date.fromisoformat(str(b_raw)[:10]) if b_raw else date.max
        if a <= end and b >= start:
            out[(exchange, symbol)] = {
                "symbol": symbol,
                "exchange": exchange,
                "listed_from": row.get("listed_from"),
                "listed_to": row.get("listed_to"),
            }
    return [out[k] for k in sorted(out)]


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
            sleep_fn(max(wait, BACKOFF_SECONDS[attempt]))
            continue
        r.raise_for_status()
        payload = r.json()
        return payload.get("data", []) if isinstance(payload, dict) else []
    return []


def download_symbol(
    item: dict,
    start: date,
    end: date,
    out_dir: Path,
    *,
    request_get=requests.get,
    sleep_fn=time.sleep,
) -> dict:
    symbol = item["symbol"]
    symbol_dir = out_dir / item["exchange"] / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)

    chunk_reports = []
    total_bars = 0
    for a, b in chunks(start, end):
        path = symbol_dir / f"{a.isoformat()}_{b.isoformat()}_5m.json"
        if path.exists():
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
                n = len(obj.get("data", []))
                total_bars += n
                chunk_reports.append({"from": a.isoformat(), "to": b.isoformat(), "bars": n, "cached": True})
                continue
            except Exception:
                pass

        t0 = time.time()
        data = _request_chunk(symbol, a, b, request_get=request_get, sleep_fn=sleep_fn)
        path.write_text(
            json.dumps(
                {
                    **item,
                    "timeframe": "5",
                    "from": a.isoformat(),
                    "to": b.isoformat(),
                    "data": data,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        n = len(data)
        total_bars += n
        chunk_reports.append({"from": a.isoformat(), "to": b.isoformat(), "bars": n, "cached": False})
        elapsed = time.time() - t0
        if elapsed < MIN_INTERVAL:
            sleep_fn(MIN_INTERVAL - elapsed)

    return {
        "symbol": symbol,
        "exchange": item["exchange"],
        "ok": True,
        "bars": total_bars,
        "chunks": chunk_reports,
    }


def build_manifest(items: Iterable[dict], from_date: str, to_date: str) -> dict:
    arr = list(items)
    return {
        "schema_version": "1.0.0",
        "universe_method": "PIT_INTERVAL_UNION",
        "from_date": from_date,
        "to_date": to_date,
        "symbol_count": len(arr),
        "twse_count": sum(x["exchange"] == "TWSE" for x in arr),
        "tpex_count": sum(x["exchange"] == "TPEx" for x in arr),
        "symbols": arr,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pit-intervals", required=True)
    ap.add_argument("--from-date", required=True)
    ap.add_argument("--to-date", required=True)
    ap.add_argument("--out", default="research_data/pit_history")
    ap.add_argument("--limit", type=int, default=0, help="Diagnostic limit only; 0 = all")
    ap.add_argument("--shard-count", type=int, default=1)
    ap.add_argument("--shard-index", type=int, default=0)
    args = ap.parse_args()

    start = date.fromisoformat(args.from_date)
    end = date.fromisoformat(args.to_date)
    if end < start:
        raise ValueError("to-date must be >= from-date")

    items = load_pit_union(args.pit_intervals, args.from_date, args.to_date)
    if args.shard_count < 1:
        raise ValueError("shard-count must be >= 1")
    if not (0 <= args.shard_index < args.shard_count):
        raise ValueError("shard-index must be in [0, shard-count)")
    items = [
        item for idx, item in enumerate(items)
        if idx % args.shard_count == args.shard_index
    ]
    if args.limit > 0:
        items = items[: args.limit]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(items, args.from_date, args.to_date)
    (out / "pit_universe_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = []
    for i, item in enumerate(items, 1):
        try:
            row = download_symbol(item, start, end, out)
            print(f"[{i}/{len(items)}] {item['exchange']} {item['symbol']}: {row['bars']} bars")
            summary.append(row)
        except Exception as e:
            print(f"[{i}/{len(items)}] {item['exchange']} {item['symbol']}: ERROR {type(e).__name__}: {e}")
            summary.append({
                "symbol": item["symbol"],
                "exchange": item["exchange"],
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
            })

    successful = [x for x in summary if x.get("ok")]
    report = {
        "schema_version": "1.0.0",
        "expected_symbols": len(items),
        "successful_symbols": len(successful),
        "failed_symbols": len(items) - len(successful),
        "total_5m_bars": sum(int(x.get("bars") or 0) for x in successful),
        "coverage_pct": round((len(successful) / len(items) * 100.0), 4) if items else 0.0,
        "promotion_gate_95pct": bool(items) and len(successful) / len(items) >= 0.95,
        "summary": summary,
    }
    (out / "download_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "summary"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
