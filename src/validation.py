from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ValidationGate:
    walk_forward_passed: bool
    oos_passed: bool
    cost_stress_passed: bool
    leakage_check_passed: bool
    paper_trade_passed: bool

    def to_dict(self):
        return asdict(self)

    @property
    def production_eligible(self):
        return all([
            self.walk_forward_passed,
            self.oos_passed,
            self.cost_stress_passed,
            self.leakage_check_passed,
            self.paper_trade_passed,
        ])


def evaluate_validation_gate(
    *,
    walk_forward_passed=False,
    oos_passed=False,
    cost_stress_passed=False,
    leakage_check_passed=False,
    paper_trade_passed=False,
):
    gate = ValidationGate(
        walk_forward_passed=bool(walk_forward_passed),
        oos_passed=bool(oos_passed),
        cost_stress_passed=bool(cost_stress_passed),
        leakage_check_passed=bool(leakage_check_passed),
        paper_trade_passed=bool(paper_trade_passed),
    )
    return {
        **gate.to_dict(),
        "production_eligible": gate.production_eligible,
        "status": "PRODUCTION_ELIGIBLE" if gate.production_eligible else "RESEARCH_ONLY",
    }


from math import isfinite
from dataclasses import dataclass as _dataclass


@_dataclass(frozen=True)
class CostScenario:
    name: str
    round_trip_cost_pct: float
    slippage_pct: float


DEFAULT_COST_SCENARIOS = (
    CostScenario("BASE", 0.45, 0.05),
    CostScenario("STRESS_1", 0.60, 0.10),
    CostScenario("STRESS_2", 0.80, 0.15),
)


def cost_stress_report(gross_returns_pct, scenarios=None):
    scenarios = tuple(scenarios or DEFAULT_COST_SCENARIOS)
    vals = [float(x) for x in (gross_returns_pct or []) if x is not None and isfinite(float(x))]
    rows = []
    for s in scenarios:
        nets = [x - float(s.round_trip_cost_pct) - float(s.slippage_pct) for x in vals]
        expectancy = sum(nets) / len(nets) if nets else 0.0
        rows.append({
            "scenario": s.name,
            "round_trip_cost_pct": s.round_trip_cost_pct,
            "slippage_pct": s.slippage_pct,
            "n": len(nets),
            "net_expectancy_pct": round(expectancy, 6),
            "net_positive_rate": round(sum(1 for x in nets if x > 0) / len(nets), 6) if nets else 0.0,
            "passed": bool(nets and expectancy > 0),
        })
    return {
        "scenarios": rows,
        "passed": bool(rows) and all(x["passed"] for x in rows),
        "note": "Research validation only; stress pass requires positive net expectancy in every configured scenario.",
    }


def leakage_audit(feature_columns, target_columns, metadata=None):
    features = set(feature_columns or [])
    targets = set(target_columns or [])
    metadata = dict(metadata or {})
    overlaps = sorted(features & targets)
    suspicious = sorted(
        x for x in features
        if any(token in str(x).lower() for token in ("future", "forward", "target", "label", "mfe", "mae"))
    )
    timestamp_order_ok = bool(metadata.get("timestamp_order_ok", False))
    survivorship_reviewed = bool(metadata.get("survivorship_reviewed", False))
    return {
        "passed": not overlaps and not suspicious and timestamp_order_ok and survivorship_reviewed,
        "feature_target_overlap": overlaps,
        "suspicious_feature_names": suspicious,
        "timestamp_order_ok": timestamp_order_ok,
        "survivorship_reviewed": survivorship_reviewed,
    }


def aggregate_by_regime(records):
    groups = {}
    for row in records or []:
        key = str(row.get("regime") or "UNKNOWN")
        groups.setdefault(key, []).append(float(row.get("net_r") or 0.0))
    return {
        key: {
            "n": len(vals),
            "expectancy_r": round(sum(vals) / len(vals), 6) if vals else 0.0,
            "positive_rate": round(sum(1 for x in vals if x > 0) / len(vals), 6) if vals else 0.0,
        }
        for key, vals in groups.items()
    }


def ablation_delta(full_metrics, ablated_metrics):
    full_metrics = dict(full_metrics or {})
    ablated_metrics = dict(ablated_metrics or {})
    def _pf(v):
        return 999.0 if v == "inf" else float(v or 0.0)
    return {
        "expectancy_r": round(float(full_metrics.get("expectancy_r") or 0.0) - float(ablated_metrics.get("expectancy_r") or 0.0), 6),
        "profit_factor": round(_pf(full_metrics.get("profit_factor")) - _pf(ablated_metrics.get("profit_factor")), 6),
        "max_drawdown_r": round(
            abs(float(ablated_metrics.get("max_drawdown_r") or 0.0))
            - abs(float(full_metrics.get("max_drawdown_r") or 0.0)),
            6,
        ),
        "interpretation": "Positive expectancy/PF delta means the removed component likely added value; positive drawdown delta means removing it worsened drawdown.",
    }
