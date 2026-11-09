import json
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
