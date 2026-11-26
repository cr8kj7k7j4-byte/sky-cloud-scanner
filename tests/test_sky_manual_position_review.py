"""W0 #363: manual holdings only, with injected synthetic quote evidence (zero API)."""
from datetime import datetime, timezone, timedelta

from src.sky_manual_position_review import parse_manual_positions, review_manual_positions

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 27, 10, 30, tzinfo=TPE)
TEXT = "Sky 持股檢查\n2330 1張 成本850 停損820"


def account():
    return {
        "account_equity": 500000, "daily_pnl": -1000,
        "open_risk": 4000, "concurrent_positions": 1,
        "correlated_open_risk": 0, "drawdown_pct": 0.0,
        "consecutive_losses": 0,
    }


def quote(price=835):
    return {
        "symbol": "2330", "source": "Fugle MarketData API /intraday/quote",
        "status": "PRICE_CAP_EXCEEDED", "executed_trade_verified": False,
        "position_trade_observed": True, "last_trade_price": price,
        "last_price": price, "quote_date": "2026-11-27",
        "last_trade_tpe": datetime(2026, 11, 27, 10, 29, tzinfo=TPE).isoformat(),
    }


def test_parse_quantity_units_and_missing_stop():
    result = parse_manual_positions("Sky 持股檢查\n2330 1張 成本850 停損820\n2317 2,000股 均價105")
    assert result["status"] == "PASS_INPUT"
    assert result["positions"][0]["shares"] == 1000
    assert result["positions"][1]["shares"] == 2000
    assert result["positions"][1]["stop"] is None


def test_never_assume_missing_holdings_or_account_are_zero():
    result = review_manual_positions("Sky 持股檢查", now=NOW)
    assert result["status"] == "HOLD"
    assert "MISSING_POSITIONS" in result["reasons"]
    assert "HOLD_MISSING_ACCOUNT_CONTEXT" in result["reasons"]
    assert result["risk_total_twd"] is None
    assert result["new_entry_allowed"] is False


def test_quote_provenance_required_and_gross_pnl_not_net():
    rejected = review_manual_positions(TEXT, quotes={"2330": {
        **quote(), "position_trade_observed": False,
    }}, account_context=account(), now=NOW)
    assert rejected["rows"][0]["現價"] is None
    assert rejected["rows"][0]["未實現毛損益"] is None
    assert rejected["status"] == "HOLD"
    accepted = review_manual_positions(TEXT, quotes={"2330": quote()},
                                       account_context=account(), now=NOW)
    row = accepted["rows"][0]
    assert row["現價"] == 835
    assert row["未實現毛損益"] == -15000
    assert row["目前價至停損風險"] == 15000
    assert row["費稅後淨損益"] is None
    assert accepted["new_entry_allowed"] is False
    assert accepted["schema"] == "SKY_MOBILE_TABLE_V1_0"


def test_stop_breach_is_manual_stop_only():
    result = review_manual_positions(TEXT, quotes={"2330": quote(810)},
                                     account_context=account(), now=NOW)
    assert result["rows"][0]["現在動作"] == "停損"
    assert result["rows"][0]["分類"] == "X"
    assert result["automatic_orders"] is False
    assert result["production_eligible"] is False


def test_hold_on_stale_quote_and_unknown_stop():
    stale = {**quote(), "last_trade_tpe": "2026-11-26T10:29:00+08:00"}
    result = review_manual_positions("2330 1000股 成本850",
                                     quotes={"2330": stale},
                                     account_context=account(), now=NOW)
    assert result["rows"][0]["現價"] is None
    assert "HOLD_STOP_2330" in result["reasons"]
    assert "HOLD_A2_EXECUTED_TRADE_2330" in result["reasons"]


def test_invalid_duplicate_negative_or_unknown_input_rejected():
    duplicated = parse_manual_positions("2330 1張 成本850\n2330 2張 成本820")
    assert "DUPLICATE_SYMBOL" in duplicated["errors"]
    assert parse_manual_positions("2330 0股 成本850")["status"] == "HOLD_POSITION_INPUT"
    assert parse_manual_positions("2330 1000股 成本0")["status"] == "HOLD_POSITION_INPUT"
    assert parse_manual_positions("2330 1000股 成本850亂碼")["status"] == "HOLD_POSITION_INPUT"
    assert parse_manual_positions("2330 1張 成本850\n2317 1張 成本100\n2303 1張 成本30\n2882 1張 成本40")["status"] == "HOLD_POSITION_INPUT"


def test_account_limits_and_nonfinite_values_fail_closed():
    broken = account()
    broken.pop("daily_pnl")
    r = review_manual_positions(TEXT, quotes={"2330": quote()},
                                account_context=broken, now=NOW)
    assert "daily_pnl" in r["missing_account_fields"]
    assert r["new_entry_allowed"] is False
    invalid = account()
    invalid["open_risk"] = float("nan")
    r = review_manual_positions(TEXT, quotes={"2330": quote()},
                                account_context=invalid, now=NOW)
    assert "open_risk" in r["invalid_account_fields"]
    lost = account()
    lost["daily_pnl"] = -10000
    lost["consecutive_losses"] = 2
    r = review_manual_positions(TEXT, quotes={"2330": quote()},
                                account_context=lost, now=NOW)
    assert "DAILY_LOSS_LOCKDOWN" in r["reasons"]
    assert "TWO_CONSECUTIVE_STOPS" in r["reasons"]


