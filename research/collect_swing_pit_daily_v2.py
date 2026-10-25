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
SCHEMA_VERSION = "SWING_PIT_DAILY_OHLCV_2.0"
SOURCE = "FinMind TaiwanStockPrice + corporate-action reference datasets"
START_DEFAULT = "2023-01-01"
EVENT_DATASETS = (
    "TaiwanStockDividendResult",
    "TaiwanStockCapitalReductionReferencePrice",
)
RARE_EVENT_DATASETS = (
    "TaiwanStockSplitPrice",
    "TaiwanStockParValueChange",
)


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


def _request(dataset: str, symbol: str, start: str, end: str, token: str = "", retries: int = 4):
    params = {
        "dataset": dataset,
        "data_id": symbol,
        "start_date": start,
        "end_date": end,
    }
    headers = {"User-Agent": "Sky-W3-Swing-PIT/2.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last = None
    for attempt in range(retries):
        try:
            r = requests.get(FINMIND_URL, params=params, headers=headers, timeout=45)
            if 400 <= r.status_code < 500 and r.status_code != 429:
                raise RuntimeError(f"HTTP_{r.status_code}:{r.text[:200]}")
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
            data = payload.get("data")
            if not isinstance(data, list):
                raise RuntimeError("FINMIND_INVALID_PAYLOAD")
            return data
        except Exception as exc:
            last = exc
            if "HTTP_4" in str(exc) and "HTTP_429" not in str(exc):
                break
            if attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"{dataset}:{symbol}:{type(last).__name__}:{last}")


def _contains(interval: dict, day: str) -> bool:
    start = str(interval.get("listed_from") or "")
    end = interval.get("listed_to")
    return bool(start and start <= day and (not end or day <= str(end)))


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
        spread = _num(r.get("spread"))
        if not day or None in (o, h, l, c, volume):
            continue
        if min(o, h, l, c) <= 0 or volume < 0:
            continue
        if h < max(o, l, c) or l > min(o, h, c):
            continue
        out.append({
            "date": day, "open_raw": o, "high_raw": h, "low_raw": l, "close_raw": c,
            "volume": volume, "turnover": turnover, "spread": spread,
        })
    out.sort(key=lambda x: x["date"])
    return out


def _candidate_event_dates(raw: list[dict], tolerance_pct: float = 0.0005):
    dates = {}
    prev = None
    for row in raw:
        if prev is not None and row["spread"] is not None:
            implied_ref = row["close_raw"] - row["spread"]
            prev_close = prev["close_raw"]
            if prev_close > 0:
                delta = abs(implied_ref / prev_close - 1.0)
                if delta > tolerance_pct:
                    dates[row["date"]] = {
                        "implied_reference": implied_ref,
                        "previous_available_close": prev_close,
                        "reference_ratio": implied_ref / prev_close,
                        "delta_pct": delta * 100,
                    }
        prev = row
    return dates


def _event_dates(dataset: str, rows: list[dict]):
    return {str(r.get("date") or "") for r in rows if r.get("date")}


def _event_fallback_factor(dataset: str, row: dict):
    if dataset == "TaiwanStockDividendResult":
        before = _num(row.get("before_price"))
        after = _num(row.get("reference_price")) or _num(row.get("after_price"))
    elif dataset == "TaiwanStockCapitalReductionReferencePrice":
        before = _num(row.get("ClosingPriceonTheLastTradingDay"))
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
        return after / before
    return None


