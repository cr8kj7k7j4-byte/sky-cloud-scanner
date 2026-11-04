from __future__ import annotations

from pathlib import Path
import json
import math
from datetime import datetime, timezone
from typing import Iterable

from research.w6_execution_baseline import (
    W6L1ExecutionSample,
    aggregate_fill_rates,
)


SCHEMA_VERSION = "1.1"


def _finite(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None



# Source timestamps may be ISO 8601, or Fugle Unix epoch microseconds.
# Invalid, timezone-naive, or future-dated quote evidence cannot pass the PIT gate.
def _timestamp(value):
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
            v = float(value)
            if not math.isfinite(v) or v <= 0:
                return None
            seconds = v / 1_000_000 if v >= 1e14 else v / 1_000 if v >= 1e11 else v
            return datetime.fromtimestamp(seconds, timezone.utc)
        if isinstance(value, str) and value:
            t = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return t if t.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError, OSError):
        pass
    return None


def quote_time_integrity(row):
    """Distinguish a quote captured later from a quote available at decision time.

    Quote-only spreads can be audited at their own acquisition time, never
    retroactively attached to the scan-start/decision timestamp.
    """
    qt = _timestamp(row.get("quote_timestamp"))
    decision = _timestamp(row.get("observation_timestamp"))
    capture = _timestamp(row.get("quote_observation_timestamp")) or decision
    has_source = bool(row.get("quote_source"))
    age = (capture - qt).total_seconds() if capture is not None and qt is not None else None
    decision_age = (decision - qt).total_seconds() if decision is not None and qt is not None else None
    # A conservative 60-second quote freshness cap is an integrity condition,
    # not a strategy parameter, and does not establish fillability.
    quote_valid = bool(has_source and age is not None and 0 <= age <= 60)
    decision_valid = bool(has_source and decision_age is not None and 0 <= decision_age <= 60)
    return {
        "quote_timestamp_valid": qt is not None,
        "quote_source_present": has_source,
        "quote_age_seconds": age,
        "quote_after_scan_observation": decision_age is not None and decision_age < 0,
        "quote_spread_time_valid": quote_valid,
        "decision_time_quote_valid": decision_valid,
        "time_basis": "QUOTE_ACQUISITION" if row.get("quote_observation_timestamp") else "LEGACY_SCAN_OBSERVATION",
    }


def decision_to_w6_evidence(decision: dict) -> dict:
    """Create a fail-closed W6 evidence row from a canonical P0-L decision."""
    row = dict(decision or {})
    market = dict(row.get("market") or {})
    execution = dict(row.get("execution") or {})
    plan = dict(row.get("plan") or {})

    observed_at = row.get("observed_at")
    reference_price = execution.get("reference_price")
    if reference_price is None:
        reference_price = plan.get("entry")
    if reference_price is None:
        reference_price = market.get("last")

    fill_status = str(execution.get("fill_status") or "UNKNOWN").upper()
    fill_price = _finite(execution.get("fill_price"))
    if fill_status in {"MISSED", "CANCELLED", "REJECTED"}:
        fill_price = None

    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": row.get("record_id"),
        "observation_record_id": row.get("observation_record_id"),
        "decision_id": row.get("decision_id"),
        "decision_provenance_status": row.get("decision_provenance_status"),
        "run_id": row.get("run_id"),
        "strategy_id": row.get("strategy_id"),
        "strategy_version": row.get("strategy_version"),
        "symbol": str(row.get("symbol") or ""),
        "exchange": row.get("exchange"),
        "observation_timestamp": observed_at,
        "execution_type": execution.get("execution_type") or execution.get("type") or "UNKNOWN",
        "reference_price": _finite(reference_price),
        "bid": _finite(market.get("bid")),
        "ask": _finite(market.get("ask")),
        "bid_size": _finite(market.get("bid_size")),
        "ask_size": _finite(market.get("ask_size")),
        "quote_timestamp": market.get("l1_quote_time") or market.get("quote_time"),
        "quote_observation_timestamp": market.get("l1_observed_at"),
        "quote_serial": market.get("l1_quote_serial"),
        "quote_source": market.get("l1_quote_source") or market.get("quote_source"),
        "fill_status": fill_status,
        "fill_price": fill_price,
        "fill_timestamp": execution.get("fill_timestamp"),
        "requested_price": _finite(execution.get("requested_price")),
        "max_chase_price": _finite(plan.get("highest_acceptable_price")),
        "risk_per_share": _risk_per_share(plan),
        "future_price_1m": _finite(execution.get("future_price_1m")),
        "future_price_3m": _finite(execution.get("future_price_3m")),
        "future_price_5m": _finite(execution.get("future_price_5m")),
        "research_only": True,
    }


