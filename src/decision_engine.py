from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from .config import MAX_PRICE, MIN_VOLUME, MIN_TRADE_VALUE


DECISION_SCHEMA_VERSION = "1.0"


def spread_pct(row):
    row = row or {}
    bid = row.get("bid")
    ask = row.get("ask")
    if not bid or not ask or ask < bid:
        return None
    mid = (bid + ask) / 2
    return (ask - bid) / mid * 100 if mid else None


def first_gate(row):
    """Canonical P0-C first eligibility gate.

    This gate filters obvious non-tradable candidates before ranking.
    It does not create a buy signal and does not replace downstream P0-R.
    """
    row = row or {}
    reasons = []
    if row.get("last") is None or row["last"] > MAX_PRICE:
        reasons.append(f"股價>{MAX_PRICE:g}或無有效成交價")
    if row.get("volume", 0) < MIN_VOLUME:
        reasons.append(f"量<{MIN_VOLUME}張")
    if row.get("trade_value", 0) < MIN_TRADE_VALUE:
        reasons.append(f"成交值<{MIN_TRADE_VALUE:,.0f}")
    sp = spread_pct(row)
    if sp is not None and sp > 0.8:
        reasons.append(f"價差過大({sp:.2f}%)")
    return not reasons, reasons


@dataclass(frozen=True)
class DecisionContract:
    schema_version: str
    symbol: str
    status: str
    action: str
    classification_cap: str | None
    monitor_state: str | None
    risk_status: str | None
    evidence_eligible: bool
    agent_status: str | None
    strategy_production_eligible: bool
    live_execution_allowed: bool
    reasons: List[str]
    guardrails: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _unique(items):
    out = []
    for x in items:
        s = str(x)
        if s and s not in out:
            out.append(s)
    return out


def evaluate_decision(candidate: Dict[str, Any]) -> DecisionContract:
    """Canonical P0-C decision contract.

    P0-C does not rank candidates, generate strategy levels, calculate risk,
    or submit orders. It only consolidates the outputs of upstream engines
    into one deterministic decision state.

    Priority:
    1. hard reject / P0-R block / P0-A invalidation
    2. missing or conflicted evidence / missing risk
    3. trigger states remain WAIT, never auto-buy
    4. otherwise OBSERVE

    Live execution remains disabled in this system.
    """
    c = candidate or {}
    symbol = str(c.get("symbol") or "")
    risk = dict(c.get("risk") or {})
    monitor = dict(c.get("monitor") or {})
    ledger = dict(c.get("evidence_ledger") or {})
    agent = dict(c.get("agent_orchestration") or {})
    plan = dict(c.get("strategy_plan") or {})

    risk_status = risk.get("status")
    monitor_state = monitor.get("state")
    agent_status = agent.get("decision_status")
    evidence_eligible = bool(ledger.get("decision_eligible", False))
    strategy_production_eligible = bool(plan.get("production_eligible", False))
    classification_cap = c.get("classification_cap")

    flags = [str(x) for x in c.get("flags", [])]
    x_flags = [x for x in flags if x.startswith("X:")]

    reasons = []
    status = "OBSERVE"
    action = monitor.get("action") or "觀察"

    if x_flags:
        status = "BLOCK"
        action = "禁止交易"
        reasons.extend(x_flags)
    elif risk_status == "BLOCK":
        status = "BLOCK"
        action = "禁止交易"
        reasons.extend(risk.get("reasons") or ["P0-R 禁止進場"])
    elif monitor_state in {"BLOCKED", "INVALIDATED"}:
        status = "BLOCK"
        action = "禁止交易"
        reasons.append(monitor.get("reason") or f"P0-A {monitor_state}")
    elif risk_status in {None, "RISK_INPUT_REQUIRED"}:
        status = "DATA_REQUIRED"
        action = "等待"
        reasons.append("P0-R 正式風控輸入不足")
    elif not evidence_eligible:
        status = "DATA_REQUIRED"
        action = "等待"
        if ledger.get("conflict"):
            reasons.append("P0-K Evidence Ledger 存在衝突")
        if ledger.get("stale_count"):
            reasons.append("P0-K Evidence Ledger 含過期證據")
        if not ledger.get("items"):
            reasons.append("缺少可追溯證據")
        if not reasons:
            reasons.append("P0-K 證據尚未達 decision eligible")
    elif agent_status not in (None, "REVIEW_READY"):
        status = "BLOCK" if agent_status == "BLOCK" else "DATA_REQUIRED"
        action = "禁止交易" if status == "BLOCK" else "等待"
        reasons.append(f"Agent Orchestration 狀態 {agent_status}")
    elif monitor_state in {"TRIGGERED", "NEAR_TRIGGER"}:
        status = "WAIT"
        action = "等待"
        reasons.append(
            "價格已進入觸發監控區，但仍需量價/VWAP/結構確認"
            if monitor_state == "TRIGGERED"
            else "價格接近觸發價"
        )
    else:
        status = "OBSERVE"
        action = monitor.get("action") or "觀察"
        reasons.append(monitor.get("reason") or "尚未形成新的可執行條件")

    # Research-only strategies can be observed/shadowed but never promoted
    # into a production/live execution signal by P0-C.
    if not strategy_production_eligible:
        reasons.append("P0-S 策略仍為 research-only，不得升格為真實交易訊號")

    return DecisionContract(
        schema_version=DECISION_SCHEMA_VERSION,
        symbol=symbol,
        status=status,
        action=action,
        classification_cap=classification_cap,
        monitor_state=monitor_state,
        risk_status=risk_status,
        evidence_eligible=evidence_eligible,
        agent_status=agent_status,
        strategy_production_eligible=strategy_production_eligible,
        live_execution_allowed=False,
        reasons=_unique(reasons),
        guardrails={
            "ranking_input_used": False,
            "single_agent_can_trade": False,
            "must_pass_p0_r": True,
            "evidence_required": True,
            "triggered_is_not_buy": True,
            "live_execution_enabled": False,
        },
    )
