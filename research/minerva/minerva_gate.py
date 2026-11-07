"""Isolated evidence-based decision gates. No order placement and no alpha claims."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class DecisionEvidence:
    source_verified: bool
    timestamp_verified: bool
    coverage_verified: bool
    contradictory_data: bool
    short_eligible: Optional[bool]
    direction: str
    trigger_confirmed: bool
    chasing: bool
    stop_valid: bool
    net_rr: Optional[float]
    counterargument_reviewed: bool
    max_risk_ok: bool

@dataclass(frozen=True)
class GateResult:
    action: str
    classification: str
    reasons: tuple[str, ...]

def evaluate(e: DecisionEvidence) -> GateResult:
    """Fail-closed check, suitable for research/Shadow; NEVER a trade execution signal."""
    reasons = []
    if e.direction not in ("LONG", "SHORT"):
        reasons.append("INVALID_DIRECTION")
    if not e.source_verified or not e.timestamp_verified or not e.coverage_verified:
        reasons.append("INSUFFICIENT_MARKET_DATA")
    if e.contradictory_data:
        reasons.append("CONFLICTING_EVIDENCE")
    if e.direction == "SHORT" and e.short_eligible is not True:
        reasons.append("SHORT_ELIGIBILITY_UNVERIFIED")
    if e.chasing:
        reasons.append("ANTI_CHASE_VETO")
    if not e.stop_valid or not e.max_risk_ok:
        reasons.append("RISK_VETO")
    if e.net_rr is None or e.net_rr < 1.5:
        reasons.append("AFTER_COST_RR_FAIL")
    if not e.counterargument_reviewed:
        reasons.append("COUNTEREVIDENCE_NOT_REVIEWED")
    if reasons:
        return GateResult("禁止交易", "X", tuple(reasons))
    if not e.trigger_confirmed:
        return GateResult("等待", "A", ("TRIGGER_NOT_CONFIRMED",))
    # This layer never authorizes live trading. Other gates / P0-G remain mandatory.
    return GateResult("觀察", "A", ("RESEARCH_GATE_PASSED_NOT_LIVE_AUTHORIZED",))
