"""W0 #363: dated Swing snapshots are evidence for research, never live trades."""
from copy import deepcopy

from src import official
from src.swing_two_track_acceptance import assess


def _payload(market, dated="2026-11-27"):
    symbol = "1234" if market == "TSE" else "5678"
    return {
        "date": dated,
        "data": [{
            "symbol": symbol, "lastPrice": 23.2,
            "previousClose": 23.0, "tradeVolume": 2000,
            "tradeValue": 50000, "isTrial": False,
        }],
    }


def test_dated_fugle_bulk_requires_explicit_research_opt_in(monkeypatch):
    from src import fugle
    monkeypatch.setattr(fugle, "snapshot_quotes", lambda market: _payload(market))
    universe = [
        {"symbol": "1234", "market": "TSE", "exchange": "TWSE"},
        {"symbol": "5678", "market": "OTC", "exchange": "TPEx"},
    ]
    blocked, warnings = official.fetch_fugle_snapshot_quotes(
        universe, trading_date="2026-11-28"
    )
    assert blocked == []
    assert any("STALE_OR_INVALID" in x for x in warnings)
    rows, warnings = official.fetch_fugle_snapshot_quotes(
        universe, trading_date="2026-11-28", allow_dated_research=True
    )
    assert len(rows) == 2
    assert {x["quote_date"] for x in rows} == {"2026-11-27"}
    assert all(x["quote_source"] == "Fugle bulk snapshot" for x in rows)
    assert any("FUGLE_DATED_RESEARCH_ONLY" in x for x in warnings)


def test_dated_bulk_rejects_future_weekend_and_older_than_seven_days(monkeypatch):
    from src import fugle
    universe = [{"symbol": "1234", "market": "TSE", "exchange": "TWSE"}]
    for source_day in ("2026-11-29", "2026-11-21", "2026-11-19", "invalid"):
        monkeypatch.setattr(fugle, "snapshot_quotes",
                            lambda market, d=source_day: _payload(market, d))
        rows, warnings = official.fetch_fugle_snapshot_quotes(
            universe, trading_date="2026-11-28", allow_dated_research=True
        )
        assert rows == []
        assert any("STALE_OR_INVALID" in x for x in warnings)


def _evidence():
    report = {
        "generated_at": "2026-11-28T01:00:00+08:00",
        "dated_research_source_date": "2026-11-27",
        "dated_research_is_live": False,
        "universe_count": 2,
        "quote_count": 0,
        "candidate_count": 0,
        "snapshot_coverage_pct": 100.0,
        "snapshot_exchange_counts": {"TWSE": 1, "TPEx": 1},
        "unverified_snapshot_observation_count": 2,
        "source_health": {"official_universe": {"twse": 1, "tpex": 1}},
        "operational_full_market_scan": False,
        "market_data_gate": "BLOCKED_EXTERNAL_DATA_NO_TRADE",
        "observations_are_trade_signals": False,
        "snapshot_individual_confirmation": [],
    }
    rows = [
        {"symbol": symbol, "exchange": exchange, "source": "Fugle bulk snapshot",
         "snapshot_date": "2026-11-27",
         "strategy_signal": False, "production_eligible": False,
         "data_status": "UNVERIFIED_EXECUTED_TRADE_TIME",
         "indicative_last_price": 23.2}
        for symbol, exchange in (("1234", "TWSE"), ("5678", "TPEx"))
    ]
    snapshot = {
        "generated_at": "2026-11-28T01:00:00+08:00",
        "source": "Fugle bulk snapshot",
        "observed_symbols": 2,
        "data": rows,
    }
    return report, snapshot


def test_dated_research_is_independent_of_live_and_trading_gates():
    report, snapshot = _evidence()
    result = assess(report, snapshot)
    assert result["snapshot_screen_status"] == "HOLD_SNAPSHOT_EVIDENCE"
    assert result["dated_snapshot_research_status"] == "PASS_DATED_SNAPSHOT_RESEARCH_ONLY"
    assert result["dated_snapshot_source_date"] == "2026-11-27"
    assert result["full_market_execution_certification_status"].startswith("HOLD")
    assert result["candidate_trade_gate"].startswith("HOLD")
    assert result["production_eligible"] is False
    assert result["automatic_order"] is False
    assert result["trade_action"] == "禁止交易"


def test_dated_research_fails_closed_for_untrusted_metadata():
    for change in ("future", "old", "wrong_row_date", "wrong_source", "trial_like",
                   "low_coverage", "wrong_count", "fake_quote", "fake_market",
                   "fake_tradable", "missing_price", "incomplete_capture",
                   "cross_market_mismatch"):
        report, snapshot = deepcopy(_evidence())
        if change == "future":
            report["dated_research_source_date"] = "2026-11-29"
        elif change == "old":
            report["dated_research_source_date"] = "2026-11-19"
        elif change == "wrong_row_date":
            snapshot["data"][0]["snapshot_date"] = "2026-11-26"
        elif change == "wrong_source":
            snapshot["data"][0]["source"] = "UNVERIFIED"
        elif change == "trial_like":
            snapshot["data"][0]["strategy_signal"] = True
        elif change == "low_coverage":
            report["snapshot_coverage_pct"] = 70.0
        elif change == "wrong_count":
            snapshot["observed_symbols"] = 1
        elif change == "fake_quote":
            report["quote_count"] = 2
        elif change == "fake_market":
            report["operational_full_market_scan"] = True
        elif change == "fake_tradable":
            snapshot["data"][0]["production_eligible"] = True
        elif change == "missing_price":
            snapshot["data"][0]["indicative_last_price"] = None
        elif change == "incomplete_capture":
            snapshot["generated_at"] = "2026-11-28T00:50:00+08:00"
        elif change == "cross_market_mismatch":
            snapshot["data"][1]["snapshot_date"] = "2026-11-26"
        assert assess(report, snapshot)["dated_snapshot_research_status"].startswith("HOLD"), change
