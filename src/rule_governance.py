CORE_RULES = {
    "market_gate",
    "sector_rs_gate",
    "anti_chase_gate",
    "phase_gate",
    "setup_gate",
    "trigger_gate",
    "rr_gate",
}


def rule_governance_decision(
    rule,
    *,
    expectancy_contribution,
    profit_factor_contribution,
    drawdown_protection,
    regime_consistent=False,
    walk_forward_consistent=False,
    sample_sufficient=False,
):
    if rule not in CORE_RULES:
        raise ValueError(f"unknown rule: {rule}")

    exp = float(expectancy_contribution or 0.0)
    pf = float(profit_factor_contribution or 0.0)
    dd = float(drawdown_protection or 0.0)

    if (
        exp > 0
        and (pf > 0 or dd > 0)
        and regime_consistent
        and walk_forward_consistent
        and sample_sufficient
    ):
        status = "KEEP"
    elif exp < 0 and pf < 0 and dd < 0 and sample_sufficient:
        status = "PRUNE_CANDIDATE"
    else:
        status = "RESEARCH_MORE"

    return {
        "rule": rule,
        "status": status,
        "expectancy_contribution": exp,
        "profit_factor_contribution": pf,
        "drawdown_protection": dd,
        "regime_consistent": bool(regime_consistent),
        "walk_forward_consistent": bool(walk_forward_consistent),
        "sample_sufficient": bool(sample_sufficient),
        "production_change_allowed": False,
        "note": (
            "Ablation is evidence, not automatic production authority. "
            "Any rule change requires complete revalidation and governance approval."
        ),
    }