def paper_snapshot_to_w6_evidence(snapshot: dict) -> dict:
    """Map a Shadow/Paper snapshot to quote evidence without inventing fills."""
    row = dict(snapshot or {})
    market = dict(row.get("market") or {})
    strategy = dict(row.get("strategy") or {})
    execution = dict(row.get("execution") or {})

    reference_price = execution.get("reference_price")
    if reference_price is None:
        reference_price = row.get("assumed_entry")
    if reference_price is None:
        reference_price = row.get("trigger_price")
    if reference_price is None:
        reference_price = market.get("last")

    fill_status = str(execution.get("fill_status") or "UNKNOWN").upper()
    fill_price = _finite(execution.get("fill_price"))
    if fill_status in {"MISSED", "CANCELLED", "REJECTED"}:
        fill_price = None

    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": row.get("record_id"),
        "observation_record_id": row.get("observation_record_id"),
        "decision_id": row.get("decision_id"),
        "decision_provenance_status": row.get("decision_provenance_status"),
        "run_id": row.get("run_id"),
        "strategy_id": row.get("strategy_id"),
        "strategy_version": row.get("strategy_version"),
        "symbol": str(row.get("symbol") or ""),
        "exchange": row.get("exchange"),
        "observation_timestamp": row.get("observation_timestamp") or row.get("observed_at"),
        "execution_type": execution.get("execution_type") or "QUOTE_ONLY",
        "reference_price": _finite(reference_price),
        "bid": _finite(market.get("bid")),
        "ask": _finite(market.get("ask")),
        "bid_size": _finite(market.get("bid_size")),
        "ask_size": _finite(market.get("ask_size")),
        "quote_timestamp": market.get("l1_quote_time") or market.get("quote_time"),
        "quote_serial": market.get("l1_quote_serial"),
        "quote_source": market.get("l1_quote_source") or market.get("quote_source"),
        "fill_status": fill_status,
        "fill_price": fill_price,
        "fill_timestamp": execution.get("fill_timestamp"),
        "requested_price": _finite(execution.get("requested_price")),
        "max_chase_price": _finite(row.get("max_acceptable_price") or strategy.get("max_entry")),
        "risk_per_share": _finite(row.get("risk_per_share")),
        "future_price_1m": _finite(execution.get("future_price_1m")),
        "future_price_3m": _finite(execution.get("future_price_3m")),
        "future_price_5m": _finite(execution.get("future_price_5m")),
        "research_only": True,
    }


def _risk_per_share(plan: dict):
    entry = _finite(plan.get("entry"))
    stop = _finite(plan.get("stop"))
    if entry is None or stop is None:
        return None
    return abs(entry - stop)


def validate_evidence_row(row: dict) -> dict:
    sample = W6L1ExecutionSample(
        symbol=str(row.get("symbol") or ""),
        observation_timestamp=str(row.get("observation_timestamp") or ""),
        execution_type=str(row.get("execution_type") or "UNKNOWN"),
        reference_price=_finite(row.get("reference_price")),
        bid=_finite(row.get("bid")),
        ask=_finite(row.get("ask")),
        fill_status=str(row.get("fill_status") or "UNKNOWN").upper(),
        fill_price=_finite(row.get("fill_price")),
        risk_per_share=_finite(row.get("risk_per_share")),
        future_price_1m=_finite(row.get("future_price_1m")),
        future_price_3m=_finite(row.get("future_price_3m")),
        future_price_5m=_finite(row.get("future_price_5m")),
    )
    return sample.metrics()


def append_evidence_jsonl(row: dict, path: str | Path = "output/private/w6_execution_evidence.jsonl") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(row)
    payload["validation"] = validate_evidence_row(payload)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return p


