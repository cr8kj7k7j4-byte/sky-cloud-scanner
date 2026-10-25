from __future__ import annotations

from typing import Any, Dict

MOBILE_API_VERSION = "1.0"

FIELDS = (
    "symbol","timestamp","latest_price","direction","bull_score","bear_score",
    "trigger","buy_range","add_price","stop","target","max_acceptable_price",
    "phase","classification","action","data_quality_status"
)

def build_mobile_payload(candidate: Dict[str, Any], *, timestamp=None, data_quality_status=None):
    c = candidate or {}
    monitor = c.get("monitor") or {}
    return {
        "api_version": MOBILE_API_VERSION,
        "symbol": str(c.get("symbol") or ""),
        "timestamp": timestamp or c.get("quote_time") or c.get("timestamp"),
        "latest_price": c.get("last", c.get("fugle_close")),
        "direction": c.get("direction"),
        "bull_score": c.get("bull_score"),
        "bear_score": c.get("bear_score"),
        "trigger": c.get("trigger"),
        "buy_range": c.get("buy_range"),
        "add_price": c.get("add_price"),
        "stop": c.get("stop"),
        "target": c.get("target", c.get("target1")),
        "max_acceptable_price": c.get("max_entry", c.get("highest_acceptable_price")),
        "phase": c.get("phase"),
        "classification": c.get("classification"),
        "action": monitor.get("action", c.get("action")),
        "data_quality_status": data_quality_status or c.get("data_quality_status"),
    }

def validate_mobile_payload(payload: Dict[str, Any]):
    missing_contract_fields = [f for f in FIELDS if f not in payload]
    return {
        "valid_contract": not missing_contract_fields,
        "missing_contract_fields": missing_contract_fields,
        "decision_logic_owned_here": False,
        "note": "Read-only projection; trading judgment remains upstream in P0-C/P0-R/P0-A.",
    }
