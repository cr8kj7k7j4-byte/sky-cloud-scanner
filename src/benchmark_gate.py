def _finite_pf(value):
    if value == "inf":
        return 999.0
    return float(value or 0.0)


def benchmark_gate(
    oos_metrics,
    *,
    walk_forward_passed=False,
    cost_stress_passed=False,
    leakage_check_passed=False,
    survivorship_reviewed=False,
    regime_robustness_passed=False,
    paper_trade_passed=False,
    min_expectancy_pct=0.0,
    min_profit_factor=1.0,
    max_drawdown_pct=20.0,
):
    m = dict(oos_metrics or {})
    expectancy = float(m.get("net_expectancy_pct") or 0.0)
    pf = _finite_pf(m.get("profit_factor"))
    mdd = abs(float(m.get("max_drawdown_pct") or 0.0))

    checks = {
        "positive_net_expectancy": expectancy > min_expectancy_pct,
        "profit_factor": pf > min_profit_factor,
        "max_drawdown": mdd <= max_drawdown_pct,
        "walk_forward": bool(walk_forward_passed),
        "cost_stress": bool(cost_stress_passed),
        "leakage_check": bool(leakage_check_passed),
        "survivorship_review": bool(survivorship_reviewed),
        "regime_robustness": bool(regime_robustness_passed),
        "paper_trade": bool(paper_trade_passed),
    }

    failed = [name for name, ok in checks.items() if not ok]
    return {
        "production_eligible": not failed,
        "checks": checks,
        "failed_checks": failed,
        "note": "Eligibility is a governance gate, not a profit guarantee.",
    }
