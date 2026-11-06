import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.sky_fast_report_gateway import read_fast_report

TZ = ZoneInfo("Asia/Taipei")

def test_missing_report_fails_closed(tmp_path):
    out = read_fast_report("Sky 全市場快報", tmp_path, datetime(2026, 11, 5, 9, 10, tzinfo=TZ))
    assert out["state"] == "REPORT_MISSING"
    assert out["trade_allowed"] is False
    assert out["entry"] is None

def test_old_snapshot_not_current_quote(tmp_path):
    path = tmp_path / "docs/SKY_UNIFIED_LATEST_ALL_MARKET.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "published_at_utc": "2026-11-04T14:55:59+00:00",
        "decision": "NO_TRADE_OUTSIDE_TW_REGULAR_SESSION",
        "scan_step_outcome": "success",
    }))
    out = read_fast_report("Sky 全市場快報", tmp_path, datetime(2026, 11, 5, 9, 20, tzinfo=TZ))
    assert out["report_fresh_for_realtime"] is False
    assert out["trade_allowed"] is False
    assert out["action"] == "觀察"

def test_fresh_status_never_becomes_trade(tmp_path):
    path = tmp_path / "docs/SKY_UNIFIED_LATEST_ALL_MARKET.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "published_at_utc": "2026-11-05T01:09:00+00:00",
        "decision": "SUCCESS",
        "scan_step_outcome": "success"
    }))
    out = read_fast_report("Sky 高速全市場", tmp_path, datetime(2026, 11, 5, 9, 10, tzinfo=TZ))
    assert out["report_fresh"] is True
    assert out["report_fresh_for_realtime"] is False
    assert out["trade_allowed"] is False
    assert out["entry"] is None and out["short_score"] is None

def test_short_research_fails_closed(tmp_path):
    out = read_fast_report("Sky 多空最佳機會掃描", tmp_path)
    assert out["state"] == "RESEARCH_ONLY"
    assert out["action"] == "禁止交易"


def test_naive_or_future_timestamp_never_fresh(tmp_path):
    path = tmp_path / "docs/SKY_UNIFIED_LATEST_ALL_MARKET.json"
    path.parent.mkdir(parents=True)
    now = datetime(2026, 11, 5, 9, 10, tzinfo=TZ)
    for timestamp in ("2026-11-05T09:09:00", "2026-11-05T01:11:00+00:00"):
        path.write_text(json.dumps({"published_at_utc": timestamp}))
        out = read_fast_report("Sky 全市場快報", tmp_path, now)
        assert out["report_fresh"] is False
        assert out["report_fresh_for_realtime"] is False
        assert out["trade_allowed"] is False

def test_null_dashboard_is_safe(tmp_path):
    path = tmp_path / "docs/SKY_UNIFIED_LATEST_ALL_MARKET.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"published_at_utc": "2026-11-05T01:09:00+00:00", "w4_dashboard": None}))
    out = read_fast_report("Sky 全市場快報", tmp_path, datetime(2026, 11, 5, 9, 10, tzinfo=TZ))
    assert out["published_decision"] is None
    assert out["trade_allowed"] is False
