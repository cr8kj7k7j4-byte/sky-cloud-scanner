from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

DQ_VERSION = "P0-DATA-DQ-1.0"

def _parse_ts(value):
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

def evaluate_rows(
    rows: Iterable[Dict[str, Any]],
    *,
    key_fields=("symbol", "timestamp"),
    required_fields=("symbol", "timestamp"),
    price_fields=("open", "high", "low", "close"),
    observed_at: Optional[str] = None,
    source: str = "unknown",
    freshness_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    items = list(rows or [])
    observed_dt = _parse_ts(observed_at) or datetime.now(timezone.utc)
    missing: List[Dict[str, Any]] = []
    duplicate_keys: List[Any] = []
    bad_ticks: List[Dict[str, Any]] = []
    future_rows: List[int] = []
    seen = set()
    latest_ts = None

    for i, row in enumerate(items):
        miss = [f for f in required_fields if row.get(f) in (None, "")]
        if miss:
            missing.append({"index": i, "fields": miss})

        key = tuple(row.get(f) for f in key_fields)
        if key in seen:
            duplicate_keys.append(key)
        else:
            seen.add(key)

        ts = _parse_ts(row.get("timestamp"))
        if ts:
            latest_ts = ts if latest_ts is None or ts > latest_ts else latest_ts
            if ts > observed_dt:
                future_rows.append(i)

        vals = {}
        for f in price_fields:
            if row.get(f) is not None:
                try:
                    vals[f] = float(row[f])
                except (TypeError, ValueError):
                    bad_ticks.append({"index": i, "reason": f"non_numeric:{f}"})
        if vals and any(v <= 0 for v in vals.values()):
            bad_ticks.append({"index": i, "reason": "nonpositive_price"})
        if {"open","high","low","close"} <= set(vals):
            if vals["high"] < max(vals["open"], vals["low"], vals["close"]):
                bad_ticks.append({"index": i, "reason": "high_inconsistent"})
            if vals["low"] > min(vals["open"], vals["high"], vals["close"]):
                bad_ticks.append({"index": i, "reason": "low_inconsistent"})
        if row.get("volume") is not None:
            try:
                if float(row["volume"]) < 0:
                    bad_ticks.append({"index": i, "reason": "negative_volume"})
            except (TypeError, ValueError):
                bad_ticks.append({"index": i, "reason": "non_numeric:volume"})

    age_seconds = None
    freshness_ok = None
    if latest_ts is not None:
        age_seconds = (observed_dt - latest_ts).total_seconds()
        if freshness_seconds is not None:
            freshness_ok = age_seconds <= float(freshness_seconds)

    errors = []
    if missing: errors.append("missing_data")
    if duplicate_keys: errors.append("duplicates")
    if bad_ticks: errors.append("bad_ticks")
    if future_rows: errors.append("timestamp_causality")
    if freshness_ok is False: errors.append("stale_source")

    return {
        "dq_version": DQ_VERSION,
        "source": source,
        "observed_at": observed_dt.isoformat(),
        "row_count": len(items),
        "missing_count": len(missing),
        "duplicate_count": len(duplicate_keys),
        "bad_tick_count": len(bad_ticks),
        "future_row_count": len(future_rows),
        "latest_source_timestamp": latest_ts.isoformat() if latest_ts else None,
        "source_age_seconds": age_seconds,
        "freshness_threshold_seconds": freshness_seconds,
        "freshness_ok": freshness_ok,
        "source_health": "HEALTHY" if not errors else "DEGRADED",
        "decision_eligible": not errors,
        "errors": errors,
        "details": {
            "missing": missing[:100],
            "duplicate_keys": [list(x) for x in duplicate_keys[:100]],
            "bad_ticks": bad_ticks[:100],
            "future_rows": future_rows[:100],
        },
        "lineage": {
            "source": source,
            "quality_evaluated_at": datetime.now(timezone.utc).isoformat(),
            "key_fields": list(key_fields),
            "required_fields": list(required_fields),
        },
    }
