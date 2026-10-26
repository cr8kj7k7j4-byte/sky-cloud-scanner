from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path

from research.download_pit_universe_intraday import (
    MIN_INTERVAL,
    _request_chunk,
    chunks,
    load_pit_union,
)

TAIPEI = timezone(timedelta(hours=8))
DECISION_TIMES = [f"09:{m:02d}" for m in range(1, 16)]
KEEP_END = dtime(9, 14)


def parse_ts(value: str) -> datetime:
    s = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TAIPEI)
    return dt.astimezone(TAIPEI)


def num(v):
    try:
        return float(v)
    except Exception:
        return None


def compact_chunk(data: list[dict]) -> list[dict]:
    by_day = defaultdict(list)
    for raw in data:
        try:
            ts = parse_ts(raw.get("date"))
        except Exception:
            continue
        by_day[ts.date().isoformat()].append((ts, raw))

    days = []
    for day, items in sorted(by_day.items()):
        items.sort(key=lambda x: x[0])
        if not items:
            continue

        session_open = num(items[0][1].get("open"))
        session_close = num(items[-1][1].get("close"))
        if session_open is None or session_close is None:
            continue

        bars = {}
        for ts, b in items:
            if ts.time() <= KEEP_END:
                bars[ts.strftime("%H:%M")] = {
                    "open": num(b.get("open")),
                    "high": num(b.get("high")),
                    "low": num(b.get("low")),
                    "close": num(b.get("close")),
                    "volume": num(b.get("volume")) or 0.0,
                }

        outcomes = {}
        bm = {ts.strftime("%H:%M"): (ts, b) for ts, b in items}
        for hhmm in DECISION_TIMES:
            decision_dt = datetime.fromisoformat(f"{day}T{hhmm}:00").replace(tzinfo=TAIPEI)
            entry_dt = decision_dt
            entry_row = bm.get(entry_dt.strftime("%H:%M"))
            if entry_row is None:
                continue
            entry = num(entry_row[1].get("open"))
            if entry is None or entry <= 0:
                continue

            future = [(ts, b) for ts, b in items if ts >= entry_dt]
            if not future:
                continue

            row = {"entry": entry}
            for horizon in (30, 60):
                exit_dt = decision_dt + timedelta(minutes=horizon - 1)
                window = [(ts, b) for ts, b in future if ts <= exit_dt]
                exit_row = bm.get(exit_dt.strftime("%H:%M"))
                if exit_row is not None and window:
                    highs = [num(b.get("high")) for _, b in window]
                    lows = [num(b.get("low")) for _, b in window]
                    highs = [x for x in highs if x is not None]
                    lows = [x for x in lows if x is not None]
                    row[f"exit_{horizon}m"] = num(exit_row[1].get("close"))
                    row[f"high_{horizon}m"] = max(highs) if highs else None
                    row[f"low_{horizon}m"] = min(lows) if lows else None

            highs = [num(b.get("high")) for _, b in future]
            lows = [num(b.get("low")) for _, b in future]
            highs = [x for x in highs if x is not None]
            lows = [x for x in lows if x is not None]
            row["session_close"] = session_close
            row["high_to_close"] = max(highs) if highs else None
            row["low_to_close"] = min(lows) if lows else None
            outcomes[hhmm] = row

        days.append({
            "date": day,
            "session_open": session_open,
            "session_close": session_close,
            "bars": bars,
            "outcomes": outcomes,
        })
    return days


def download_symbol(item: dict, start: date, end: date, out_dir: Path) -> dict:
    symbol = item["symbol"]
    exchange = item["exchange"]
    all_days = {}
    raw_bars = 0

    for a, b in chunks(start, end):
        t0 = time.time()
        data = _request_chunk(symbol, a, b, timeframe="1")
        raw_bars += len(data)
        for d in compact_chunk(data):
            all_days[d["date"]] = d
        elapsed = time.time() - t0
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

    symbol_dir = out_dir / exchange
    symbol_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        **item,
        "schema_version": "OPENING_ACCELERATION_1M_COMPACT_V1_0",
        "timeframe": "1",
        "from": start.isoformat(),
        "to": end.isoformat(),
        "days": [all_days[k] for k in sorted(all_days)],
    }
    path = symbol_dir / f"{symbol}_opening_1m.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {
        "symbol": symbol,
        "exchange": exchange,
        "ok": True,
        "raw_bars": raw_bars,
        "days": len(all_days),
        "stored_opening_bars": sum(len(x["bars"]) for x in all_days.values()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pit-intervals", required=True)
    ap.add_argument("--from-date", required=True)
    ap.add_argument("--to-date", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard-count", type=int, default=1)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    start = date.fromisoformat(args.from_date)
    end = date.fromisoformat(args.to_date)
    items = load_pit_union(args.pit_intervals, args.from_date, args.to_date)
    items = [x for i, x in enumerate(items) if i % args.shard_count == args.shard_index]
    if args.limit > 0:
        items = items[:args.limit]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    for i, item in enumerate(items, 1):
        try:
            a = max(start, date.fromisoformat(item.get("history_required_from", start.isoformat())))
            b = min(end, date.fromisoformat(item.get("history_required_to", end.isoformat())))
            row = download_symbol(item, a, b, out)
            summary.append(row)
            print(f"[{i}/{len(items)}] {item['exchange']} {item['symbol']}: {row['days']} days / {row['raw_bars']} raw bars", flush=True)
        except Exception as exc:
            row = {
                "symbol": item.get("symbol"),
                "exchange": item.get("exchange"),
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            summary.append(row)
            print(f"[{i}/{len(items)}] ERROR {row}", flush=True)

    report = {
        "schema_version": "OPENING_ACCELERATION_1M_DOWNLOAD_SUMMARY_V1_0",
        "from_date": args.from_date,
        "to_date": args.to_date,
        "shard_count": args.shard_count,
        "shard_index": args.shard_index,
        "expected_symbols": len(items),
        "successful_symbols": sum(bool(x.get("ok")) for x in summary),
        "symbols_with_days": sum(bool(x.get("ok")) and int(x.get("days") or 0) > 0 for x in summary),
        "raw_bars": sum(int(x.get("raw_bars") or 0) for x in summary),
        "stored_opening_bars": sum(int(x.get("stored_opening_bars") or 0) for x in summary),
        "summary": summary,
    }
    (out / "download_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k:v for k,v in report.items() if k != "summary"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
