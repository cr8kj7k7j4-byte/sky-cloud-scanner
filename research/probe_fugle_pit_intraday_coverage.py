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


def _spread_sample(rows, n):
    rows = list(rows)
    if n <= 0 or not rows:
        return []
    if len(rows) <= n:
        return rows
    if n == 1:
        return [rows[len(rows) // 2]]
    idx = [round(i * (len(rows) - 1) / (n - 1)) for i in range(n)]
    seen = set()
    out = []
    for i in idx:
        key = (str(rows[i].get("exchange")), str(rows[i].get("symbol")), str(rows[i].get("listed_from")))
        if key not in seen:
            seen.add(key)
            out.append(rows[i])
    return out


def select_probe(intervals, audit_dates, per_exchange: int, historical_closed_n: int):
    selected = []
    seen = set()

    for as_of in audit_dates:
        by_exchange = defaultdict(list)
        for x in intervals:
            symbol = str(x.get("symbol") or "").strip()
            exchange = str(x.get("exchange") or "").upper().strip()
            if not symbol or exchange not in {"TWSE", "TPEx", "TPEX"}:
                continue
            if active_on(x, as_of):
                exch = "TPEx" if exchange == "TPEX" else exchange
                by_exchange[exch].append(x)

        for exch in ("TWSE", "TPEx"):
            uniq = {}
            for x in by_exchange[exch]:
                uniq[str(x["symbol"])] = x
            population = [uniq[s] for s in sorted(uniq)]
            for x in _spread_sample(population, per_exchange):
                key = ("PIT_DATE", as_of.isoformat(), exch, str(x["symbol"]))
                if key in seen:
                    continue
                seen.add(key)
                selected.append({
                    **x,
                    "probe_type": "PIT_DATE",
                    "probe_as_of": as_of.isoformat(),
                    "probe_exchange": exch,
                })

    # Historical-closed feasibility is only meaningful inside Fugle's documented
    # minute-history window. Older closures are outside the supported research
    # horizon and must not be counted as provider failures.
    minute_start = date(2023, 5, 23)
    closed = []
    for x in intervals:
        symbol = str(x.get("symbol") or "").strip()
        exchange = str(x.get("exchange") or "").upper().strip()
        listed_to = x.get("listed_to")
        if not symbol or exchange not in {"TWSE", "TPEx", "TPEX"} or not listed_to:
            continue
        end_d = date.fromisoformat(str(listed_to)[:10])
        start_d = date.fromisoformat(str(x["listed_from"])[:10])
        if end_d >= minute_start and end_d >= start_d:
            closed.append(x)

    closed_sorted = sorted(
        closed,
        key=lambda x: (str(x.get("listed_to") or ""), str(x.get("exchange")), str(x["symbol"])),
    )
    for x in _spread_sample(closed_sorted, historical_closed_n):
        exch = "TPEx" if str(x.get("exchange")).upper() == "TPEX" else str(x.get("exchange"))
        key = ("HISTORICAL_CLOSED", exch, str(x["symbol"]), str(x.get("listed_to")))
        if key in seen:
            continue
        seen.add(key)
        selected.append({
            **x,
            "probe_type": "HISTORICAL_CLOSED",
            "probe_as_of": str(x.get("listed_to"))[:10],
            "probe_exchange": exch,
        })
    return selected


def request_one(symbol: str, start: str, end: str, *, max_retries: int = 6):
    url = f"{BASE}/historical/candles/{symbol}"
    params = {
        "from": start,
        "to": end,
        "timeframe": "5",
        "fields": "open,high,low,close,volume,average",
        "sort": "asc",
    }
    backoff = [5, 10, 20, 30, 45, 60]
    for attempt in range(max_retries + 1):
        r = requests.get(url, params=params, headers=headers(), timeout=30)
        if r.status_code == 404:
            return {"status": "NO_DATA_404", "bars": 0, "attempts": attempt + 1}
        if r.status_code == 403:
            return {"status": "PLAN_RESTRICTED_403", "bars": 0, "attempts": attempt + 1}
        if r.status_code == 429:
            if attempt >= max_retries:
                return {"status": "RATE_LIMIT_429_EXHAUSTED", "bars": 0, "attempts": attempt + 1}
            retry_after = r.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after is not None else backoff[attempt]
            except (TypeError, ValueError):
                wait = backoff[attempt]
            time.sleep(max(wait, backoff[attempt]))
            continue
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        return {
            "status": "OK" if rows else "EMPTY",
            "bars": len(rows),
            "attempts": attempt + 1,
            "first_bar": rows[0].get("date") if rows else None,
            "last_bar": rows[-1].get("date") if rows else None,
        }
    return {"status": "UNKNOWN", "bars": 0, "attempts": max_retries + 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pit-snapshot", required=True)
    ap.add_argument("--as-of", default="2026-09-30")
    ap.add_argument(
        "--audit-dates",
        default="2023-12-31,2024-12-31,2025-12-31,2026-09-30",
        help="Comma-separated PIT audit dates; each exchange is sampled on every date.",
    )
    ap.add_argument("--from-date", default="2026-09-01")
    ap.add_argument("--to-date", default="2026-09-30")
    ap.add_argument("--per-exchange", type=int, default=20)
    ap.add_argument("--historical-closed-n", type=int, default=10)
    ap.add_argument("--out", default="research_output_pit/fugle_pit_coverage_probe.json")
    args = ap.parse_args()

    payload = json.loads(Path(args.pit_snapshot).read_text(encoding="utf-8"))
    intervals = payload.get("intervals", [])
    audit_dates = [date.fromisoformat(x.strip()) for x in args.audit_dates.split(",") if x.strip()]
    selected = select_probe(
        intervals,
        audit_dates,
        args.per_exchange,
        args.historical_closed_n,
    )

    rows = []
    for i, item in enumerate(selected, 1):
        symbol = str(item["symbol"])
        # Probe each row inside the actual PIT membership interval.
        probe_as_of = date.fromisoformat(str(item.get("probe_as_of") or args.as_of)[:10])
        start_d = date.fromisoformat(str(item["listed_from"])[:10])
        end_raw = item.get("listed_to")
        end_d = date.fromisoformat(str(end_raw)[:10]) if end_raw else probe_as_of
        probe_end = min(probe_as_of, end_d)
        probe_start = max(start_d, date(2023, 5, 23), date.fromordinal(probe_end.toordinal() - 30))
        query_from, query_to = probe_start.isoformat(), probe_end.isoformat()

        try:
            result = request_one(symbol, query_from, query_to)
        except Exception as e:
            result = {"status": f"ERROR_{type(e).__name__}", "bars": 0, "error": str(e)}
        rows.append({
            "symbol": symbol,
            "exchange": item.get("exchange"),
            "listed_from": item.get("listed_from"),
            "listed_to": item.get("listed_to"),
            "probe_type": item.get("probe_type"),
            "probe_as_of": item.get("probe_as_of"),
            "probe_exchange": item.get("probe_exchange"),
            "query_from": query_from,
            "query_to": query_to,
            **result,
        })
        print(f"[{i}/{len(selected)}] {symbol}: {result['status']} bars={result.get('bars',0)}")
        time.sleep(2.2)

    ok = [x for x in rows if x["status"] == "OK"]
    pit_rows = [x for x in rows if x["probe_type"] == "PIT_DATE"]
    closed = [x for x in rows if x["probe_type"] == "HISTORICAL_CLOSED"]

    by_audit_date = {}
    for d in sorted({x.get("probe_as_of") for x in pit_rows if x.get("probe_as_of")}):
        subset = [x for x in pit_rows if x.get("probe_as_of") == d]
        by_exchange = {}
        for exch in ("TWSE", "TPEx"):
            ex = [x for x in subset if x.get("probe_exchange") == exch]
            ex_ok = [x for x in ex if x["status"] == "OK"]
            by_exchange[exch] = {
                "sample_n": len(ex),
                "ok_n": len(ex_ok),
                "ok_share": round(len(ex_ok) / len(ex), 6) if ex else None,
            }
        date_ok = [x for x in subset if x["status"] == "OK"]
        by_audit_date[d] = {
            "sample_n": len(subset),
            "ok_n": len(date_ok),
            "ok_share": round(len(date_ok) / len(subset), 6) if subset else None,
            "by_exchange": by_exchange,
        }

    closed_ok = [x for x in closed if x["status"] == "OK"]
    report = {
        "probe_contract": "W3A_FUGLE_PIT_COVERAGE_PROBE_V2",
        "audit_dates": [d.isoformat() for d in audit_dates],
        "provider_minute_history_start": "2023-05-23",
        "sample_n": len(rows),
        "pit_date_sample_n": len(pit_rows),
        "historical_closed_sample_n": len(closed),
        "historical_closed_ok_n": len(closed_ok),
        "historical_closed_ok_share": round(len(closed_ok) / len(closed), 6) if closed else None,
        "overall_ok_n": len(ok),
        "overall_ok_share": round(len(ok) / len(rows), 6) if rows else 0.0,
        "by_audit_date": by_audit_date,
        "status_counts": {
            s: sum(1 for x in rows if x["status"] == s)
            for s in sorted({x["status"] for x in rows})
        },
        "rows": rows,
        "governance_note": (
            "This is a stratified feasibility/stress probe only. It does not establish "
            "formal whole-universe >=95% PIT coverage and does not authorize preregistration "
            "or Production changes."
        ),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
