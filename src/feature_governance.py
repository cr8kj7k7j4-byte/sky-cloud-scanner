def feature_decision(
    *,
    expectancy_contribution,
    profit_factor_contribution,
    drawdown_protection,
    regime_consistent=False,
    walk_forward_consistent=False,
    min_expectancy=0.0,
):
    """
    Governance decision for research features/rules.
    This is not a trading signal and not a probability.
    """
    exp = float(expectancy_contribution or 0.0)
    pf = float(profit_factor_contribution or 0.0)
    dd = float(drawdown_protection or 0.0)

    if (
        exp > min_expectancy
        and (pf > 0 or dd > 0)
        and regime_consistent
        and walk_forward_consistent
    ):
        status = "KEEP"
    elif exp < 0 and pf < 0 and dd < 0:
        status = "PRUNE_CANDIDATE"
    else:
        status = "RESEARCH_MORE"

    return {
        "status": status,
        "expectancy_contribution": exp,
        "profit_factor_contribution": pf,
        "drawdown_protection": dd,
        "regime_consistent": bool(regime_consistent),
        "walk_forward_consistent": bool(walk_forward_consistent),
        "note": (
            "KEEP requires cross-regime and walk-forward consistency. "
            "Importance alone cannot justify production changes."
        ),
    }


def rule_ablation_decision(full_metrics, without_rule_metrics, **kwargs):
    def pf(v):
        return 999.0 if v == "inf" else float(v or 0.0)

    exp = float(full_metrics.get("net_expectancy_pct") or 0.0) - float(
        without_rule_metrics.get("net_expectancy_pct") or 0.0
    )
    pfd = pf(full_metrics.get("profit_factor")) - pf(
        without_rule_metrics.get("profit_factor")
    )
    dd = abs(float(without_rule_metrics.get("max_drawdown_pct") or 0.0)) - abs(
        float(full_metrics.get("max_drawdown_pct") or 0.0)
    )
    return feature_decision(
        expectancy_contribution=exp,
        profit_factor_contribution=pfd,
        drawdown_protection=dd,
        **kwargs,
    )
