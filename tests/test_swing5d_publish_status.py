from src.swing5d_publish_status import build_status, COLUMNS


def test_missing_report_is_explicitly_blocked():
    result = build_status(None, 123, "2026-11-10T01:00:00+00:00")
    assert result["status"] == "REPORT_MISSING"
    assert result["preview"] == []
    assert result["production_eligible"] is False


def test_partial_bulk_snapshot_remains_research_only():
    row = {k: "待確認" for k in COLUMNS}
    row["股票代碼"] = "1101"
    payload = {
        "generated_at": "2026-11-10T09:10:00+08:00",
        "market_data_gate": "BLOCKED_EXTERNAL_DATA_NO_TRADE",
        "operational_full_market_scan": False,
        "quote_coverage_pct": 2.77,
        "information_preview_13col": [row],
        "information_count_13col": 1,
    }
    result = build_status(payload, 456)
    assert result["status"] == "BLOCKED_EXTERNAL_DATA"
    assert result["preview"][0]["即時價"] == "待確認"
    assert result["production_eligible"] is False
    assert len(result["information_columns_13col"]) == 13


def test_operational_success_still_does_not_promote_research():
    payload = {
        "operational_full_market_scan": True,
        "quote_scope": "WHOLE_MARKET_EXECUTED_LIVE",
        "market_data_gate": "PASS_OPERATIONAL_WHOLE_MARKET_LIVE_RESEARCH_ONLY",
        "live_market_evidence": {"valid_whole_market_operational": True},
    }
    result = build_status(payload, 789)
    assert result["status"] == "REPORT_READY_RESEARCH_ONLY"
    assert result["trade_decision"] == "禁止新進場、未驗證通過"
    assert result["production_eligible"] is False
