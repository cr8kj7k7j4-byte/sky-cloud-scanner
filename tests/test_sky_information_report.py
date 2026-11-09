import json
from datetime import datetime, timezone, timedelta
import subprocess
import sys

from src.sky_information_report import project_information_first
from src.sky_command_router import route_command


def test_all_market_aliases_route_to_existing_engine():
    for command in ("Sky 全市場掃描", "Sky 全市場完整掃描", "Sky 即時全市場完整掃描"):
        route = route_command(command)
        assert route.command_family == "SKY_UNIFIED_MARKET_SCAN"
        assert route.realtime_required and route.whole_market_required


def test_blocked_live_market_still_shows_true_observations():
    observed = {"symbol": "1101", "last_trade": 42.0, "source": "Fugle", "timestamp": "2026-11-09T10:00:00+08:00"}
    result = project_information_first({
        "operational_full_market_scan": False,
        "market_data_gate": "BLOCKED_EXTERNAL_DATA",
        "quote_scope": "CANDIDATES_ONLY_REALTIME",
        "quote_coverage_pct": 4.53,
        "candidates": [observed],
    })
    assert result["data_status"] == "PARTIAL_OR_UNVERIFIED"
    assert result["observed_candidate_records"] == [observed]
    assert result["coverage"]["quote_coverage_pct"] == 4.53
    assert result["trading_permission"] != "BUY"


def test_unknown_coverage_remains_unknown_not_zero_or_complete():
    result = project_information_first({"market_data_gate": "BLOCKED_EXTERNAL_DATA"})
    assert result["coverage"]["universe"] is None
    assert result["coverage"]["twse"] is None
    assert result["coverage"]["tpex"] is None
    assert result["observed_candidate_count"] == 0
    assert result["live_full_market_verified"] is False


def test_reject_false_or_incomplete_full_market_flag():
    base = {"operational_full_market_scan": True, "quote_scope": "WHOLE_MARKET_EXECUTED_LIVE",
            "market_data_gate": "PASS_FULL_MARKET_LIVE", "live_market_evidence": {}}
    assert project_information_first(base)["live_full_market_verified"] is False
    base["live_market_evidence"]["valid_whole_market_operational"] = True
    assert project_information_first(base)["live_full_market_verified"] is True


def test_cli_writes_missing_report_without_inventing_quotes(tmp_path):
    output = tmp_path / "information_first.json"
    subprocess.run([sys.executable, "-m", "src.sky_information_report", "--input",
                    str(tmp_path / "missing.json"), "--output", str(output)],
                   check=True)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["source_status"] == "REPORT_MISSING"
    assert result["observed_candidate_records"] == []
    assert result["live_full_market_verified"] is False


def test_required_mobile_columns_survive_data_block():
    from src.sky_information_report import DISPLAY_FIELDS
    report = project_information_first({
        "market_data_gate": "BLOCKED_EXTERNAL_DATA",
        "deep_candidates": [{
            "symbol": "1101", "name": "台泥", "fugle_close": 33.2,
            "data_status": "DATA_STALE", "bull_score": 99,
            "candidate_action": "買進", "entry_price": 33.5,
        }],
    })
    row = report["display_rows"][0]
    assert set(row) == set(DISPLAY_FIELDS)
    assert row["股票代碼"] == "1101"
    assert row["即時價"] is None
    assert row["多方評分"] is None
    assert row["買進觸發"] is None
    assert row["現在動作"] == "禁止交易"
    assert row["分類"] == "X"


def test_verified_single_quote_is_visible_without_full_market_buy():
    report = project_information_first({
        "market_data_gate": "BLOCKED_EXTERNAL_DATA",
        "deep_candidates": [{
            "symbol": "1101", "name": "台泥",
            "data_status": "VERIFIED_EXECUTED_TRADE",
            "fugle_close": 34.0, "trade_volume": 1000,
            "last_trade_time": datetime.now(timezone.utc).isoformat(),
            "source": "Fugle",
        }],
    })
    row = report["display_rows"][0]
    assert row["即時價"] == 34.0
    assert row["當日成交量"] == 1000
    assert row["資料來源"] == "Fugle"
    assert row["現在動作"] == "禁止交易"
    assert row["融資維持率"] is None


def test_unified_report_keeps_strategy_and_all_columns():
    from src.sky_information_report import project_unified_information
    payload = {"run_id": "123", "result": {
        "decision": "DATA_COVERAGE_INSUFFICIENT_NO_TRADE",
        "reports": {
            "intraday": {
                "available": True, "quote_coverage_pct": 5.04,
                "candidate_count": None,
                "candidate_preview": [{"symbol": "1101", "name": "台泥", "price": 40,
                                       "action": "買進"}],
            },
            "swing5d_research": {
                "available": True, "candidate_count": 0, "candidate_preview": [],
                "research_only": True,
            },
        },
    }}
    result = project_unified_information(payload)
    assert result["strategies"]["intraday"]["quote_coverage_pct"] == 5.04
    assert result["strategies"]["intraday"]["candidate_count"] is None
    assert result["strategies"]["swing5d_research"]["candidate_count"] == 0
    assert len(result["display_rows"]) == 1
    row = result["display_rows"][0]
    assert row["即時價"] is None
    assert row["股票代碼"] == "1101"
    assert row["現在動作"] == "禁止交易"
    assert row["買進觸發"] is None


def test_stale_trade_still_visible_but_not_as_realtime():
    from src.sky_information_report import project_information_first
    report = project_information_first({
        "deep_candidates": [{
            "symbol": "1101", "data_status": "VERIFIED_EXECUTED_TRADE",
            "last_trade_price": 27.05,
            "last_trade_time": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        }]
    })
    row = report["display_rows"][0]
    assert row["即時價"] is None
    assert row["最近已知成交快照（可能延遲）"] == 27.05
    assert row["現在動作"] == "禁止交易"
