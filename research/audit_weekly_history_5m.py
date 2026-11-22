"""Fail-closed historical 5-minute data audit. Research only; never generates signals."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

from research.historical_5m_quality import inspect_history

START = date(2026, 11, 16)
END = date(2026, 11, 20)


def audit_candles(candles, *, start=START, end=END):
    """Use the canonical 5m inspector; retain only weekly QA aggregation.

    Neither the inspector nor this adapter certifies market-day completeness,
    contemporaneous strategy signals, PIT origin or actual executions.
    """
    if not isinstance(candles, list):
        return {
            "status": "INVALID", "errors": ["INVALID_CANDLES_TYPE"],
            "error_total": 1, "daily": {},
            "point_in_time_verified": False,
            "historical_signal_verified": False,
        }
    canonical = inspect_history(candles, start=start.isoformat(), end=end.isoformat())
    days = [(start + timedelta(days=i)).isoformat()
            for i in range((end - start).days + 1)
            if (start + timedelta(days=i)).weekday() < 5]
    invalid_counts = canonical.get("invalid_counts", {})
    errors = [f"{reason}:{count}" for reason, count in sorted(invalid_counts.items())]
    return {
        "status": ("INVALID" if canonical.get("status") == "INVALID_DATA"
                   else "EMPTY" if canonical.get("status") == "EMPTY"
                   else "STRUCTURE_PASS_NOT_PIT_VERIFIED"),
        "count": len(candles),
        "daily": {day: canonical.get("session_counts", {}).get(day, 0) for day in days},
        "errors": errors[:50],
        "error_total": sum(invalid_counts.values()),
        "point_in_time_verified": False,
        "historical_signal_verified": False,
        "official_trading_calendar_reconciled": False,
    }


def build_report(history_dir: Path, manifest_path: Path, start=START, end=END):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sample = manifest.get("sample", [])
    symbols = [x.get("symbol") for x in sample]
    if not symbols or any(not isinstance(s, str) or not s.isdigit() for s in symbols) or len(symbols) != len(set(symbols)):
        raise ValueError("INVALID_UNIVERSE_MANIFEST")
    out = []
    for symbol in symbols:
        path = history_dir / f"{symbol}_5.json"
        if not path.exists():
            out.append({"symbol": symbol, "status": "MISSING_FILE"})
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("symbol") != symbol or payload.get("from") != start.isoformat() or payload.get("to") != end.isoformat():
                raise ValueError("IDENTITY_OR_RANGE_MISMATCH")
            result = audit_candles(payload.get("data"), start=start, end=end)
            result.update({"symbol": symbol, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            out.append(result)
        except (ValueError, TypeError, json.JSONDecodeError):
            out.append({"symbol": symbol, "status": "INVALID_FILE"})
    days = [(start + timedelta(days=i)).isoformat()
            for i in range((end - start).days + 1)
            if (start + timedelta(days=i)).weekday() < 5]
    daily_bars = {d: sum(item.get('daily', {}).get(d, 0) for item in out) for d in days}
    missing_days = [d for d, count in daily_bars.items() if count == 0]
    status_counts = {}
    for item in out:
        key = item["status"]
        status_counts[key] = status_counts.get(key, 0) + 1
    return {
        "schema": "SKY_WEEKLY_HISTORICAL_5M_QA_V1",
        "period": {"from": start.isoformat(), "to": end.isoformat(), "timezone": "Asia/Taipei"},
        "status": "STRUCTURE_PASS_NOT_STRATEGY_VERIFIED" if status_counts.get("STRUCTURE_PASS_NOT_PIT_VERIFIED") == len(out) and not missing_days else "INSUFFICIENT_DATA",
        "daily_bars": daily_bars,
        "missing_market_days": missing_days,
        "sample_size": len(out),
        "status_counts": status_counts,
        "sample_only": True,
        "historical_pit_universe_verified": False,
        "contemporaneous_model_signals_verified": False,
        "replay_or_backtest_executed": False,
        "production_eligible": False,
        "automatic_order": False,
        "symbols": out,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--history-dir", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--from-date", default=START.isoformat())
    p.add_argument("--to-date", default=END.isoformat())
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    start, end = date.fromisoformat(args.from_date), date.fromisoformat(args.to_date)
    if start > end:
        raise SystemExit("INVALID_DATE_RANGE")
    result = build_report(args.history_dir, args.manifest, start=start, end=end)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "status_counts": result["status_counts"]}))
    if result["status"] == "INSUFFICIENT_DATA":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
