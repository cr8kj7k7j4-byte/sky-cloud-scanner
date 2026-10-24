from research.opportunity_ranking import rank_snapshot


def test_ranking_prefers_stronger_positive_features():
    rows = [
        {
            "symbol": "AAA",
            "gate_pass": "true",
            "intraday_momentum": "10",
            "market_relative_strength": "10",
            "net_rr": "2.5",
            "anti_chase_risk": "1",
            "liquidity_slippage_risk": "1",
        },
        {
            "symbol": "BBB",
            "gate_pass": "true",
            "intraday_momentum": "5",
            "market_relative_strength": "5",
            "net_rr": "1.6",
            "anti_chase_risk": "5",
            "liquidity_slippage_risk": "5",
        },
    ]

    ranked = rank_snapshot(rows)
    assert ranked[0]["symbol"] == "AAA"
    assert ranked[0]["opportunity_rank"] == 1
    assert ranked[0]["opportunity_score"] > ranked[1]["opportunity_score"]


def test_failed_gate_is_excluded():
    rows = [
        {"symbol": "AAA", "gate_pass": "false", "intraday_momentum": "100"},
        {"symbol": "BBB", "gate_pass": "true", "intraday_momentum": "1"},
    ]

    ranked = rank_snapshot(rows)
    assert [x["symbol"] for x in ranked] == ["BBB"]


def test_score_is_relative_not_probability_contract():
    rows = [
        {"symbol": "AAA", "gate_pass": "true", "intraday_momentum": "10"},
        {"symbol": "BBB", "gate_pass": "true", "intraday_momentum": "5"},
        {"symbol": "CCC", "gate_pass": "true", "intraday_momentum": "1"},
    ]

    ranked = rank_snapshot(rows)
    assert ranked[0]["opportunity_score"] == 100.0
    assert ranked[-1]["opportunity_score"] == 0.0
