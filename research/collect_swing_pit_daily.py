from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
SCHEMA_VERSION = "SWING_PIT_DAILY_OHLCV_1.1"
SOURCE_NAME = "FinMind TaiwanStockPrice + corporate-action reference datasets"
ADJUSTMENT_METHOD = "SKY_BACKWARD_REFERENCE_RATIO_V1"
DEFAULT_START = "2023-01-01"

EVENT_DATASETS = (
    "TaiwanStockDividendResult",
    "TaiwanStockCapitalReductionReferencePrice",
    "TaiwanStockSplitPrice",
    "TaiwanStockParValueChange",
)

class ProviderQuotaError(RuntimeError):
    pass

def _contains(interval: dict, day: str) -> bool:
    start = str(interval.get("listed_from") or "")
    end = interval.get("listed_to")
    return bool(start and start <= day and (not end or day <= str(end)))

def _to_float(v):
    if v in (None, "", "--"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None

def _to_int(v):
    if v in (None, "", "--"):
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None

def _get_dataset(dataset: str, symbol: str, start: str, end: str, token: str, retries: int = 3):
    params = {"dataset": dataset, "data_id": symbol, "start_date": start, "end_date": end}
    headers = {"User-Agent": "Sky-W3-Swing-PIT/1.1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                FINMIND_URL,
                params=params,
                timeout=45,
                headers=headers,
            )
            if r.status_code in (402, 429):
                raise ProviderQuotaError(f"{dataset}:RATE_OR_QUOTA_{r.status_code}:{r.text[:160]}")
            if 400 <= r.status_code < 500:
                raise RuntimeError(f"{dataset}:CLIENT_{r.status_code}:{r.text[:160]}")
            r.raise_for_status()
            payload = r.json()
            status = payload.get("status")
            if status not in (200, "200", None):
                msg = payload.get("msg") or payload.get("message")
                raise RuntimeError(f"{dataset}:FINMIND_STATUS_{status}:{msg}")
            data = payload.get("data")
            if not isinstance(data, list):
                raise RuntimeError(f"{dataset}:INVALID_DATA_PAYLOAD")
            return data
        except ProviderQuotaError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError(f"FETCH_FAILED:{dataset}:{symbol}:{type(last_error).__name__}:{last_error}")

def _symbol_intervals(pit: dict) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for interval in pit.get("intervals") or []:
        symbol = str(interval.get("symbol") or "")
        if symbol:
            out[symbol].append(interval)
    for symbol in out:
        out[symbol] = sorted(
            out[symbol],
            key=lambda x: (
                str(x.get("listed_from") or ""),
                str(x.get("listed_to") or "9999-12-31"),
                str(x.get("exchange") or ""),
            ),
        )
    return dict(out)

def _interval_for_day(intervals: list[dict], day: str):
    return [x for x in intervals if _contains(x, day)]

def _event_ratio(dataset: str, row: dict):
    if dataset == "TaiwanStockDividendResult":
        before = _to_float(row.get("before_price"))
        after = _to_float(row.get("reference_price"))
        if after is None:
            after = _to_float(row.get("after_price"))
    elif dataset == "TaiwanStockCapitalReductionReferencePrice":
        before = _to_float(row.get("ClosingPriceonTheLastTradingDay"))
        after = _to_float(row.get("PostReductionReferencePrice"))
        if after is None:
            after = _to_float(row.get("OpeningReferencePrice"))
    elif dataset == "TaiwanStockSplitPrice":
        before = _to_float(row.get("before_price"))
        after = _to_float(row.get("after_price"))
    elif dataset == "TaiwanStockParValueChange":
        before = _to_float(row.get("before_close"))
        after = _to_float(row.get("after_ref_close"))
    else:
        return None
    if before is None or after is None or before <= 0 or after <= 0:
        return None
    ratio = after / before
    return ratio if ratio > 0 else None

def _build_adjustment_events(symbol: str, events_by_dataset: dict[str, list[dict]]):
    by_date = defaultdict(list)
    invalid = []
    for dataset, rows in events_by_dataset.items():
        for row in rows or []:
            day = str(row.get("date") or "")
            if not day:
                continue
            ratio = _event_ratio(dataset, row)
            if ratio is None:
                invalid.append({
                    "symbol": symbol,
                    "date": day,
                    "dataset": dataset,
                    "reason": "MISSING_OR_INVALID_REFERENCE_RATIO",
                })
                continue
            by_date[day].append({"dataset": dataset, "ratio": ratio})
    conflicts = []
    events = []
    for day, items in sorted(by_date.items()):
        if len(items) > 1:
            conflicts.append({
                "symbol": symbol,
                "date": day,
                "datasets": [x["dataset"] for x in items],
                "reason": "MULTIPLE_CORPORATE_ACTION_DATASETS_SAME_DATE_FAIL_CLOSED",
            })
            continue
        events.append({"date": day, "dataset": items[0]["dataset"], "ratio": items[0]["ratio"]})
    return events, conflicts, invalid

def _adjustment_factor(day: str, events: list[dict]) -> float:
    factor = 1.0
    for event in events:
        if day < event["date"]:
            factor *= float(event["ratio"])
    return factor

def _adjust_price(value, factor):
    return round(float(value) * float(factor), 8)

def collect(*, pit_path: str, out_dir: str, start: str, end: str, shard_index: int, shard_count: int, token: str = ""):
    pit = json.loads(Path(pit_path).read_text(encoding="utf-8"))
    if not pit.get("historical_universe_gate_pass"):
        raise SystemExit("canonical PIT gate is not PASS")
    if not (pit.get("interval_validation") or {}).get("valid"):
        raise SystemExit("canonical PIT interval validation is not PASS")

    by_symbol = _symbol_intervals(pit)
    symbols = sorted(by_symbol)
    selected = [s for i, s in enumerate(symbols) if i % shard_count == shard_index]
    out = Path(out_dir)
    history_dir = out / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE_NAME,
        "adjusted": True,
        "volume_adjusted": False,
        "adjustment_method": ADJUSTMENT_METHOD,
        "retrieved_at": retrieved_at,
        "start": start,
        "end": end,
        "shard_index": shard_index,
        "shard_count": shard_count,
        "canonical_pit_symbols_total": len(symbols),
        "symbols_selected": len(selected),
        "symbols_written": 0,
        "symbols_empty": [],
        "symbols_failed": [],
        "continuity_conflicts": [],
        "corporate_action_conflicts": [],
        "corporate_action_invalid": [],
        "outside_pit_rows_dropped": 0,
        "zero_or_invalid_price_rows_dropped": 0,
        "rows_written": 0,
        "requests_expected_max": len(selected) * (1 + len(EVENT_DATASETS)),
    }

    for n, symbol in enumerate(selected, 1):
        intervals = by_symbol[symbol]
        try:
            raw = _get_dataset("TaiwanStockPrice", symbol, start, end, token)
            events_by_dataset = {ds: _get_dataset(ds, symbol, start, end, token) for ds in EVENT_DATASETS}
            events, ca_conflicts, ca_invalid = _build_adjustment_events(symbol, events_by_dataset)
            if ca_conflicts:
                report["corporate_action_conflicts"].extend(ca_conflicts)
                report["symbols_failed"].append({"symbol": symbol, "error": "CORPORATE_ACTION_CONFLICT_FAIL_CLOSED"})
                continue
            report["corporate_action_invalid"].extend(ca_invalid)
            bars = []
            for row in raw:
                day = str(row.get("date") or "")
                if not day or day < start or day > end:
                    continue
                matches = _interval_for_day(intervals, day)
                if not matches:
                    report["outside_pit_rows_dropped"] += 1
                    continue
                if len(matches) != 1:
                    report["continuity_conflicts"].append({"symbol": symbol, "date": day, "matches": matches})
                    continue
                interval = matches[0]
                o = _to_float(row.get("open"))
                h = _to_float(row.get("max"))
                l = _to_float(row.get("min"))
                c = _to_float(row.get("close"))
                volume = _to_int(row.get("Trading_Volume"))
                turnover = _to_int(row.get("Trading_money"))
                if None in (o, h, l, c, volume) or min(o, h, l, c) <= 0 or volume < 0:
                    report["zero_or_invalid_price_rows_dropped"] += 1
                    continue
                if h < max(o, l, c) or l > min(o, h, c):
                    report["zero_or_invalid_price_rows_dropped"] += 1
                    continue
                factor = _adjustment_factor(day, events)
                bars.append({
                    "symbol": symbol,
                    "exchange": str(interval.get("exchange") or ""),
                    "date": day,
                    "trading_date": day,
                    "open": _adjust_price(o, factor),
                    "high": _adjust_price(h, factor),
                    "low": _adjust_price(l, factor),
                    "close": _adjust_price(c, factor),
                    "raw_open": o,
                    "raw_high": h,
                    "raw_low": l,
                    "raw_close": c,
                    "volume": volume,
                    "turnover": turnover,
                    "source": SOURCE_NAME,
                    "source_as_of": retrieved_at,
                    "retrieved_at": retrieved_at,
                    "adjusted": True,
                    "volume_adjusted": False,
                    "adjustment_factor": factor,
                    "adjustment_method": ADJUSTMENT_METHOD,
                    "listed_from": interval.get("listed_from"),
                    "listed_to": interval.get("listed_to"),
                })
            bars.sort(key=lambda x: x["date"])
            if not bars:
                report["symbols_empty"].append(symbol)
                continue
            payload = {
                "schema_version": SCHEMA_VERSION,
                "symbol": symbol,
                "source": SOURCE_NAME,
                "retrieved_at": retrieved_at,
                "adjusted": True,
                "volume_adjusted": False,
                "adjustment_method": ADJUSTMENT_METHOD,
                "corporate_action_events": events,
                "data": bars,
            }
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            payload["sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
            (history_dir / f"{symbol}_D.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            report["symbols_written"] += 1
            report["rows_written"] += len(bars)
        except ProviderQuotaError as exc:
            report["symbols_failed"].append({"symbol": symbol, "error": f"{type(exc).__name__}:{exc}"})
            report["provider_blocker"] = {"type": "RATE_OR_QUOTA", "symbol": symbol, "error": str(exc)}
            report_path = out / f"shard_report_{shard_index:02d}.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SystemExit(4)
        except Exception as exc:
            report["symbols_failed"].append({"symbol": symbol, "error": f"{type(exc).__name__}:{exc}"})
        if n % 10 == 0:
            print(json.dumps({
                "shard": shard_index,
                "progress": f"{n}/{len(selected)}",
                "written": report["symbols_written"],
                "failed": len(report["symbols_failed"]),
            }, ensure_ascii=False), flush=True)

    report_path = out / f"shard_report_{shard_index:02d}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if report["continuity_conflicts"]:
        raise SystemExit(3)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pit-json", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", required=True)
    ap.add_argument("--shard-index", type=int, required=True)
    ap.add_argument("--shard-count", type=int, required=True)
    args = ap.parse_args()
    if not (0 <= args.shard_index < args.shard_count):
        raise SystemExit("invalid shard index/count")
    collect(
        pit_path=args.pit_json,
        out_dir=args.out,
        start=args.start,
        end=args.end,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        token=os.getenv("FINMIND_TOKEN", "").strip(),
    )

if __name__ == "__main__":
    main()
