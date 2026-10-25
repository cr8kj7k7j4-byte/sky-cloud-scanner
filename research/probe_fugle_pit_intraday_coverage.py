from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import requests

BASE = "https://api.fugle.tw/marketdata/v1.0/stock"
UA = "Sky-W3A-PIT-Coverage-Probe/1.0"


def headers():
    key = os.getenv("FUGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing FUGLE_API_KEY")
    return {"X-API-KEY": key, "User-Agent": UA}


def active_on(interval, d: date) -> bool:
    start = date.fromisoformat(str(interval["listed_from"])[:10])
    end_raw = interval.get("listed_to")
    end = date.fromisoformat(str(end_raw)[:10]) if end_raw else None
    return start <= d and (end is None or d <= end)


def select_probe(intervals, as_of: date, per_exchange: int, historical_closed_n: int):
    by_exchange = defaultdict(list)
    closed = []

    for x in intervals:
        symbol = str(x.get("symbol") or "").strip()
        exchange = str(x.get("exchange") or "").upper().strip()
        if not symbol or exchange not in {"TWSE", "TPEx", "TPEX"}:
            continue
        if active_on(x, as_of):
            by_exchange["TPEx" if exchange == "TPEX" else exchange].append(x)
        elif x.get("listed_to"):
            closed.append(x)

    selected = []
    for exch in ("TWSE", "TPEx"):
        uniq = {}
        for x in by_exchange[exch]:
            uniq[str(x["symbol"])] = x
        for symbol in sorted(uniq)[:per_exchange]:
            selected.append({**uniq[symbol], "probe_type": "ACTIVE", "probe_as_of": as_of.isoformat()})

    uniq_closed = {}
    for x in closed:
        uniq_closed[(str(x.get("exchange")), str(x["symbol"]))] = x
    closed_sorted = sorted(
        uniq_closed.values(),
        key=lambda x: (str(x.get("listed_to") or ""), str(x["symbol"])),
        reverse=True,
    )
    for x in closed_sorted[:historical_closed_n]:
        selected.append({**x, "probe_type": "HISTORICAL_CLOSED", "probe_as_of": as_of.isoformat()})
    return selected


def request_one(symbol: str, start: str, end: str):
    r = requests.get(
        f"{BASE}/historical/candles/{symbol}",
        params={
            "from": start,
            "to": end,
            "timeframe": "5",
            "fields": "open,high,low,close,volume,average",
            "sort": "asc",
        },
        headers=headers(),
        timeout=30,
    )
    if r.status_code == 404:
        return {"status": "NO_DATA_404", "bars": 0}
    if r.status_code == 403:
        return {"status": "PLAN_RESTRICTED_403", "bars": 0}
    if r.status_code == 429:
        return {"status": "RATE_LIMIT_429", "bars": 0}
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    return {
        "status": "OK" if rows else "EMPTY",
        "bars": len(rows),
        "first_bar": rows[0].get("date") if rows else None,
        "last_bar": rows[-1].get("date") if rows else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pit-snapshot", required=True)
    ap.add_argument("--as-of", default="2026-09-30")
    ap.add_argument("--from-date", default="2026-09-01")
    ap.add_argument("--to-date", default="2026-09-30")
    ap.add_argument("--per-exchange", type=int, default=20)
    ap.add_argument("--historical-closed-n", type=int, default=10)
    ap.add_argument("--out", default="research_output_pit/fugle_pit_coverage_probe.json")
    args = ap.parse_args()

    payload = json.loads(Path(args.pit_snapshot).read_text(encoding="utf-8"))
    intervals = payload.get("intervals", [])
    selected = select_probe(
        intervals,
        date.fromisoformat(args.as_of),
        args.per_exchange,
        args.historical_closed_n,
    )

    rows = []
    for i, item in enumerate(selected, 1):
        symbol = str(item["symbol"])
        try:
            result = request_one(symbol, args.from_date, args.to_date)
        except Exception as e:
            result = {"status": f"ERROR_{type(e).__name__}", "bars": 0, "error": str(e)}
        rows.append({
            "symbol": symbol,
            "exchange": item.get("exchange"),
            "listed_from": item.get("listed_from"),
            "listed_to": item.get("listed_to"),
            "probe_type": item.get("probe_type"),
            **result,
        })
        print(f"[{i}/{len(selected)}] {symbol}: {result['status']} bars={result.get('bars',0)}")
        time.sleep(1.1)

    ok = [x for x in rows if x["status"] == "OK"]
    active = [x for x in rows if x["probe_type"] == "ACTIVE"]
    active_ok = [x for x in active if x["status"] == "OK"]
    closed = [x for x in rows if x["probe_type"] == "HISTORICAL_CLOSED"]
    closed_ok = [x for x in closed if x["status"] == "OK"]

    report = {
        "probe_contract": "W3A_FUGLE_PIT_COVERAGE_PROBE_V1",
        "as_of": args.as_of,
        "date_range": [args.from_date, args.to_date],
        "sample_n": len(rows),
        "active_sample_n": len(active),
        "active_ok_n": len(active_ok),
        "active_ok_share": round(len(active_ok) / len(active), 6) if active else 0.0,
        "historical_closed_sample_n": len(closed),
        "historical_closed_ok_n": len(closed_ok),
        "historical_closed_ok_share": round(len(closed_ok) / len(closed), 6) if closed else 0.0,
        "overall_ok_share": round(len(ok) / len(rows), 6) if rows else 0.0,
        "status_counts": {
            s: sum(1 for x in rows if x["status"] == s)
            for s in sorted({x["status"] for x in rows})
        },
        "rows": rows,
        "governance_note": (
            "This is a feasibility probe only. It does not establish >=95% PIT coverage "
            "and does not authorize preregistration or Production changes."
        ),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
