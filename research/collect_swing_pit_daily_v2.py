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
SCHEMA_VERSION = "SWING_PIT_DAILY_OHLCV_2.1"
SOURCE = "FinMind TaiwanStockPrice + corporate-action reference datasets"
START_DEFAULT = "2023-01-01"


def _num(v):
    if v in (None, "", "--", "---"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _integer(v):
    x = _num(v)
    return None if x is None else int(x)


def _get(dataset: str, *, symbol: str | None, start: str, end: str, token: str = "", retries: int = 4):
    params = {"dataset": dataset, "start_date": start, "end_date": end}
    if symbol is not None:
        params["data_id"] = symbol
    headers = {"User-Agent": "Sky-W3-Swing-PIT/2.1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last = None
    for attempt in range(retries):
        try:
            r = requests.get(FINMIND_URL, params=params, headers=headers, timeout=45)
            if 400 <= r.status_code < 500 and r.status_code != 429:
                raise RuntimeError(f"HTTP_{r.status_code}:{r.text[:250]}")
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else min(5 * (2 ** attempt), 60)
                time.sleep(wait)
                continue
            r.raise_for_status()
            payload = r.json()
            status = payload.get("status")
            if status not in (None, 200, "200"):
                raise RuntimeError(f"FINMIND_STATUS_{status}:{payload.get('msg') or payload.get('detail')}")
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise RuntimeError("FINMIND_INVALID_PAYLOAD")
            return rows
        except Exception as exc:
            last = exc
            if "HTTP_4" in str(exc) and "HTTP_429" not in str(exc):
                break
            if attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"{dataset}:{symbol or 'ALL'}:{type(last).__name__}:{last}")


def _contains(interval: dict, day: str) -> bool:
    a = str(interval.get("listed_from") or "")
    b = interval.get("listed_to")
    return bool(a and a <= day and (not b or day <= str(b)))


def _index_intervals(pit: dict) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for row in pit.get("intervals") or []:
        symbol = str(row.get("symbol") or "")
        if symbol:
            out[symbol].append(row)
    return {
        s: sorted(rows, key=lambda x: (str(x.get("listed_from") or ""), str(x.get("listed_to") or "9999-12-31")))
        for s, rows in out.items()
    }


def _interval_for_day(rows: list[dict], day: str):
    found = [x for x in rows if _contains(x, day)]
    return found[0] if len(found) == 1 else None


def _parse_raw(rows: list[dict]):
    out = []
    for r in rows:
        day = str(r.get("date") or "")
        o, h, l, c = (_num(r.get(k)) for k in ("open", "max", "min", "close"))
        volume = _integer(r.get("Trading_Volume"))
        turnover = _integer(r.get("Trading_money"))
        if not day or None in (o, h, l, c, volume):
            continue
        # FinMind documents zero OHLC when there is no announced transaction price.
        # Such rows are missing/no-trade observations, not bars and are not forward-filled.
        if min(o, h, l, c) <= 0 or volume < 0:
            continue
        if h < max(o, l, c) or l > min(o, h, c):
            continue
        out.append({
            "date": day,
            "open_raw": o,
            "high_raw": h,
            "low_raw": l,
            "close_raw": c,
            "volume": volume,
            "turnover": turnover,
        })
    return sorted(out, key=lambda x: x["date"])


def _factor(dataset: str, row: dict):
    if dataset == "TaiwanStockDividendResult":
        before = _num(row.get("before_price"))
        after = _num(row.get("reference_price")) or _num(row.get("after_price"))
    elif dataset == "TaiwanStockCapitalReductionReferencePrice":
        before = _num(row.get("ClosingPriceonTheLastTradingDay"))
        # For combined reduction + ex-right cases, ExrightReferencePrice is the
        # final trading reference when populated.
        after = _num(row.get("ExrightReferencePrice"))
        if not after or after <= 0:
            after = _num(row.get("PostReductionReferencePrice")) or _num(row.get("OpeningReferencePrice"))
    elif dataset == "TaiwanStockSplitPrice":
        before = _num(row.get("before_price"))
        after = _num(row.get("after_price")) or _num(row.get("open_price"))
    elif dataset == "TaiwanStockParValueChange":
        before = _num(row.get("before_close"))
        after = _num(row.get("after_ref_close")) or _num(row.get("after_ref_open"))
    else:
        return None
    if before and after and before > 0 and after > 0:
        ratio = after / before
        if 0.01 <= ratio <= 100:
            return ratio
    return None


def _global_rare_events(start: str, end: str, token: str):
    by_symbol = defaultdict(list)
    source_errors = []
    for ds in ("TaiwanStockSplitPrice", "TaiwanStockParValueChange"):
        try:
            rows = _get(ds, symbol=None, start=start, end=end, token=token)
        except Exception as exc:
            source_errors.append(f"{ds}:{exc}")
            continue
        for row in rows:
            symbol = str(row.get("stock_id") or "")
            day = str(row.get("date") or "")
            f = _factor(ds, row)
            if symbol and day and f:
                by_symbol[symbol].append({
                    "date": day, "factor": f, "source": ds, "row": row,
                })
    return dict(by_symbol), source_errors


def _symbol_events(symbol: str, start: str, end: str, token: str, rare_events: dict[str, list[dict]]):
    events = defaultdict(list)
    errors = []
    for ds in ("TaiwanStockDividendResult", "TaiwanStockCapitalReductionReferencePrice"):
        try:
            rows = _get(ds, symbol=symbol, start=start, end=end, token=token)
        except Exception as exc:
            errors.append(f"{ds}:{exc}")
            continue
        for row in rows:
            day = str(row.get("date") or "")
            f = _factor(ds, row)
            if day and f:
                events[day].append({"factor": f, "source": ds, "row": row})

    for e in rare_events.get(symbol, []):
        events[e["date"]].append(e)

    factors = {}
    conflicts = []
    for day, rows in sorted(events.items()):
        sources = {x["source"] for x in rows}
        # Structural actions supersede a plain dividend row on the same date.
        # Capital reduction explicitly exposes ExrightReferencePrice for combined cases.
        priority = [
            "TaiwanStockCapitalReductionReferencePrice",
            "TaiwanStockParValueChange",
            "TaiwanStockSplitPrice",
            "TaiwanStockDividendResult",
        ]
        chosen = None
        for ds in priority:
            candidates = [x for x in rows if x["source"] == ds]
            if candidates:
                chosen = candidates[0]
                break
        structural = sources & {
            "TaiwanStockCapitalReductionReferencePrice",
            "TaiwanStockParValueChange",
            "TaiwanStockSplitPrice",
        }
        if len(structural) > 1:
            conflicts.append({"date": day, "sources": sorted(sources), "reason": "MULTIPLE_STRUCTURAL_ACTIONS"})
            continue
        if chosen:
            factors[day] = {
                "factor": chosen["factor"],
                "source": chosen["source"],
                "sources_on_date": sorted(sources),
            }
    return factors, conflicts, errors


def _adjust(raw: list[dict], factors: dict[str, dict]):
    event_days = sorted(factors)
    out = []
    for row in raw:
        scale = 1.0
        for day in event_days:
            if day > row["date"]:
                scale *= factors[day]["factor"]
        out.append({
            **row,
            "open": row["open_raw"] * scale,
            "high": row["high_raw"] * scale,
            "low": row["low_raw"] * scale,
            "close": row["close_raw"] * scale,
            "price_adjustment_factor": scale,
        })
    return out


def collect(*, pit_path: str, out_dir: str, start: str, end: str, shard_index: int, shard_count: int, token: str = ""):
    pit = json.loads(Path(pit_path).read_text(encoding="utf-8"))
    if not pit.get("historical_universe_gate_pass"):
        raise SystemExit("canonical PIT gate is not PASS")
    if not (pit.get("interval_validation") or {}).get("valid"):
        raise SystemExit("canonical PIT interval validation is not PASS")

    intervals = _index_intervals(pit)
    symbols = sorted(intervals)
    selected = [s for i, s in enumerate(symbols) if i % shard_count == shard_index]

    rare_events, rare_errors = _global_rare_events(start, end, token)
    # These datasets are the only governed source for split/par-value adjustment.
    # If either global dataset is structurally unavailable, fail the shard closed.
    if rare_errors:
        raise SystemExit("rare corporate-action source unavailable: " + " | ".join(rare_errors))

    out = Path(out_dir)
    hist = out / "history"
    hist.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(timezone.utc).isoformat()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "retrieved_at": retrieved,
        "adjusted": True,
        "volume_adjusted": False,
        "shard_index": shard_index,
        "shard_count": shard_count,
        "canonical_pit_symbols_total": len(symbols),
        "symbols_selected": len(selected),
        "symbols_written": 0,
        "symbols_empty": [],
        "symbols_failed": [],
        "symbols_quarantined": [],
        "rows_written": 0,
        "outside_pit_rows_dropped": 0,
    }

    for n, symbol in enumerate(selected, 1):
        try:
            raw = _parse_raw(_get("TaiwanStockPrice", symbol=symbol, start=start, end=end, token=token))
            if not raw:
                report["symbols_empty"].append(symbol)
                continue

            factors, conflicts, event_errors = _symbol_events(symbol, start, end, token, rare_events)
            # Dividend/capital-reduction endpoints are Free per-symbol and are required
            # for a governed adjusted series. A source error is not silently ignored.
            if event_errors or conflicts:
                report["symbols_quarantined"].append({
                    "symbol": symbol,
                    "conflicts": conflicts,
                    "event_request_errors": event_errors,
                })
                continue

            adjusted = _adjust(raw, factors)
            bars = []
            for row in adjusted:
                interval = _interval_for_day(intervals[symbol], row["date"])
                if interval is None:
                    report["outside_pit_rows_dropped"] += 1
                    continue
                bars.append({
                    "symbol": symbol,
                    "exchange": interval.get("exchange"),
                    "date": row["date"],
                    "trading_date": row["date"],
                    "open": round(row["open"], 8),
                    "high": round(row["high"], 8),
                    "low": round(row["low"], 8),
                    "close": round(row["close"], 8),
                    "volume": row["volume"],
                    "turnover": row["turnover"],
                    "source": SOURCE,
                    "source_as_of": retrieved,
                    "retrieved_at": retrieved,
                    "adjusted": True,
                    "volume_adjusted": False,
                    "adjustment_method": "governed_corporate_action_reference_backward_v2",
                    "price_adjustment_factor": round(row["price_adjustment_factor"], 12),
                    "listed_from": interval.get("listed_from"),
                    "listed_to": interval.get("listed_to"),
                })
            if not bars:
                report["symbols_empty"].append(symbol)
                continue

            payload = {
                "schema_version": SCHEMA_VERSION,
                "symbol": symbol,
                "source": SOURCE,
                "retrieved_at": retrieved,
                "adjusted": True,
                "volume_adjusted": False,
                "adjustment_method": "governed_corporate_action_reference_backward_v2",
                "corporate_action_events": factors,
                "data": bars,
            }
            canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            payload["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            (hist / f"{symbol}_D.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            report["symbols_written"] += 1
            report["rows_written"] += len(bars)
        except Exception as exc:
            report["symbols_failed"].append({"symbol": symbol, "error": f"{type(exc).__name__}:{exc}"})

        if n % 10 == 0:
            print(json.dumps({
                "shard": shard_index,
                "progress": f"{n}/{len(selected)}",
                "written": report["symbols_written"],
                "quarantined": len(report["symbols_quarantined"]),
                "failed": len(report["symbols_failed"]),
            }, ensure_ascii=False), flush=True)

    (out / f"shard_report_{shard_index:02d}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k not in {"symbols_failed", "symbols_quarantined"}}, ensure_ascii=False))
    if selected and report["symbols_written"] == 0 and report["symbols_failed"]:
        raise SystemExit(4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pit-json", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", default=START_DEFAULT)
    ap.add_argument("--end", required=True)
    ap.add_argument("--shard-index", type=int, required=True)
    ap.add_argument("--shard-count", type=int, required=True)
    args = ap.parse_args()
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
