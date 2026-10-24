from src.evidence_ledger import build_evidence_ledger
from src.market_intelligence import summarize_market
from src.relative_strength import apply_relative_strength
from src.event_risk import assess_event_risk


def test_market_intelligence_breadth():
    rows = [
        {"symbol": "1", "change_pct": 2.0, "trade_value": 100},
        {"symbol": "2", "change_pct": 1.0, "trade_value": 90},
        {"symbol": "3", "change_pct": -0.5, "trade_value": 80},
    ]
    out = summarize_market(rows)
    assert out["status"] == "OK"
    assert out["advancers"] == 2
    assert out["market_bias"] in {"BULLISH", "NEUTRAL"}


def test_relative_strength_grouped():
    rows = [
        {"symbol": "A", "exchange": "TWSE", "change_pct": 3.0},
        {"symbol": "B", "exchange": "TWSE", "change_pct": 1.0},
    ]
    out = apply_relative_strength(rows)
    by_symbol = {x["symbol"]: x for x in out}
    assert by_symbol["A"]["relative_strength_score"] == 1.0
    assert by_symbol["B"]["relative_strength_score"] == -1.0


def test_evidence_ledger_separates_facts_and_derived():
    row = {
        "symbol": "2409",
        "last": 37.0,
        "change_pct": 1.2,
        "volume": 1000,
        "quote_source": "TWSE MIS",
        "quote_time": "10:15:00",
        "universe_source": "TWSE OpenAPI",
        "relative_strength_score": 0.8,
    }
    ledger = build_evidence_ledger(row, "2026-10-24T10:15:00+08:00")
    assert ledger["fact_count"] >= 4
    assert ledger["derived_count"] == 1


def test_event_risk_unknown_is_not_safe():
    out = assess_event_risk([])
    assert out["level"] == "UNKNOWN"
    assert out["action"] == "VERIFY_BEFORE_TRADE"


def test_event_risk_high():
    out = assess_event_risk([{"type": "CPI", "active": True}])
    assert out["level"] == "HIGH"
    assert out["action"] == "REDUCE_OR_BLOCK"