def _build_events(symbol: str, raw: list[dict], start: str, end: str, token: str):
    candidates = _candidate_event_dates(raw)
    datasets = {}
    known = set()
    request_errors = []

    for ds in EVENT_DATASETS:
        try:
            rows = _request(ds, symbol, start, end, token)
            datasets[ds] = rows
            known |= _event_dates(ds, rows)
        except Exception as exc:
            request_errors.append(f"{ds}:{exc}")
            datasets[ds] = []

    unresolved = set(candidates) - known
    if unresolved:
        for ds in RARE_EVENT_DATASETS:
            try:
                rows = _request(ds, symbol, start, end, token)
                datasets[ds] = rows
                known |= _event_dates(ds, rows)
            except Exception as exc:
                request_errors.append(f"{ds}:{exc}")
                datasets[ds] = []

    event_rows = defaultdict(list)
    for ds, rows in datasets.items():
        for r in rows:
            day = str(r.get("date") or "")
            if day:
                event_rows[day].append((ds, r))

    factors = {}
    unresolved_details = []
    for day, cand in sorted(candidates.items()):
        if day not in known:
            unresolved_details.append({"date": day, **cand, "reason": "UNRESOLVED_REFERENCE_DISCONTINUITY"})
            continue
        ratio = cand["reference_ratio"]
        if not (0.05 <= ratio <= 20):
            # fallback to published event reference if the raw-derived ratio is implausible
            ratio = None
            for ds, row in event_rows.get(day, []):
                ratio = _event_fallback_factor(ds, row)
                if ratio:
                    break
        if not ratio or not (0.05 <= ratio <= 20):
            unresolved_details.append({"date": day, **cand, "reason": "INVALID_ADJUSTMENT_FACTOR"})
            continue
        factors[day] = {
            "factor": ratio,
            "sources": sorted({ds for ds, _ in event_rows.get(day, [])}),
            "implied_reference": cand["implied_reference"],
            "previous_available_close": cand["previous_available_close"],
        }

    return factors, unresolved_details, request_errors


def _adjust(raw: list[dict], factors: dict[str, dict]):
    cumulative = 1.0
    factor_by_date = {d: x["factor"] for d, x in factors.items()}
    adjusted = []
    # Walk backward: an event affects all bars strictly before its event date.
    for row in reversed(raw):
        day = row["date"]
        scale = cumulative
        adjusted.append({
            **row,
            "open": row["open_raw"] * scale,
            "high": row["high_raw"] * scale,
            "low": row["low_raw"] * scale,
            "close": row["close_raw"] * scale,
            "price_adjustment_factor": scale,
        })
        if day in factor_by_date:
            cumulative *= factor_by_date[day]
    adjusted.reverse()
    return adjusted


def collect(*, pit_path: str, out_dir: str, start: str, end: str, shard_index: int, shard_count: int, token: str = ""):
    pit = json.loads(Path(pit_path).read_text(encoding="utf-8"))
    if not pit.get("historical_universe_gate_pass"):
        raise SystemExit("canonical PIT gate is not PASS")
    if not (pit.get("interval_validation") or {}).get("valid"):
        raise SystemExit("canonical PIT interval validation is not PASS")

    intervals = _index_intervals(pit)
    symbols = sorted(intervals)
    selected = [s for i, s in enumerate(symbols) if i % shard_count == shard_index]
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
            raw = _parse_raw(_request("TaiwanStockPrice", symbol, start, end, token))
            if not raw:
                report["symbols_empty"].append(symbol)
                continue
            factors, unresolved, event_errors = _build_events(symbol, raw, start, end, token)
            if unresolved:
                report["symbols_quarantined"].append({
                    "symbol": symbol,
                    "unresolved": unresolved,
                    "event_request_errors": event_errors,
                })
                continue
            adjusted = _adjust(raw, factors)
            bars = []
            continuity_conflict = False
            for row in adjusted:
                day = row["date"]
                interval = _interval_for_day(intervals[symbol], day)
                if interval is None:
                    report["outside_pit_rows_dropped"] += 1
                    continue
                bars.append({
                    "symbol": symbol,
                    "exchange": interval.get("exchange"),
                    "date": day,
                    "trading_date": day,
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
                    "adjustment_method": "confirmed_event_reference_ratio_backward_v1",
                    "price_adjustment_factor": round(row["price_adjustment_factor"], 12),
                    "listed_from": interval.get("listed_from"),
                    "listed_to": interval.get("listed_to"),
                })
            if continuity_conflict or not bars:
                report["symbols_empty"].append(symbol)
                continue
            payload = {
                "schema_version": SCHEMA_VERSION,
                "symbol": symbol,
                "source": SOURCE,
                "retrieved_at": retrieved,
                "adjusted": True,
                "volume_adjusted": False,
                "adjustment_method": "confirmed_event_reference_ratio_backward_v1",
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
                "shard": shard_index, "progress": f"{n}/{len(selected)}",
                "written": report["symbols_written"],
                "quarantined": len(report["symbols_quarantined"]),
                "failed": len(report["symbols_failed"]),
            }, ensure_ascii=False), flush=True)

    (out / f"shard_report_{shard_index:02d}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k not in {"symbols_failed","symbols_quarantined"}}, ensure_ascii=False))
    # Fail closed when the source is structurally unavailable for the shard.
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