def test_market_snapshot_time_never_becomes_execution_time():
    observed = {**quote(), "source": "FUGLE_PAID_SNAPSHOT"}
    observed.pop("last_trade_tpe")
    observed["last_updated_tpe"] = NOW.isoformat()
    r = review_manual_positions(TEXT, quotes={"2330": observed},
                                account_context=account(), now=NOW)
    assert r["rows"][0]["現價"] is None
    assert r["status"] == "HOLD"


def test_inline_manual_command_and_non_daytrade_holding_quote():
    parsed = parse_manual_positions("Sky 持股檢查 2330 1張 成本850 停損820")
    assert parsed["status"] == "PASS_INPUT"
    result = review_manual_positions("Sky 持股檢查 2330 1張 成本850 停損820",
                                     quotes={"2330": quote(860)},
                                     account_context=account(), now=NOW)
    assert result["rows"][0]["現價"] == 860
    assert result["rows"][0]["未實現毛損益"] == 10000
    assert result["new_entry_allowed"] is False


def test_lastprice_fallback_does_not_certify_holding_execution():
    observed = {**quote(), "last_trade_price": None, "last_price": 860}
    result = review_manual_positions(TEXT, quotes={"2330": observed},
                                     account_context=account(), now=NOW)
    assert result["rows"][0]["現價"] is None
    assert result["status"] == "HOLD"


def test_single_position_1r_limit_is_reported():
    result = review_manual_positions(TEXT, quotes={"2330": quote()},
                                     account_context=account(), now=NOW)
    assert "SINGLE_POSITION_RISK_EXCEEDED_2330" in result["reasons"]


def test_manual_average_cost_with_spaces_supported():
    parsed = parse_manual_positions("Sky 持股檢查\n2330 1 張 平均成本 850 停損 820")
    assert parsed["status"] == "PASS_INPUT"
    assert parsed["positions"][0]["shares"] == 1000
    assert parsed["positions"][0]["average_cost"] == 850


def test_existing_holding_not_applicable_buying_and_independent_gross_pnl():
    unknown_account = review_manual_positions(
        TEXT, quotes={"2330": quote(835)}, now=NOW
    )
    row = unknown_account["rows"][0]
    assert row["買進觸發"] == "不適用（既有持股）"
    assert row["最高接受價"] == "不適用（既有持股）"
    assert row["未實現毛損益"] == -15000
    assert row["目前價至停損風險"] == 15000
    assert unknown_account["status"] == "HOLD"
    assert "daily_pnl" in unknown_account["帳戶風控缺失原因"]
    assert "未提供真實帳戶" in unknown_account["帳戶風控缺失原因"]["daily_pnl"]
    assert "成本後RR" in row["欄位缺失原因"]
    assert "目標價" in row["欄位缺失原因"]
    assert row["成本後RR"] is None


def test_position_missing_quote_explains_price_but_preserves_user_stop():
    result = review_manual_positions(TEXT, account_context=account(), now=NOW)
    row = result["rows"][0]
    assert row["現價"] is None
    assert row["停損／失效"] == 820.0
    assert row["未實現毛損益"] is None
    assert "A2" in row["欄位缺失原因"]["現價"]
    assert "未實現毛損益" in row["欄位缺失原因"]
    assert "停損／失效" not in row["欄位缺失原因"]
    assert result["new_entry_allowed"] is False


def test_position_known_quote_missing_stop_keeps_gross_pnl():
    result = review_manual_positions(
        "2330 1張 成本850", quotes={"2330": quote(835)},
        account_context=account(), now=NOW
    )
    row = result["rows"][0]
    assert row["現價"] == 835
    assert row["未實現毛損益"] == -15000
    assert row["停損／失效"] is None
    assert "停損／失效" in row["欄位缺失原因"]
    assert result["risk_total_twd"] is None
    assert result["status"] == "HOLD"


def test_scanner_column_diagnostics_without_any_fugle_api():
    from research.sky_13col_report import missing_field_reasons, projection
    item = {
        "symbol": "2330", "source": "Fugle paid bulk snapshot",
        "data_status": "UNVERIFIED_EXECUTION_TIME",
        "last_price": 850.0,
    }
    missing = missing_field_reasons(item)
    row = projection(item)
    assert "A2" in missing["即時價"]
    assert "OHLC" in missing["多方評分"]
    assert "strategy_plan" in missing["買進觸發"]
    assert "滑價" in missing["成本後RR"]
    assert row["買進觸發"] == "待確認（缺同次策略計畫）"
    assert row["現在動作"] == "等待"
    assert row["分類"] == "X"
