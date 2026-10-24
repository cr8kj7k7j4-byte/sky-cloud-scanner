def stability_governance(
    rule,
    *,
    fold_positive_share,
    regime_positive_share,
    sample_n,
    min_sample_n=30,
    min_fold_share=0.67,
    min_regime_share=0.67,
):
    fold_share = float(fold_positive_share or 0.0)
    regime_share = float(regime_positive_share or 0.0)
    sample_n = int(sample_n or 0)

    if (
        sample_n >= min_sample_n
        and fold_share >= min_fold_share
        and regime_share >= min_regime_share
    ):
        status = "STABLE_KEEP_CANDIDATE"
    elif sample_n < min_sample_n:
        status = "INSUFFICIENT_SAMPLE"
    else:
        status = "MIXED_RESEARCH_MORE"

    return {
        "rule": rule,
        "status": status,
        "fold_positive_share": fold_share,
        "regime_positive_share": regime_share,
        "sample_n": sample_n,
        "production_change_allowed": False,
        "note": (
            "Stable contribution is necessary but not sufficient. Production changes "
            "still require full backtest, cost stress, OOS and paper trading."
        ),
    }
