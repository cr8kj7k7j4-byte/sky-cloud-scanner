def challenger_review(
    comparison,
    *,
    min_events=100,
    min_expectancy_delta=0.0,
    min_pf_delta=0.0,
    require_regime_consistency=True,
    regime_comparisons=None,
    max_false_breakout_increase=0,
    max_missed_opportunity_increase=0,
):
    c=comparison.get("champion",{})
    q=comparison.get("challenger",{})
    d=comparison.get("delta",{})

    checks={
        "sample_size": int(q.get("events") or 0) >= int(min_events),
        "expectancy_delta": float(d.get("expectancy_r") or 0.0) > float(min_expectancy_delta),
        "pf_delta": float(d.get("profit_factor") or 0.0) > float(min_pf_delta),
        "false_breakout_control": int(d.get("false_breakouts") or 0) >= -int(max_false_breakout_increase),
        "missed_opportunity_control": int(d.get("missed_opportunities") or 0) >= -int(max_missed_opportunity_increase),
    }

    regime_ok=True
    if require_regime_consistency:
        comps=regime_comparisons or {}
        eligible=[]
        for _,item in comps.items():
            ch=item.get("challenger",{})
            delta=item.get("delta",{})
            if int(ch.get("events") or 0) >= max(10,int(min_events*0.1)):
                eligible.append(float(delta.get("expectancy_r") or 0.0) > 0)
        regime_ok=bool(eligible) and sum(eligible)/len(eligible) >= 0.67
    checks["regime_consistency"]=regime_ok

    failed=[k for k,v in checks.items() if not v]
    return {
        "governance_review_ready": not failed,
        "automatic_promotion_allowed": False,
        "checks": checks,
        "failed_checks": failed,
        "note": (
            "Passing this review only permits human/governance evaluation. "
            "Champion replacement is never automatic."
        ),
    }
