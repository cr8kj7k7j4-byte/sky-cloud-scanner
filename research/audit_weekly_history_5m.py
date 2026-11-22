"""Fail-closed historical 5-minute data audit. Research only; never generates signals."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

TPE = timezone(timedelta(hours=8))
FIELDS = ("open", "high", "low", "close", "volume")
START = date(2026, 11, 16)
END = date(2026, 11, 20)


def audit_candles(candles, *, start=START, end=END):
    """Return data-quality evidence; a successful fetch is not a backtest."""
    if not isinstance(candles, list):
        return {"status": "INVALID", "errors": ["INVALID_CANDLES_TYPE"], "daily": {}}
    errors, seen, by_day = [], set(), {}
    for index, candle in enumerate(candles):
        if not isinstance(candle, dict):
            errors.append(f"ROW_{index}_NOT_OBJECT")
            continue
        raw = candle.get("date")
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None or dt.utcoffset() is None:
                raise ValueError("missing offset")
            local = dt.astimezone(TPE)
        except (AttributeError, TypeError, ValueError):
            errors.append(f"ROW_{index}_INVALID_TIMESTAMP")
            continue
        if dt.astimezone(timezone.utc).isoformat() in seen:
            errors.append(f"ROW_{index}_DUPLICATE_TIMESTAMP")
        seen.add(dt.astimezone(timezone.utc).isoformat())
        if not (start <= local.date() <= end):
            errors.append(f"ROW_{index}_OUTSIDE_REQUESTED_PERIOD")
        if local.weekday() >= 5 or not (time(9, 0) <= local.time() <= time(13, 35)):
            errors.append(f"ROW_{index}_OUTSIDE_SESSION")
        if local.minute % 5 != 0 or local.second != 0 or local.microsecond != 0:
            errors.append(f"ROW_{index}_MISALIGNED_5M")
        values = {}
        for field in FIELDS:
            try:
                val = candle[field]
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
                    raise ValueError("nonfinite")
                if val < 0 or (field != "volume" and val == 0):
                    raise ValueError("nonpositive")
                values[field] = val
            except (KeyError, ValueError, TypeError):
                errors.append(f"ROW_{index}_INVALID_{field.upper()}")
        if all(field in values for field in FIELDS):
            if values["high"] < max(values["open"], values["close"], values["low"]):
                errors.append(f"ROW_{index}_INVALID_HIGH")
            if values["low"] > min(values["open"], values["close"], values["high"]):
                errors.append(f"ROW_{index}_INVALID_LOW")
        d = local.date().isoformat()
        by_day[d] = by_day.get(d, 0) + 1
    days = [(start + timedelta(days=i)).isoformat()
            for i in range((end - start).days + 1)
            if (start + timedelta(days=i)).weekday() < 5]
    return {
        "status": "INVALID" if errors else "EMPTY" if not candles else "STRUCTURE_PASS_NOT_PIT_VERIFIED",
        "count": len(candles),
        "daily": {d: by_day.get(d, 0) for d in days},
        "errors": errors[:50],
        "error_total": len(errors),
        "point_in_time_verified": False,
        "historical_signal_verified": False,
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
