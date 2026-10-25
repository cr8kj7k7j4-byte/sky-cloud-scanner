from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
from typing import Iterable

from research.w6_execution_baseline import (
    W6L1ExecutionSample,
    aggregate_fill_rates,
)


SCHEMA_VERSION = "1.0"


def _finite(value):
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x


def decision_to_w6_evidence(decision: dict) -> dict:
    """Create a fail-closed W6 evidence row from a canonical P0-L decision.

    This does not infer fills. If execution evidence is absent, fill_status
    remains UNKNOWN and fill_price remains None.
    """
    row = dict(decision or {})
    market = dict(row.get("market") or {})
    execution = dict(row.get("execution") or {})
    plan = dict(row.get("plan") or {})

    observed_at = row.get("observed_at")
    symbol = str(row.get("symbol") or "")

    reference_price = execution.get("reference_price")
    if reference_price is None:
        reference_price = plan.get("entry")
    if reference_price is None:
        reference_price = market.get("last")

    fill_status = str(execution.get("fill_status") or "UNKNOWN").upper()
    fill_price = _finite(execution.get("fill_price"))

    # Never retain a fill price for explicit non-fill states.
    if fill_status in {"MISSED", "CANCELLED", "REJECTED"}:
        fill_price = None

    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": row.get("record_id"),
        "run_id": row.get("run_id"),
        "strategy_id": row.get("strategy_id"),
        "strategy_version": row.get("strategy_version"),
        "symbol": symbol,
        "exchange": row.get("exchange"),
        "observation_timestamp": observed_at,
        "execution_type": execution.get("execution_type") or execution.get("type") or "UNKNOWN",
        "reference_price": _finite(reference_price),
        "bid": _finite(market.get("bid")),
        "ask": _finite(market.get("ask")),
        "quote_timestamp": market.get("quote_time"),
        "quote_source": market.get("quote_source"),
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

    for row in items:
        metrics = validate_evidence_row(row)
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

        if metrics.get("spread_bps") is not None:
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
    return {
        "status": "P1_BASELINE_READY" if len(items) >= 20 and valid == len(items) else "INSUFFICIENT_DATA",
        "sample": len(items),
        "valid_sample": valid,
        "fill_rate": fill.get("fill_rate"),
        "missed_trade_rate": fill.get("missed_trade_rate"),
        "spread_sample_count": len(spread_values),
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
            "P1 summary is execution evidence only. It does not prove directional alpha "
            "or authorize Production changes."
        ),
    }


def _mean(values):
    return None if not values else sum(values) / len(values)


def _bool_rate(values):
    return None if not values else sum(bool(x) for x in values) / len(values)
