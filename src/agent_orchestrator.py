from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from .knowledge_engine import build_evidence_ledger


@dataclass
class AgentFinding:
    agent: str
    stance: str
    score: int
    facts: List[str]
    inferences: List[str]
    unknowns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def market_agent(candidate: Dict[str, Any]) -> AgentFinding:
    chg = candidate.get("change_pct")
    facts, inferences, unknowns = [], [], []
    score = 50
    if chg is not None:
        chg = float(chg)
        facts.append(f"當日漲跌幅 {chg:+.2f}%")
        score = _clamp_score(50 + chg * 4)
        inferences.append("僅代表當日價格方向，不等同可交易訊號")
    else:
        unknowns.append("缺少當日漲跌幅")
    stance = "偏多" if score >= 60 else "偏空" if score <= 40 else "中性"
    return AgentFinding("Market Agent", stance, score, facts, inferences, unknowns)


def technical_agent(candidate: Dict[str, Any]) -> AgentFinding:
    features = candidate.get("features") or {}
    facts, inferences, unknowns = [], [], []
    score = 50
    momentum = features.get("momentum_5")
    vwap = features.get("vwap_distance_pct")
    volume_ratio = features.get("volume_ratio")

    if momentum is not None:
        momentum = float(momentum)
        facts.append(f"5期動能 {momentum:.3f}")
        score += max(-20, min(20, momentum * 4))
    else:
        unknowns.append("缺少5期動能")

    if volume_ratio is not None:
        volume_ratio = float(volume_ratio)
        facts.append(f"量比 {volume_ratio:.3f}")
        if volume_ratio >= 1.2:
            score += 8
    else:
        unknowns.append("缺少量比")

    if vwap is not None:
        vwap = float(vwap)
        facts.append(f"距VWAP {vwap:.3f}%")
        if abs(vwap) >= 3:
            score -= 15
            inferences.append("與VWAP乖離偏大，Anti-Chase 風險升高")
    else:
        unknowns.append("缺少VWAP距離")

    score = _clamp_score(score)
    stance = "偏多" if score >= 60 else "偏空" if score <= 40 else "中性"
    return AgentFinding("Technical Agent", stance, score, facts, inferences, unknowns)


def risk_agent(candidate: Dict[str, Any]) -> AgentFinding:
    risk = candidate.get("risk") or {}
    status = risk.get("status")
    facts, inferences, unknowns = [], [], []
    if not status:
        unknowns.append("尚未執行 P0-R")
        return AgentFinding("Risk Agent", "禁止判定", 0, facts, inferences, unknowns)

    facts.append(f"P0-R 狀態 {status}")
    reasons = [str(x) for x in risk.get("reasons", [])]
    facts.extend(reasons)
    score = 100 if status == "ALLOW" else 0
    stance = "允許" if status == "ALLOW" else "禁止"
    return AgentFinding("Risk Agent", stance, score, facts, inferences, unknowns)


def devils_advocate_agent(candidate: Dict[str, Any], ledger: Dict[str, Any]) -> AgentFinding:
    facts, inferences, unknowns = [], [], []
    score = 100

    if ledger.get("conflict"):
        score -= 50
        facts.append("Evidence Ledger 存在來源衝突")
        inferences.append("衝突未解前不得提高交易信心")
    if ledger.get("stale_count", 0):
        score -= 30
        facts.append(f"過期證據 {ledger['stale_count']} 筆")
    flags = [str(x) for x in candidate.get("flags", [])]
    x_flags = [x for x in flags if x.startswith("X:")]
    if x_flags:
        score = 0
        facts.extend(x_flags)
        inferences.append("存在強制否決旗標")
    if not ledger.get("items"):
        score = 0
        unknowns.append("缺少可追溯證據")

    return AgentFinding("Devil’s Advocate Agent", "通過" if score >= 70 else "警戒", _clamp_score(score), facts, inferences, unknowns)


def orchestrate(candidate: Dict[str, Any], evidence_ledger: Dict[str, Any]) -> Dict[str, Any]:
    findings = [
        market_agent(candidate),
        technical_agent(candidate),
        risk_agent(candidate),
        devils_advocate_agent(candidate, evidence_ledger),
    ]
    risk = next(x for x in findings if x.agent == "Risk Agent")
    devil = next(x for x in findings if x.agent == "Devil’s Advocate Agent")

    blocked = risk.stance != "允許" or devil.score < 70
    return {
        "agents": [x.to_dict() for x in findings],
        "decision_status": "BLOCK" if blocked else "REVIEW_READY",
        "guardrails": {
            "single_agent_can_trade": False,
            "must_pass_p0_r": True,
            "evidence_required": True,
            "hallucination_guard": True,
        },
    }


def orchestrate_with_evidence(candidate: Dict[str, Any], evidence_items, *, max_age_hours=None, now=None):
    ledger = build_evidence_ledger(evidence_items, max_age_hours=max_age_hours, now=now)
    return ledger, orchestrate(candidate, ledger)
