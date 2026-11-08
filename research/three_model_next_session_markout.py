"""Research-only next-session close-to-close evidence, never fills or profit.

Read private immutable historical observations, find first strictly later
Fugle D candle, store an immutable outcome linked by ledger_record_id.
A next-session markout is NOT an executable strategy, short borrow eligibility,
execution cost, or a realized P&L.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import re

from research.three_model_fugle_pipeline import TPE, read_fugle

OBS_PREFIX = "three-model-research/v1/"
OUTCOME_PREFIX = "three-model-followup/v1/"
MAX_SCAN = 500
MODEL_IDS = frozenset(("bidirectional_intraday", "next_day", "swing_3_20d"))
DIRECTIONS = frozenset(("LONG_WATCH", "SHORT_WATCH", "NO_TRADE"))


def canonical_json(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def validate_observation(record):
    if not isinstance(record, dict) or record.get("model_id") not in MODEL_IDS:
        raise ValueError("unsupported_model_record")
    if any(record.get(k) is not False for k in
           ("production_signal", "order_authorized", "eligible_strategy_trade",
            "trained_model_used")):
        raise ValueError("unsafe_record_claim")
    symbol = record.get("symbol")
    if not isinstance(symbol, str) or not re.fullmatch(r"\d{4,5}", symbol):
        raise ValueError("invalid_symbol")
    rid = record.get("ledger_record_id")
    if not isinstance(rid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{8,90}", rid):
        raise ValueError("invalid_record_id")
    if record.get("direction") not in DIRECTIONS:
        raise ValueError("invalid_direction")
    stamp = record.get("bar_time")
    reference = record.get("reference_close")
    if stamp is None or reference is None:
        return None
    if not isinstance(stamp, str):
        raise ValueError("invalid_bar_time")
    observed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if observed.utcoffset() is None:
        raise ValueError("bar_time_without_timezone")
    observed = observed.astimezone(TPE)
    if not isinstance(reference, (int, float)) or isinstance(reference, bool):
        raise ValueError("invalid_reference_price")
    if not math.isfinite(float(reference)) or reference <= 0:
        raise ValueError("invalid_reference_price")
    return {"symbol": symbol, "record_id": rid, "model_id": record["model_id"],
            "direction": record["direction"], "bar_time": observed,
            "reference_close": float(reference)}


def first_next_session(observation, daily_rows):
    """Use first future trading session (not the next calendar day)."""
    day = observation["bar_time"].date()
    future = []
    for row in daily_rows:
        ts = datetime.fromisoformat(row["timestamp"])
        if ts.utcoffset() is None:
            raise ValueError("provider_daily_timezone_required")
        ts = ts.astimezone(TPE)
        if ts.date() > day:
            future.append((ts, row))
    if not future:
        return None
    ts, row = min(future, key=lambda pair: pair[0])
    price = float(row["close"])
    if not math.isfinite(price) or price <= 0:
        raise ValueError("invalid_future_price")
    delta = (price / observation["reference_close"] - 1) * 100
    return {"schema": "sky-three-model-next-session-markout-v1",
            "ledger_record_id": observation["record_id"],
            "symbol": observation["symbol"], "model_id": observation["model_id"],
            "direction_at_observation": observation["direction"],
            "observation_bar_time": observation["bar_time"].isoformat(),
            "reference_close": observation["reference_close"],
            "next_session_close_time": ts.isoformat(),
            "next_session_close": price,
            "next_session_return_pct": round(delta, 8),
            "followup_type": "OBSERVATIONAL_PRICE_CHANGE_ONLY",
            "actual_fill": False, "realized_net_pnl": None,
            "net_strategy_return": None, "trade_eligible": False,
            "production_signal": False, "trading_enabled": False}


def create_only(store, bucket, record):
    key = (f"{OUTCOME_PREFIX}{record['model_id']}/"
           f"{record['symbol']}/{record['ledger_record_id']}.json")
    blob = store.bucket(bucket).blob(key)
    payload = canonical_json(record).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    try:
        blob.upload_from_string(payload, content_type="application/json",
                                if_generation_match=0)
        state = "CREATED"
    except Exception as exc:
        if type(exc).__name__ != "PreconditionFailed":
            raise
        state = "ALREADY_EXISTS_IDENTICAL"
    if hashlib.sha256(blob.download_as_bytes()).hexdigest() != digest:
        raise ValueError("immutable_followup_conflict")
    return {"ledger_record_id": record["ledger_record_id"],
            "status": state, "object_sha256": digest}


def run(store, bucket, key, as_of, *, fetch=read_fugle):
    if not bucket or bucket == "sky-disclosure-evidence-20261108":
        raise ValueError("invalid_research_bucket")
    if not key:
        raise ValueError("missing_fugle_key")
    if as_of > datetime.now(TPE).date():
        raise ValueError("future_followup_requested")
    blobs = list(store.list_blobs(bucket, prefix=OBS_PREFIX,
                                  max_results=MAX_SCAN))
    if len(blobs) >= MAX_SCAN:
        raise ValueError("ledger_scan_limit_reached")
    valid = []
    pending = []
    seen = set()
    for blob in blobs:
        if not blob.name.endswith(".json") or "/__preflight__/" in blob.name:
            continue
        record = json.loads(blob.download_as_bytes())
        item = validate_observation(record)
        rid = record["ledger_record_id"]
        if rid in seen:
            raise ValueError("duplicate_ledger_record_id")
        seen.add(rid)
        if item is None:
            pending.append({"ledger_record_id": rid,
                            "reason": "ORIGINAL_TIME_OR_REFERENCE_MISSING"})
        elif as_of <= item["bar_time"].date():
            pending.append({"ledger_record_id": rid,
                            "reason": "NO_LATER_COMPLETED_SESSION_YET"})
        elif (as_of - item["bar_time"].date()).days > 29:
            pending.append({"ledger_record_id": rid,
                            "reason": "OUTSIDE_30_DAY_FOLLOWUP_WINDOW"})
        else:
            valid.append(item)
    by_symbol = defaultdict(list)
    for row in valid:
        by_symbol[row["symbol"]].append(row)
    updates = []
    for symbol, group in sorted(by_symbol.items()):
        start = min(r["bar_time"].date() for r in group) + timedelta(days=1)
        candles = fetch(symbol, "D", start, as_of, key)
        for row in group:
            outcome = first_next_session(row, candles)
            if outcome is None:
                pending.append({"ledger_record_id": row["record_id"],
                                "reason": "NEXT_SESSION_CANDLE_NOT_AVAILABLE"})
                continue
            updates.append(create_only(store, bucket, outcome))
    return {"status": "RESEARCH_NEXT_SESSION_MARKOUT_AUDIT",
            "as_of_tpe": as_of.isoformat(),
            "observations_scanned": len(seen),
            "unique_symbols_queried": len(by_symbol),
            "completed_outcomes": len(updates),
            "new_outcomes": sum(x["status"] == "CREATED" for x in updates),
            "already_exists_identical": sum(
                x["status"] == "ALREADY_EXISTS_IDENTICAL" for x in updates),
            "pending_count": len(pending), "pending_reasons": pending,
            "write_evidence": updates,
            "historical_only": True, "realized_net_pnl": None,
            "production_signal": False, "trading_enabled": False,
            "note": "Descriptive next-session price movement, not trade P&L."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--end", required=True)
    p.add_argument("--bucket", default=os.getenv("SKY_RESEARCH_GCS_BUCKET", ""))
    p.add_argument("--out", default="output/three_model_next_session_audit.json")
    args = p.parse_args()
    from google.cloud import storage
    result = run(storage.Client(), args.bucket, os.getenv("FUGLE_API_KEY", ""),
                 date.fromisoformat(args.end))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "completed": result["completed_outcomes"],
                      "pending": result["pending_count"],
                      "trading_enabled": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
