from datetime import datetime
from zoneinfo import ZoneInfo

from src.data_engine import DataQualityPolicy, validate_quote, validate_market_rows
from src.feature_contract import wrap_features
from src.trade_log import build_trade_decision_record

TZ = ZoneInfo("Asia/Taipei")


def test_data_quality_passes_fresh_quote():
    now = datetime(2026, 10, 24, 9, 15, 30, tzinfo=TZ)
    row = {
        "symbol": "2409",
        "last": 37.2,
        "volume": 1000,
        "quote_time": "09:15:00",
        "quote_source": "TWSE MIS",
    }
    result = validate_quote(row, now=now, policy=DataQualityPolicy(max_quote_age_seconds=60))
    assert result["ok"] is True
    assert result["age_seconds"] == 30.0


def test_data_quality_blocks_stale_quote():
    now = datetime(2026, 10, 24, 9, 20, 0, tzinfo=TZ)
    row = {"symbol": "2409", "last": 37.2, "volume": 1000, "quote_time": "09:15:00"}
    result = validate_quote(row, now=now, policy=DataQualityPolicy(max_quote_age_seconds=60))
    assert result["ok"] is False
    assert any("報價逾時" in x for x in result["reasons"])


def test_market_quality_summary():
    now = datetime(2026, 10, 24, 9, 15, 30, tzinfo=TZ)
    rows = [
        {"symbol": "2409", "last": 37.2, "volume": 10, "quote_time": "09:15:00"},
        {"symbol": "3481", "last": None, "volume": 10, "quote_time": "09:15:00"},
    ]
    result = validate_market_rows(rows, now=now)
    assert result["total"] == 2
    assert result["pass_count"] == 1


def test_feature_contract_has_version_and_bucket():
    now = datetime(2026, 10, 24, 9, 29, 0, tzinfo=TZ)
    env = wrap_features(
        {"symbol": "2409", "exchange": "TWSE", "last": 37.2, "bid": 37.15, "ask": 37.2},
        {"momentum_5": 1.2},
        observed_at=now,
    ).to_dict()
    assert env["schema_version"] == "1.0"
    assert env["features"]["scan_time_bucket"] == "09:30"
    assert env["features"]["spread_pct"] is not None


def test_trade_record_is_reproducible_contract():
    now = datetime(2026, 10, 24, 9, 30, 0, tzinfo=TZ)
    item = {
        "symbol": "2409",
        "name": "友達",
        "exchange": "TWSE",
        "last": 37.2,
        "risk": {"status": "BLOCK", "net_rr": None},
        "features": {"momentum_5": 1.0},
    }
    rec = build_trade_decision_record(item=item, run_id="run-1", observed_at=now)
    payload = rec.to_dict()
    assert payload["schema_version"] == "1.0"
    assert payload["symbol"] == "2409"
    assert payload["decision"] == "BLOCK"
    assert payload["execution"] == {}
    assert payload["outcome"] == {}
