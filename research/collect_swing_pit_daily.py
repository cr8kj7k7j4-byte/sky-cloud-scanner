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
SCHEMA_VERSION = "SWING_PIT_DAILY_OHLCV_1.0"

class ProviderQuotaError(RuntimeError):
    pass
SOURCE_NAME = "FinMind TaiwanStockPriceAdj"
DEFAULT_START = "2023-01-01"


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


def _request_symbol(symbol: str, start: str, end: str, token: str, retries: int = 5):
    params = {
        "dataset": "TaiwanStockPriceAdj",
        "data_id": symbol,
        "start_date": start,
        "end_date": end,
    }
    if token:
        params["token"] = token

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                FINMIND_URL,
                params=params,
                timeout=45,
                headers={"User-Agent": "Sky-W3-Swing-PIT/1.0"},
            )
            if r.status_code in (402, 429):
                raise ProviderQuotaError(f"RATE_OR_QUOTA_{r.status_code}:{r.text[:200]}")
            r.raise_for_status()
            payload = r.json()
            status = payload.get("status")
            if status not in (200, "200", None):
                raise RuntimeError(
                    f"FINMIND_STATUS_{status}:{payload.get('msg') or payload.get('message')}"
                )
            data = payload.get("data")
            if not isinstance(data, list):
                raise RuntimeError("FINMIND_INVALID_DATA_PAYLOAD")
            return data
        except ProviderQuotaError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(min(2 ** (attempt - 1), 15))
    raise RuntimeError(f"FETCH_FAILED:{symbol}:{type(last_error).__name__}:{last_error}")


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
    matches = [x for x in intervals if _contains(x, day)]
    return matches


def collect(
    *,
    pit_path: str,
    out_dir: str,
    start: str,
    end: str,
    shard_index: int,
    shard_count: int,
    token: str = "",
):
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
        "adjustment_method": "FinMind TaiwanStockPriceAdj corporate-action-adjusted series",
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
        "outside_pit_rows_dropped": 0,
        "rows_written": 0,
    }

    for n, symbol in enumerate(selected, 1):
        intervals = by_symbol[symbol]
        try:
            raw = _request_symbol(symbol, start, end, token)
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
                    report["continuity_conflicts"].append({
                        "symbol": symbol,
                        "date": day,
                        "matches": matches,
                    })
                    continue
                interval = matches[0]
                o = _to_float(row.get("open"))
                h = _to_float(row.get("max"))
                l = _to_float(row.get("min"))
                c = _to_float(row.get("close"))
                volume = _to_int(row.get("Trading_Volume"))
                turnover = _to_int(row.get("Trading_money"))
                if None in (o, h, l, c, volume):
                    continue
                if min(o, h, l, c) <= 0 or volume < 0:
                    continue
                if h < max(o, l, c) or l > min(o, h, c):
                    continue
                bars.append({
                    "symbol": symbol,
                    "exchange": str(interval.get("exchange") or ""),
                    "date": day,
                    "trading_date": day,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": volume,
                    "turnover": turnover,
                    "source": SOURCE_NAME,
                    "source_as_of": retrieved_at,
                    "retrieved_at": retrieved_at,
                    "adjusted": True,
                    "adjustment_method": "FinMind TaiwanStockPriceAdj",
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
                "adjustment_method": "FinMind TaiwanStockPriceAdj",
                "data": bars,
            }
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            payload["sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
            (history_dir / f"{symbol}_D.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
            report["symbols_written"] += 1
            report["rows_written"] += len(bars)
        except ProviderQuotaError as exc:
            report["symbols_failed"].append({
                "symbol": symbol,
                "error": f"{type(exc).__name__}:{exc}",
            })
            report["provider_blocker"] = {
                "type": "RATE_OR_QUOTA",
                "symbol": symbol,
                "error": str(exc),
            }
            report_path = out / f"shard_report_{shard_index:02d}.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SystemExit(4)
        except Exception as exc:
            report["symbols_failed"].append({
                "symbol": symbol,
                "error": f"{type(exc).__name__}:{exc}",
            })

        if n % 25 == 0:
            print(
                json.dumps(
                    {
                        "shard": shard_index,
                        "progress": f"{n}/{len(selected)}",
                        "written": report["symbols_written"],
                        "failed": len(report["symbols_failed"]),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    report_path = out / f"shard_report_{shard_index:02d}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))

    # Fail only on structural continuity conflicts. Missing symbols are audited later
    # and may be retried by the workflow without fabricating/forward-filling data.
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
