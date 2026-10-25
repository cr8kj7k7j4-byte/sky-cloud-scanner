from src.decision_engine import first_gate, spread_pct
from src.feature_engine import enrich_candidate_context
from src.ranking_engine import screening_rank_score
from src.sky_rules import (
    first_gate as legacy_first_gate,
    spread_pct as legacy_spread_pct,
    score_for_ranking,
    enrich,
)


def test_first_gate_legacy_alias_matches_p0c():
    row = {
        "last": 50.0,
        "volume": 5000,
        "trade_value": 250_000_000,
        "bid": 49.9,
        "ask": 50.0,
    }
    assert legacy_first_gate(row) == first_gate(row)
    assert legacy_spread_pct(row) == spread_pct(row)


def test_ranking_alias_matches_p0o():
    row = {"change_pct": 3.0, "trade_value": 50_000_000, "volume": 5000}
    assert score_for_ranking(row) == screening_rank_score(row)


def test_enrich_alias_matches_p0f():
    row = {"symbol": "TEST"}
    ticker = {
        "canDayTrade": True,
        "canBuyDayTrade": True,
        "limitUpPrice": 12.0,
        "industry": "TEST",
    }
    quote = {
        "avgPrice": 10.0,
        "closePrice": 10.5,
        "highPrice": 10.6,
        "lowPrice": 9.9,
        "total": {"tradeVolume": 1000},
    }
    candles = {
        "data": [
            {"close": 10.0, "volume": 100},
            {"close": 10.5, "volume": 200},
        ]
    }
    assert enrich(row, ticker, quote, candles) == enrich_candidate_context(
        row, ticker, quote, candles
    )


def test_enrichment_preserves_rejection_flags():
    out = enrich_candidate_context(
        {"symbol": "TEST"},
        {"canDayTrade": False, "limitUpPrice": 10.5},
        {"closePrice": 10.5, "avgPrice": 10.0, "total": {"tradeVolume": 100}},
        {"data": []},
    )
    assert "X:漲停" in out["flags"]
    assert "X:不可當沖" in out["flags"]
