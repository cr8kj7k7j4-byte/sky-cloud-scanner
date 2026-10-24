def shadow_promotion_gate(
    metrics,
    *,
    min_trades=100,
    min_expectancy_r=0.0,
    min_profit_factor=1.0,
    max_drawdown_r=10.0,
    max_mae_r_p95=1.5,
    min_regime_coverage=2,
    monitoring_clean=False,
    data_quality_clean=False,
):
    m = dict(metrics or {})
    checks = {
        "sample_size": int(m.get("trades") or 0) >= int(min_trades),
        "expectancy": float(m.get("expectancy_r") or 0.0) > float(min_expectancy_r),
        "profit_factor": float(m.get("profit_factor") or 0.0) > float(min_profit_factor),
        "drawdown": abs(float(m.get("max_drawdown_r") or 0.0)) <= abs(float(max_drawdown_r)),
        "mae_tail": float(m.get("mae_r_p95") or 999.0) <= float(max_mae_r_p95),
        "regime_coverage": int(m.get("regime_count") or 0) >= int(min_regime_coverage),
        "monitoring_clean": bool(monitoring_clean),
        "data_quality_clean": bool(data_quality_clean),
    }
    failed = [k for k,v in checks.items() if not v]
    return {
        "shadow_passed": not failed,
        "production_eligible": False,
        "checks": checks,
        "failed_checks": failed,
        "note": (
            "Passing shadow trading only permits governance review. "
            "It does not authorize live trading or production promotion."
        ),
    }
