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
    assert row["現在動作"] == "觀察"
    assert row["分類"] == "A"
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
    assert row["現在動作"] == "禁止交易"
    assert "已過，不追" in row["買進觸發"]
    assert row["分類"] == "X"