def load_evidence_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def summarize_p1(rows: Iterable[dict]) -> dict:
    items = [dict(x) for x in rows if isinstance(x, dict)]
    samples = []
    valid = 0
    spread_values = []
    slippage_values = []
    slippage_r_values = []
    adverse = {1: [], 3: [], 5: []}
    by_time = {}
    by_price = {}
    quote_time_valid_count = 0
    quote_decision_time_valid_count = 0
    quote_after_scan_count = 0
    quote_missing_or_invalid_count = 0

    for row in items:
        metrics = validate_evidence_row(row)
        quote_quality = quote_time_integrity(row)
        quote_time_valid_count += int(quote_quality["quote_spread_time_valid"])
        quote_decision_time_valid_count += int(quote_quality["decision_time_quote_valid"])
        quote_after_scan_count += int(quote_quality["quote_after_scan_observation"])
        quote_missing_or_invalid_count += int(not quote_quality["quote_spread_time_valid"])
        if metrics.get("status") == "OK":
            valid += 1
        sample = W6L1ExecutionSample(
            symbol=str(row.get("symbol") or ""),
            observation_timestamp=str(row.get("observation_timestamp") or ""),
            execution_type=str(row.get("execution_type") or "UNKNOWN"),
            reference_price=_finite(row.get("reference_price")),
            bid=_finite(row.get("bid")),
            ask=_finite(row.get("ask")),
            fill_status=str(row.get("fill_status") or "UNKNOWN").upper(),
            fill_price=_finite(row.get("fill_price")),
            risk_per_share=_finite(row.get("risk_per_share")),
            future_price_1m=_finite(row.get("future_price_1m")),
            future_price_3m=_finite(row.get("future_price_3m")),
            future_price_5m=_finite(row.get("future_price_5m")),
        )
        samples.append(sample)

        if metrics.get("spread_bps") is not None and quote_quality["quote_spread_time_valid"]:
            spread_values.append(metrics["spread_bps"])
        if metrics.get("entry_slippage_bps") is not None:
            slippage_values.append(metrics["entry_slippage_bps"])
        if metrics.get("slippage_r") is not None:
            slippage_r_values.append(metrics["slippage_r"])
        for horizon in (1, 3, 5):
            key = f"adverse_selection_{horizon}m"
            if metrics.get(key) is not None:
                adverse[horizon].append(bool(metrics[key]))

        tb = metrics.get("time_bucket")
        pb = metrics.get("price_bucket")
        if tb:
            by_time.setdefault(tb, []).append(sample)
        if pb:
            by_price.setdefault(pb, []).append(sample)

    fill = aggregate_fill_rates(samples)
    spread_status = "BASELINE_READY" if len(spread_values) >= 20 else "INSUFFICIENT_DATA"
    slippage_status = "BASELINE_READY" if len(slippage_values) >= 20 else "INSUFFICIENT_DATA"
    overall_ready = (
        spread_status == "BASELINE_READY"
        and slippage_status == "BASELINE_READY"
        and valid == len(items)
    )

    return {
        "status": "P1_BASELINE_READY" if overall_ready else "INSUFFICIENT_DATA",
        "spread_status": spread_status,
        "slippage_status": slippage_status,
        "sample": len(items),
        "valid_sample": valid,
        "fill_evaluable_sample": fill.get("sample"),
        "fill_unknown_sample": fill.get("unknown_sample"),
        "fill_rate": fill.get("fill_rate"),
        "missed_trade_rate": fill.get("missed_trade_rate"),
        "spread_sample_count": len(spread_values),
        "quote_spread_pit_valid_count": quote_time_valid_count,
        "decision_time_quote_valid_count": quote_decision_time_valid_count,
        "quote_after_scan_observation_count": quote_after_scan_count,
        "quote_missing_or_invalid_count": quote_missing_or_invalid_count,
        "quote_time_integrity_policy": "Source + parseable timezone-aware quote/acquisition timestamps; quote age 0-60s; no future quote for its acquisition timestamp. Decision-time validity is reported separately.",
        "avg_spread_bps": _mean(spread_values),
        "slippage_sample_count": len(slippage_values),
        "avg_entry_slippage_bps": _mean(slippage_values),
        "slippage_r_sample_count": len(slippage_r_values),
        "avg_slippage_r": _mean(slippage_r_values),
        "adverse_selection_rate_1m": _bool_rate(adverse[1]),
        "adverse_selection_rate_3m": _bool_rate(adverse[3]),
        "adverse_selection_rate_5m": _bool_rate(adverse[5]),
        "time_bucket_fill": {k: aggregate_fill_rates(v) for k, v in sorted(by_time.items())},
        "price_bucket_fill": {k: aggregate_fill_rates(v) for k, v in sorted(by_price.items())},
        "note": (
            "Spread evidence and slippage evidence are gated separately. Quote-only "
            "rows may establish a quote-time Spread baseline (only when timestamp-valid) but can never establish Slippage, "
            "Fill Rate or Adverse Selection without explicit fill evidence."
        ),
    }


def _mean(values):
    return None if not values else sum(values) / len(values)


def _bool_rate(values):
    return None if not values else sum(bool(x) for x in values) / len(values)
