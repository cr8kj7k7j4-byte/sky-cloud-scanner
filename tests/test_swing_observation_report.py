from src.swing_observation_report import HEADERS, observation_rows, render


def test_thirteen_columns_and_missing_levels_are_explicit():
    report = {
        "generated_at": "2026-11-09T11:25:00+08:00",
        "official_daily_signal_date": "2026-11-06",
        "official_daily_count": 1964, "universe_count": 1983,
        "official_daily_coverage_pct": 99.04,
        "live_quote_available": 1, "live_quote_requested": 1,
        "daily_scope_status": "PASS_DAILY_CROSS_SECTION",
        "candidates": [{
            "symbol": "3576", "name": "測試股票", "close": 17.8,
            "current_price": 18.2, "current_price_updated_at": "2026-11-09T11:24:55+08:00",
            "live_quote_status": "FRESH_DATE_AND_TIMESTAMP_VERIFIED",
            "current_price_source": "Fugle single-symbol intraday",
            "classification": "研究觀察／未評級",
            "direction": "待確認",
            "invalidation_text": "正式 V1.1 訊號日期未驗證",
        }],
    }
    rows = observation_rows(report)
    assert len(HEADERS) == 13
    assert len(rows) == 1 and len(rows[0]) == 13
    assert rows[0][0:3] == ["3576", "測試股票", 18.2]
    assert rows[0][5:9] == [None, None, None, None]
    output = render(report)
    assert "股票名稱" in output and "加碼價格" in output and "停利價格" in output
    assert "3576 | 測試股票 | 18.2" in output
    assert "未通過正式進場資格" in output


def test_stale_execution_quote_is_not_displayed_as_live_price():
    report = {"candidates": [{"symbol": "9999", "current_price": 30,
                              "live_quote_status": "STALE_OR_FUTURE_TIMESTAMP"}]}
    assert observation_rows(report)[0][2] is None
    assert "—" in render(report)


def test_empty_candidate_table_is_still_13_columns():
    report = {"candidates": [], "daily_scope_status": "DATA_BLOCKED"}
    output = render(report)
    assert "無候選" in output
    assert len([x for x in output.splitlines() if x.startswith("| ")][0].split("|")) == 15
