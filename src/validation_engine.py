from dataclasses import dataclass, asdict
from math import isfinite


@dataclass(frozen=True)
class CostScenario:
    name: str
    round_trip_cost_pct: float
    slippage_pct: float

    def to_dict(self):
        return asdict(self)


DEFAULT_COST_SCENARIOS = [
    CostScenario("BASE", 0.45, 0.05),
    CostScenario("STRESS_1", 0.60, 0.10),
    CostScenario("STRESS_2", 0.80, 0.15),
]


def net_return_pct(gross_return_pct, scenario):
    s = scenario if isinstance(scenario, CostScenario) else CostScenario(**scenario)
    return float(gross_return_pct) - s.round_trip_cost_pct - s.slippage_pct


def cost_stress_report(gross_returns_pct, scenarios=None):
    scenarios = scenarios or DEFAULT_COST_SCENARIOS
    vals = [float(x) for x in gross_returns_pct if x is not None and isfinite(float(x))]
    rows = []
    for s in scenarios:
        nets = [net_return_pct(x, s) for x in vals]
        expectancy = sum(nets) / len(nets) if nets else 0.0
        win_rate = sum(1 for x in nets if x > 0) / len(nets) if nets else 0.0
        rows.append({
            "scenario": s.name,
            "round_trip_cost_pct": s.round_trip_cost_pct,
            "slippage_pct": s.slippage_pct,
            "n": len(nets),
            "net_expectancy_pct": round(expectancy, 6),
            "net_positive_rate": round(win_rate, 6),
            "passed": bool(nets and expectancy > 0),
        })
    return {
        "scenarios": rows,
        "passed": bool(rows) and all(x["passed"] for x in rows),
        "note": "Stress pass requires positive net expectancy in every configured scenario.",
    }


def leakage_audit(feature_columns, target_columns, metadata=None):
    features = set(feature_columns or [])
    targets = set(target_columns or [])
    metadata = metadata or {}

    overlaps = sorted(features & targets)
    suspicious = sorted(
        x for x in features
        if any(token in x.lower() for token in ("future", "forward", "target", "label", "mfe", "mae"))
    )
    timestamp_order_ok = bool(metadata.get("timestamp_order_ok", False))
    survivorship_reviewed = bool(metadata.get("survivorship_reviewed", False))

    passed = not overlaps and not suspicious and timestamp_order_ok and survivorship_reviewed
    return {
        "passed": passed,
        "feature_target_overlap": overlaps,
        "suspicious_feature_names": suspicious,
        "timestamp_order_ok": timestamp_order_ok,
        "survivorship_reviewed": survivorship_reviewed,
    }


def regime_bucket(market_return_pct=None, volatility_pct=None):
    mr = float(market_return_pct or 0.0)
    vol = abs(float(volatility_pct or 0.0))
    if mr >= 1.0:
        trend = "BULL"
    elif mr <= -1.0:
        trend = "BEAR"
    else:
        trend = "NEUTRAL"

    if vol >= 2.5:
        vol_state = "HIGH"
    elif vol >= 1.0:
        vol_state = "MEDIUM"
    else:
        vol_state = "LOW"
    return f"{trend}_{vol_state}"


def aggregate_by_regime(records):
    groups = {}
    for row in records or []:
        key = row.get("regime") or regime_bucket(
            row.get("market_return_pct"), row.get("volatility_pct")
        )
        groups.setdefault(key, []).append(float(row.get("net_r") or 0.0))

    out = {}
    for key, vals in groups.items():
        out[key] = {
            "n": len(vals),
            "expectancy_r": round(sum(vals) / len(vals), 6) if vals else 0.0,
            "positive_rate": round(sum(1 for x in vals if x > 0) / len(vals), 6) if vals else 0.0,
        }
    return out


def ablation_delta(full_metrics, ablated_metrics):
    keys = ("expectancy_r", "profit_factor", "max_drawdown_r")
    delta = {}
    for key in keys:
        full = float(full_metrics.get(key) or 0.0)
        ablated = float(ablated_metrics.get(key) or 0.0)
        if key == "max_drawdown_r":
            delta[key] = round(abs(ablated) - abs(full), 6)
        else:
            delta[key] = round(full - ablated, 6)
    delta["interpretation"] = (
        "Positive expectancy/PF delta means the removed component likely added value; "
        "positive drawdown delta means removing it worsened drawdown."
    )
    return delta
