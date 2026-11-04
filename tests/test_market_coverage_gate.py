from src.market_coverage_gate import (
    MarketCoverageError,
    require_operational_quote_coverage,
    validate_operational_quote_coverage,
)


def test_mis_populated_without_valid_last_prices_is_blocked():
    observed = {
        "universe_count": 1985,
        "mis_quote_count": 86,
        "quote_coverage_pct": 4.33,
        "operational_full_market_scan": False,
        "source_health": {
            "official_universe": {"twse": 1092, "tpex": 893},
            "twse_intraday": {"count": 42},
            "tpex_intraday": {"fallback_count": 44},
        },
    }
    out = validate_operational_quote_coverage(observed)
    assert out["status"] == "BLOCKED_QUOTE_COVERAGE"
    assert out["missing_valid_last_trade_count"] == 1899
    assert not out["trading_signal_publication_allowed"]
    try:
        require_operational_quote_coverage(observed)
    except MarketCoverageError as exc:
        assert "4.33%" in str(exc)
    else:
        assert False, "coverage gate must fail closed"


def test_healthy_operational_quotes_can_pass_without_claiming_tpex_certification():
    observed = {
        "universe_count": 1985,
        "mis_quote_count": 1700,
        "quote_coverage_pct": 85.64,
        "operational_full_market_scan": True,
        "source_health": {
            "official_universe": {"twse": 1092, "tpex": 893},
            "twse_intraday": {"count": 950},
            "tpex_intraday": {"fallback_count": 750},
        },
    }
    out = require_operational_quote_coverage(observed)
    assert out["status"] == "PASS"
    assert out["tpex_official_intraday_certified"] is False


def test_flag_missing_even_with_healthy_counts_still_blocks():
    data = {
        "universe_count": 1900,
        "mis_quote_count": 1700,
        "quote_coverage_pct": 89.47,
        "operational_full_market_scan": False,
        "source_health": {
            "official_universe": {"twse": 1050, "tpex": 850},
            "twse_intraday": {"count": 950},
            "tpex_intraday": {"fallback_count": 750},
        },
    }
    assert validate_operational_quote_coverage(data)["status"] == "BLOCKED_QUOTE_COVERAGE"
