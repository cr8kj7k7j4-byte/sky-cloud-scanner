from src.swing5d_information_table import (
    COLUMNS, build_swing5d_13col_rows, render_swing5d_13col_table,
)


def test_unverified_snapshot_price_is_not_live_price():
    obs = [{"symbol": "1234", "name": "測試", "indicative_last_price": 42.5,
            "source": "Fugle bulk snapshot"}]
    rows = build_swing5d_13col_rows(obs, [])
    assert len(COLUMNS) == 13
    assert rows[0]["即時價"] == "待確認"
    assert rows[0]["最近觀察價（未驗證成交時間）"] == 42.5
    assert rows[0]["正式交易資格"] is False
    assert rows[0]["買進觸發"] == "待確認"
    assert rows[0]["現在動作"] == "等待"
    assert "股票代碼" in render_swing5d_13col_table(rows)


def test_verified_individual_quote_is_visible_without_strategy_approval():
    obs = [{"symbol": "1234", "name": "測試", "indicative_last_price": 42.5}]
    confirms = [{"symbol": "1234", "verified_executed_price": 42.6,
                 "verified_executed_at": "2026-11-09T11:48:06+08:00",
                 "data_status": "FRESH_EXECUTED_TRADE", "source": "Fugle individual"}]
    rows = build_swing5d_13col_rows(obs, confirms)
    assert rows[0]["即時價"] == 42.6
    assert rows[0]["現在動作"] == "觀察"
    assert rows[0]["正式交易資格"] is False
    assert rows[0]["多方評分"] == "—"
    assert rows[0]["停利價格"] == "待確認"


def test_table_has_placeholder_when_no_data():
    table = render_swing5d_13col_table([])
    assert "暫無可驗證觀察" in table
    assert table.count("|") >= 42
