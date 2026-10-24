from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
from hashlib import sha256
from zoneinfo import ZoneInfo
import json


TZ = ZoneInfo("Asia/Taipei")
TRADE_LEDGER_SCHEMA_VERSION = "2.0.0"


@dataclass(frozen=True)
class TradeDecisionRecord:
    record_id: str
    schema_version: str
    observed_at: str
    run_id: str
    symbol: str
    name: str
    exchange: str | None
    mode: str
    decision: str
    classification_cap: str | None
    market: dict
    data_quality: dict
    features: dict
    ml: dict
    risk: dict
    plan: dict
    execution: dict
    outcome: dict

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class TradeRecord:
    symbol: str
    side: str
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    quantity: int
    initial_stop: float
    fees: float = 0.0
    tax: float = 0.0
    slippage: float = 0.0
    max_price_during_trade: float | None = None
    min_price_during_trade: float | None = None
    setup: str | None = None
    phase: str | None = None
    model_version: str | None = None
    decision_record_id: str | None = None
    strategy_version: str | None = None
    feature_schema_version: str | None = None
    rule_config_version: str | None = None

    def to_dict(self):
        return asdict(self)


def _parse_iso(value):
    return datetime.fromisoformat(value)


def build_trade_decision_record(*, item, run_id, observed_at=None, mode="SCANNER"):
    item = item or {}
    observed_at = observed_at or datetime.now(TZ)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=TZ)
    else:
        observed_at = observed_at.astimezone(TZ)

    symbol = str(item.get("symbol") or "")
    risk = dict(item.get("risk") or {})
    decision = risk.get("status") or "OBSERVE"
    raw_id = f"{run_id}|{symbol}|{mode}|{observed_at.isoformat()}"
    record_id = sha256(raw_id.encode("utf-8")).hexdigest()[:24]

    plan = {
        "entry": item.get("entry"),
        "stop": item.get("stop"),
        "target": item.get("target"),
        "highest_acceptable_price": item.get("highest_acceptable_price"),
        "add_price": item.get("add_price"),
        "net_rr": risk.get("net_rr"),
    }
    market = {
        "last": item.get("last"),
        "previous_close": item.get("previous_close"),
        "change_pct": item.get("change_pct"),
        "volume": item.get("volume"),
        "trade_value": item.get("trade_value"),
        "high": item.get("high"),
        "low": item.get("low"),
        "open": item.get("open"),
        "bid": item.get("bid"),
        "ask": item.get("ask"),
        "quote_time": item.get("quote_time"),
        "quote_source": item.get("quote_source"),
    }

    return TradeDecisionRecord(
        record_id=record_id,
        schema_version=TRADE_LEDGER_SCHEMA_VERSION,
        observed_at=observed_at.isoformat(),
        run_id=str(run_id),
        symbol=symbol,
        name=str(item.get("name") or ""),
        exchange=item.get("exchange"),
        mode=mode,
        decision=str(decision),
        classification_cap=item.get("classification_cap"),
        market=market,
        data_quality=dict(item.get("data_quality") or {}),
        features=dict(item.get("feature_envelope") or item.get("features") or {}),
        ml=dict(item.get("ml") or {}),
        risk=risk,
        plan=plan,
        execution=dict(item.get("execution") or {}),
        outcome=dict(item.get("outcome") or {}),
    )


def evaluate_trade_record(record):
    r = record if isinstance(record, TradeRecord) else TradeRecord(**record)

    if r.side.upper() not in {"LONG", "SHORT"}:
        raise ValueError("side must be LONG or SHORT")
    if r.quantity <= 0:
        raise ValueError("quantity must be positive")
    if r.entry_price <= 0 or r.exit_price <= 0 or r.initial_stop <= 0:
        raise ValueError("prices must be positive")

    direction = 1.0 if r.side.upper() == "LONG" else -1.0
    gross = (r.exit_price - r.entry_price) * direction * r.quantity
    total_cost = float(r.fees) + float(r.tax) + float(r.slippage)
    net = gross - total_cost

    initial_risk_per_share = abs(r.entry_price - r.initial_stop)
    initial_risk = initial_risk_per_share * r.quantity
    r_multiple = net / initial_risk if initial_risk > 0 else None

    mfe = None
    mae = None
    mfe_r = None
    mae_r = None
    if r.max_price_during_trade is not None and r.min_price_during_trade is not None:
        if r.side.upper() == "LONG":
            mfe = (r.max_price_during_trade - r.entry_price) * r.quantity
            mae = (r.entry_price - r.min_price_during_trade) * r.quantity
        else:
            mfe = (r.entry_price - r.min_price_during_trade) * r.quantity
            mae = (r.max_price_during_trade - r.entry_price) * r.quantity
        if initial_risk > 0:
            mfe_r = mfe / initial_risk
            mae_r = mae / initial_risk

    duration_minutes = (
        _parse_iso(r.exit_time) - _parse_iso(r.entry_time)
    ).total_seconds() / 60.0

    return {
        "schema_version": TRADE_LEDGER_SCHEMA_VERSION,
        **r.to_dict(),
        "gross_pnl": round(gross, 2),
        "total_cost": round(total_cost, 2),
        "net_pnl": round(net, 2),
        "initial_risk": round(initial_risk, 2),
        "r_multiple": round(r_multiple, 4) if r_multiple is not None else None,
        "mfe_amount": round(mfe, 2) if mfe is not None else None,
        "mae_amount": round(mae, 2) if mae is not None else None,
        "mfe_r": round(mfe_r, 4) if mfe_r is not None else None,
        "mae_r": round(mae_r, 4) if mae_r is not None else None,
        "holding_minutes": round(duration_minutes, 2),
    }


def append_jsonl(record, path="output/trade_decisions.jsonl"):
    payload = record.to_dict() if hasattr(record, "to_dict") else dict(record)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return str(target)


def append_trade(path, record):
    evaluated = evaluate_trade_record(record)
    append_jsonl(evaluated, path=path)
    return evaluated


def attach_outcome(record, outcome):
    payload = record.to_dict() if hasattr(record, "to_dict") else dict(record)
    outcome_payload = outcome.to_dict() if hasattr(outcome, "to_dict") else dict(outcome or {})
    payload["schema_version"] = TRADE_LEDGER_SCHEMA_VERSION
    payload["outcome"] = outcome_payload
    return payload


def build_canonical_ledger_entry(decision_record, trade_result=None):
    decision = (
        decision_record.to_dict()
        if hasattr(decision_record, "to_dict")
        else dict(decision_record or {})
    )
    trade = dict(trade_result or {})
    return {
        "schema_version": TRADE_LEDGER_SCHEMA_VERSION,
        "record_id": decision.get("record_id"),
        "decision": decision,
        "trade": trade,
        "outcome": trade.get("outcome") or decision.get("outcome") or {},
    }
