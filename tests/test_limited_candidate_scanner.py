"""Safety contracts for limited, prior-session candidate research."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from research.limited_candidate_scanner import build_pool, run

TPE = ZoneInfo("Asia/Taipei")
NOW = datetime(2026, 11, 6, 10, 10, tzinfo=TPE)


def fixtures(date="1151105", num=75):
    twse = [{"Date": date, "Code": str(1101 + i),
             "ClosingPrice": "42.5", "TradeValue": str((num - i) * 1_000_000)}
            for i in range(num)]
    tpex = [{"Date": date, "SecuritiesCompanyCode": str(6101 + i),
             "Close": "43.5", "TransactionAmount": str((num - i) * 800_000)}
            for i in range(num)]
    return twse, tpex


def test_bounded_no_alpha_fabrication():
    twse, tpex = fixtures()
    pool = build_pool(twse, tpex, now=NOW, max_candidates=12)
    assert pool["official_previous_session"] == "2026-11-05"
    assert len(pool["candidates"]) == 12
    assert set(x["exchange"] for x in pool["candidates"]) == {"TWSE", "TPEx"}


def test_stale_or_mixed_official_dates_fail_closed():
    twse, tpex = fixtures()
    tpex[0]["Date"] = "1151104"
    with pytest.raises(ValueError, match="exactly one"):
        build_pool(twse, tpex, now=NOW)
    twse, tpex = fixtures(date="1151106")
    with pytest.raises(ValueError, match="prior-session"):
        build_pool(twse, tpex, now=NOW)
    twse, tpex = fixtures()
    tpex = fixtures(date="1151104")[1]
    with pytest.raises(ValueError, match="dates mismatch"):
        build_pool(twse, tpex, now=NOW)


def test_bound_limit_and_non_stock_are_rejected():
    twse, tpex = fixtures()
    twse[0]["Code"] = "0050"
    twse[1]["ClosingPrice"] = "150"
    twse[2]["TradeValue"] = "-"
    assert build_pool(twse, tpex, now=NOW)["official_market_counts"]["TWSE"] == 72
    with pytest.raises(ValueError, match="bounded"):
        build_pool(twse, tpex, now=NOW, max_candidates=500)


def test_limited_scope_never_claims_full_market_or_buy():
    twse, tpex = fixtures()
    queried = []
    def loader(url):
        return twse if "twse.com.tw" in url else tpex
    def collect(symbol, now):
        queried.append(symbol)
        return {"status": "REALTIME_QUOTE_VERIFIED", "last_price": 42,
                "last_trade_tpe": now.isoformat()}
    report = run(now=NOW, loader=loader, quote_collector=collect, max_candidates=8)
    assert report["data_status"] == "LIMITED_SCOPE_VERIFIED"
    assert report["verified_count"] == 8
    assert len(queried) == 8
    assert report["scope"] == "NOT_FULL_MARKET_LIVE"
    assert report["trading_signal_generated"] is False
    assert report["execution_authorized"] is False
    assert all(not x["execution_authorized"] for x in report["results"])


def test_upstream_error_never_synthesizes_quote():
    report = run(now=NOW, loader=lambda _: (_ for _ in ()).throw(TimeoutError()),
                 quote_collector=lambda *a, **k: None)
    assert report["data_status"] == "BLOCKED"
    assert report["candidate_count"] == 0
    assert not report["results"]
    assert report["trading_signal_generated"] is False


def test_quote_failure_does_not_approve_trade():
    twse, tpex = fixtures()
    report = run(now=NOW, max_candidates=4,
                 loader=lambda url: twse if "twse.com.tw" in url else tpex,
                 quote_collector=lambda symbol, now: {"status": "STALE_QUOTE"})
    assert report["data_status"] == "NO_VALID_SINGLE_QUOTE"
    assert report["verified_count"] == 0
    assert not report["execution_authorized"]


def test_research_schedule_is_separate_and_calendar_gated():
    from pathlib import Path
    workflow = (Path(__file__).resolve().parents[1] /
                ".github/workflows/sky-limited-candidate-research.yml").read_text()
    assert 'cron: "20 1 * * 1-5"' in workflow
    assert "python -m src.trading_calendar" in workflow
    assert "source_status" in workflow
    assert "steps.calendar.outputs.open == 'true'" in workflow
    assert "--max-candidates 12" in workflow
    assert "submit_order" not in workflow
    assert "workflow_dispatch:" in workflow


def test_quote_freshness_uses_each_api_request_time_not_frozen_scan_start():
    from datetime import timedelta
    twse, tpex = fixtures()
    times = iter(NOW + timedelta(seconds=75 * i) for i in range(4))
    visited = []

    def collect(symbol, now):
        visited.append(now)
        # A trade from the query's wall clock is valid; compared with the
        # frozen original NOW, later ones would all appear >=75s future.
        age = (now - (NOW + timedelta(seconds=75 * (len(visited) - 1)))).total_seconds()
        return {"status": "REALTIME_QUOTE_VERIFIED" if abs(age) <= 30
                else "FUTURE_QUOTE_TIMESTAMP", "last_price": 45.0}

    result = run(
        now=NOW, max_candidates=4,
        loader=lambda url: twse if "twse.com.tw" in url else tpex,
        quote_collector=collect, quote_clock=lambda: next(times),
    )
    assert result["verified_count"] == 4
    assert len(visited) == 4
    assert visited[3] > visited[0]
    assert not result["execution_authorized"]
