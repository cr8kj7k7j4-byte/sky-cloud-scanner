from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass(frozen=True)
class ShadowOutcome:
    event_id: str
    config_role: str
    config_version: str
    symbol: str
    regime: str | None
    signaled: bool
    accepted_by_risk: bool
    triggered: bool
    net_r: float | None = None
    mfe_r: float | None = None
    mae_r: float | None = None
    false_breakout: bool = False
    missed_opportunity: bool = False
    rejection_reason: str | None = None

    def to_dict(self):
        return asdict(self)


def _safe_mean(values):
    vals=[float(x) for x in values if x is not None]
    return sum(vals)/len(vals) if vals else 0.0


def _profit_factor(values):
    vals=[float(x) for x in values if x is not None]
    gains=sum(x for x in vals if x>0)
    losses=abs(sum(x for x in vals if x<0))
    if losses==0:
        return float("inf") if gains>0 else 0.0
    return gains/losses


def summarize_outcomes(rows):
    rows=list(rows or [])
    triggered=[r for r in rows if r.triggered and r.net_r is not None]
    net_r=[r.net_r for r in triggered]
    pf=_profit_factor(net_r)

    return {
        "events": len(rows),
        "signals": sum(1 for r in rows if r.signaled),
        "risk_accepted": sum(1 for r in rows if r.accepted_by_risk),
        "triggered": len(triggered),
        "expectancy_r": round(_safe_mean(net_r),6),
        "profit_factor": round(pf,6) if pf != float("inf") else "inf",
        "mfe_r_mean": round(_safe_mean([r.mfe_r for r in triggered]),6),
        "mae_r_mean": round(_safe_mean([r.mae_r for r in triggered]),6),
        "false_breakouts": sum(1 for r in rows if r.false_breakout),
        "missed_opportunities": sum(1 for r in rows if r.missed_opportunity),
        "risk_rejections": sum(1 for r in rows if r.signaled and not r.accepted_by_risk),
    }


def compare_roles(rows):
    groups=defaultdict(list)
    for row in rows or []:
        r=row if isinstance(row,ShadowOutcome) else ShadowOutcome(**row)
        groups[r.config_role.upper()].append(r)

    champion=summarize_outcomes(groups.get("CHAMPION",[]))
    challenger=summarize_outcomes(groups.get("CHALLENGER",[]))

    def pf(v):
        return 999.0 if v=="inf" else float(v or 0.0)

    delta={
        "expectancy_r": round(float(challenger["expectancy_r"])-float(champion["expectancy_r"]),6),
        "profit_factor": round(pf(challenger["profit_factor"])-pf(champion["profit_factor"]),6),
        "mfe_r_mean": round(float(challenger["mfe_r_mean"])-float(champion["mfe_r_mean"]),6),
        "mae_r_mean": round(float(champion["mae_r_mean"])-float(challenger["mae_r_mean"]),6),
        "false_breakouts": champion["false_breakouts"]-challenger["false_breakouts"],
        "missed_opportunities": champion["missed_opportunities"]-challenger["missed_opportunities"],
        "risk_rejections": champion["risk_rejections"]-challenger["risk_rejections"],
    }
    return {"champion":champion,"challenger":challenger,"delta":delta}


def compare_by_regime(rows):
    buckets=defaultdict(list)
    for row in rows or []:
        r=row if isinstance(row,ShadowOutcome) else ShadowOutcome(**row)
        buckets[r.regime or "UNKNOWN"].append(r)
    return {regime:compare_roles(items) for regime,items in buckets.items()}
