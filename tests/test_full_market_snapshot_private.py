from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from research.full_market_snapshot_private import build_snapshot

NOW = datetime(2026, 11, 9, 11, 45, tzinfo=ZoneInfo("Asia/Taipei"))
UNI = [{"symbol":"1101","name":"A","exchange":"TWSE"},
       {"symbol":"8088","name":"B","exchange":"TPEx"}]


def test_snapshot_reference_is_visible_without_trade_eligibility():
    data = build_snapshot(UNI, {
        "TSE":{"date":"2026-11-09","time":"114500",
               "data":[{"symbol":"1101","lastPrice":33.5,"tradeVolume":100,
                        "changePercent":1.1}]},
        "OTC":{"date":"2026-11-09","time":"114500",
               "data":[{"symbol":"8088","lastPrice":27,"tradeVolume":50,
                        "isTrial":True}]},
    },now=NOW)
    assert data["observation_count"] == 1
    assert data["six_models_inferred"] is False
    assert all(not x["trade_eligible"] for x in data["observations"])
    assert data["observations"][0]["price_kind"] == "SNAPSHOT_REFERENCE_NOT_VERIFIED_EXECUTION"
    assert data["observations"][1]["price"] is None


def test_stale_snapshot_rejected():
    with pytest.raises(ValueError, match="stale_snapshot_TSE"):
        build_snapshot(UNI, {
            "TSE":{"date":"2026-11-09","time":"110000","data":[]},
            "OTC":{"date":"2026-11-09","time":"114500","data":[]},
        },now=NOW)
