# Legacy research compatibility adapter.
# Canonical V2.1 module is P0-L / trade_logger.py; this file is retained so
# historical research datasets and tests remain reproducible.

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Taipei")
TRADE_LOG_SCHEMA_VERSION = "1.0"


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
        schema_version=TRADE_LOG_SCHEMA_VERSION,
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
        execution={},
        outcome={},
    )


def append_jsonl(record, path="output/trade_decisions.jsonl"):
    if hasattr(record, "to_dict"):
        payload = record.to_dict()
    else:
        payload = dict(record)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return str(target)


def attach_outcome(record, outcome):
    """Return a new serializable record with the outcome payload attached."""
    payload = record.to_dict() if hasattr(record, "to_dict") else dict(record)
    outcome_payload = outcome.to_dict() if hasattr(outcome, "to_dict") else dict(outcome or {})
    payload["outcome"] = outcome_payload
    return payload
