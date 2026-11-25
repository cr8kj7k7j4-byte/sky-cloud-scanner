"""Regression: no-price zero-volume is a complete QUERY, never a trade."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.sky_full_universe_information import (
    build, RESEARCH_EXCLUDED_TIB_SYMBOLS,
)
from research.sky_query_validity import apply_query_validity


NOW = datetime(2026, 11, 26, 10, 15, tzinfo=ZoneInfo("Asia/Taipei"))
MARKET = [
    {"symbol": "2237", "exchange": "TWSE", "name": "Excluded TIB"},
    {"symbol": "2330", "exchange": "TWSE", "name": "Priced"},
    {"symbol": "6488", "exchange": "TPEx", "name": "No transactions"},
]
assert "2237" in RESEARCH_EXCLUDED_TIB_SYMBOLS


def _snapshot(date, *, volume=0):
    return {
        "TSE": {"date": date, "data": [
            {"symbol": "2237", "lastPrice": 19.0, "tradeVolume": 5},
            {"symbol": "2330", "lastPrice": 25.0, "tradeVolume": 50},
        ]},
        "OTC": {"date": date, "data": [
            {"symbol": "6488", "lastPrice": None, "tradeVolume": volume},
        ]},
    }


def test_intraday_all_official_stocks_queried_but_exclusions_not_ranked():
    result = build(MARKET, _snapshot(NOW.date().isoformat()), NOW,
                   excluded_research_symbols=["2237"])
    assert result["universe_count"] == 3
    assert result["official_universe_count_before_research_exclusion"] == 3
    assert result["research_universe_count"] == 2
    assert result["excluded_research_symbol_count"] == 1
    assert result["information_query_valid_count"] == 3
    assert result["information_query_with_price_count"] == 2
    assert result["information_query_zero_volume_no_price_count"] == 1
    assert result["information_query_valid_pct_official"] == 100.0
    assert result["information_query_full_universe_complete"] is True
    excluded = result["all_symbols"][0]
    assert excluded["excluded_from_research_ranking"] is True
    assert all(x["symbol"] != "2237" for x in result["ranked_observations"])
    row = result["all_symbols"][2]
    assert row["information_query_status"] == "VALID_QUERY_ZERO_REPORTED_VOLUME_NO_PRICE"
    assert row["information_query_valid"] is True
    assert row["information_observed_price_valid"] is False
    assert row["information_executed_trade_certified_by_query"] is False
    assert row["last_price"] is None
    assert row["required_fields"]["即時價"] is None
    assert row["trade_signal"] is False
    assert row["production_eligible"] is False
    assert result["quote_execution_certified_count"] == 0


def test_earlier_snapshot_allowed_only_for_postmarket_information():
    yesterday = (NOW.date() - timedelta(days=1)).isoformat()
    result = build(MARKET, _snapshot(yesterday), NOW,
                   excluded_research_symbols=["2237"])
    assert result["information_query_valid_count"] == 0
    assert result["information_query_full_universe_complete"] is False
    post = apply_query_validity(result, mode="POSTMARKET_RESEARCH_ONLY")
    assert post["information_query_valid_count"] == 3
    assert post["information_query_full_universe_complete"] is True
    assert post["fresh_executed_count"] == 0


def test_no_row_not_a_valid_zero_volume_query():
    snapshots = _snapshot(NOW.date().isoformat())
    snapshots["OTC"]["data"] = []
    report = build(MARKET, snapshots, NOW)
    assert report["information_query_valid_count"] == 2
    assert report["information_query_hold_count"] == 1
    assert report["information_query_full_universe_complete"] is False
    assert report["all_symbols"][-1]["volume"] is None


def test_no_price_unknown_bool_or_positive_volume_stays_hold():
    for volume in (None, False, True, 5):
        report = build(MARKET, _snapshot(NOW.date().isoformat(), volume=volume),
                       NOW)
        assert report["information_query_zero_volume_no_price_count"] == 0
        assert report["information_query_valid_count"] == 2
        assert report["information_query_full_universe_complete"] is False


def test_trial_or_future_date_or_missing_provider_market_stays_hold():
    for invalid in ("trial", "future", "missing_provider"):
        snapshots = _snapshot(NOW.date().isoformat())
        if invalid == "trial":
            snapshots["OTC"]["data"][0]["isTrial"] = True
        elif invalid == "future":
            snapshots["OTC"]["date"] = (NOW.date() + timedelta(days=1)).isoformat()
        else:
            snapshots.pop("OTC")
        report = build(MARKET, snapshots, NOW)
        assert report["information_query_zero_volume_no_price_count"] == 0
        assert report["information_query_full_universe_complete"] is False


def test_no_data_never_fakes_full_universe():
    report = build(MARKET, {}, NOW, excluded_research_symbols=["2237"])
    assert report["information_query_valid_count"] == 0
    assert report["information_query_hold_count"] == 3
    assert report["information_query_official_denominator"] == 3
    assert report["information_query_full_universe_complete"] is False
