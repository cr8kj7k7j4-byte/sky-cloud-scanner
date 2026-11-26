from src.sky_mobile_table import (
    evidence_scores,
    normalize_mobile_row,
    render_mobile_table,
)


def test_mobile_table_columns_and_action():
    item = {
        "symbol": "9914",
        "name": "測試股",
        "last": 63.4,
        "open": 63.0,
        "change_pct": 1.2,
        "relative_to_market_pct": 0.8,
        "trigger": 63.8,
        "max_entry": 64.1,
        "stop": 63.0,
        "candidate_action": "觀察",
        "classification": "A",
    }
    row = normalize_mobile_row(item)
    assert row["股票"] == "**9914 測試股**"
    assert row["現在動作"] == "**觀察**"
    assert row["分類"] == "**A**"
    assert row["多方評分"] != "—"
    assert "9914" in render_mobile_table([item])


def test_scores_are_missing_when_inputs_insufficient():
    assert evidence_scores({"symbol": "2409"}) == (None, None)


def test_v11_passed_open_window_is_no_chase():
    item = {
        "symbol": "1234",
        "name": "V11",
        "current_price": 52,
        "entry_open": 50,
        "stop": 48,
        "execution_status": "OPEN_ENTRY_PASSED_NO_CHASE",
        "strategy_signal": True,
    }
    row = normalize_mobile_row(item)
    assert row["現在動作"] == "**禁止交易**"
    assert "已過，不追" in row["買進觸發"]
    assert row["分類"] == "**X**"


def test_unified_v13_format():
    item = {
        "symbol": "6770",
        "name": "力積電",
        "last": 69.2,
        "open": 69.5,
        "change_pct": -0.4,
        "relative_to_market_pct": -0.7,
        "bull_score": 37,
        "bear_score": 74,
        "direction": "弱勢反彈",
        "buy_trigger": "站回 69.4～69.5 並守穩，再突破 69.6",
        "max_entry": 69.7,
        "invalidation_text": "跌破 69.0 則續弱",
        "classification": "X",
        "candidate_action": "觀察",
    }
    row = normalize_mobile_row(item)
    assert row["現價"] == "**69.2**"
    assert row["多方評分"] == "**37 / 100**"
    assert row["空方評分"] == "**74 / 100**"
    assert row["買進觸發"] == "**站回 69.4～69.5 並守穩，再突破 69.6**"
    assert row["最高接受價"] == "**69.7**"
    assert row["停損／失效"] == "**跌破 69.0 則續弱**"
    assert row["分類"] == "**X**"
    assert row["現在動作"] == "**觀察**"


def test_general_table_direction_is_bold():
    item = {
        "symbol": "6770",
        "name": "力積電",
        "last": 69.5,
        "direction": "弱勢反彈轉改善",
        "bull_score": 52,
        "bear_score": 60,
        "buy_trigger": "69.5 守穩後，再突破 69.6～69.7",
        "max_entry": 69.8,
        "invalidation_text": "跌回 69.2 以下則反彈失效",
        "classification": "A",
        "candidate_action": "等待",
    }
    row = normalize_mobile_row(item)
    assert row["方向"] == "**弱勢反彈轉改善**"
    assert row["多方評分"] == "**52 / 100**"
    assert row["空方評分"] == "**60 / 100**"
    assert row["買進觸發"] == "**69.5 守穩後，再突破 69.6～69.7**"
    assert row["最高接受價"] == "**69.8**"
    assert row["停損／失效"] == "**跌回 69.2 以下則反彈失效**"
    assert row["分類"] == "**A**"
    assert row["現在動作"] == "**等待**"


def test_partial_market_observation_is_visible_but_never_an_entry_signal():
    item = {
        "symbol": "1234", "name": "局部樣本",
        "last": 42, "open": 41, "change_pct": 2,
        "candidate_scope": "PARTIAL_SAMPLE_OBSERVATION",
        "data_status": "UNVERIFIED_EXECUTED_TRADE",
        "candidate_action": "觀察", "max_entry": 43, "stop": 40,
        "bull_score": 99,
    }
    row = normalize_mobile_row(item)
    assert row["股票"] == "**1234 局部樣本**"
    assert row["現價"] == "—"
    assert row["分類"] == "**X**"
    assert row["現在動作"] == "**觀察**"
    assert row["多方評分"] == "—"
    assert row["最高接受價"] == "—"
    assert row["停損／失效"] == "—"
    assert "禁止新進場" in row["買進觸發"]


def test_manual_position_mobile_adapter_preserves_not_applicable_and_missing_reasons():
    from datetime import datetime, timedelta, timezone
    from src.sky_mobile_table import render_manual_position_report

    tz = timezone(timedelta(hours=8))
    # Anonymous financing fixture: no real portfolio is transmitted or stored.
    result = render_manual_position_report(
        "Sky 持股檢查\\n9999 融資 1,000股 平均成本10.00",
        now=datetime(2026, 11, 27, 10, 30, tzinfo=tz),
    )
    assert result["status"] == "HOLD"
    assert result["source_review"]["reasons"]
    assert result["rows"][0]["買進觸發"] == "不適用（既有持股）"
    assert result["rows"][0]["最高接受價"] == "不適用（既有持股）"
    assert result["rows"][0]["停損／失效"] == "未設定（缺使用者停損）"
    assert result["rows"][0]["現價"] == "—"
    assert result["rows"][0]["多方評分"] == "—"
    assert result["rows"][0]["空方評分"] == "—"
    assert "A2" in result["rows"][0]["欄位缺失原因"]["現價"]
    assert "不適用（既有持股）" in result["markdown"]
    assert result["live_a2_certified"] is False
    assert result["new_entry_allowed"] is False
    assert result["mobile_e2e_verified"] is False
    assert result["github_run_id"] is None
    assert result["automatic_orders"] is False


def test_manual_position_mobile_adapter_rejects_empty_and_incomplete_input():
    from datetime import datetime, timedelta, timezone
    from src.sky_mobile_table import render_manual_position_report

    tz = timezone(timedelta(hours=8))
    result = render_manual_position_report(
        "Sky 持股檢查", now=datetime(2026, 11, 27, tzinfo=tz)
    )
    assert result["status"] == "HOLD"
    assert result["rows"] == []
    assert "缺合格持股輸入" in result["markdown"]
    assert result["action"] == "禁止交易"
