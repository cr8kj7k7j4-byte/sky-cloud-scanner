from datetime import datetime, timezone

from src.alert_observation import build_alert_observation
from src.sky_command_router import route_command


def test_alert_observations_remain_visible_when_production_blocked():
    universe = [
        {"symbol": "1111", "exchange": "TWSE"},
        {"symbol": "2222", "exchange": "TPEx"},
        {"symbol": "3333", "exchange": "TWSE"},
    ]
    accepted = [
        {"symbol": "1111", "name": "A", "exchange": "TWSE",
         "last": 22.3, "change_pct": 1.5, "quote_date": "2026-11-09",
         "quote_time": "11:15:00", "quote_source": "TWSE MIS"},
        {"symbol": "2222", "name": "B", "exchange": "TPEx",
         "last": 13.2, "change_pct": 3.2, "quote_date": "2026-11-09",
         "quote_time": "11:14:59", "quote_source": "TWSE MIS"},
    ]
    r = build_alert_observation(accepted, universe,
                                observed_at=datetime(2026, 11, 9, tzinfo=timezone.utc))
    assert r["valid_total"] == 2
    assert r["coverage_pct"] == 66.67
    assert r["twse_valid"] == 1 and r["tpex_valid"] == 1
    assert [x["symbol"] for x in r["candidates"]] == ["2222", "1111"]
    assert all(x["production_entry_allowed"] is False for x in r["candidates"])
    assert all(x["classification"] == "UNVERIFIED_OBSERVATION" for x in r["candidates"])


def test_alert_has_no_fabricated_missing_prices():
    r = build_alert_observation([
        {"symbol": "1234", "last": None, "change_pct": 10},
        {"symbol": "5678", "last": 30, "quote_time": "11:00:00"},
    ], [{"symbol": "1234"}, {"symbol": "5678"}],
        observed_at="2026-11-09T11:00:00+08:00")
    assert [x["symbol"] for x in r["candidates"]] == ["5678"]
    assert r["candidates"][0]["bid"] is None


def test_sky_alert_is_whole_market_observation_not_position():
    r = route_command("Sky 警戒")
    assert r.whole_market_required and r.realtime_required
    assert r.command_family == "SKY_ALERT_WHOLE_MARKET_OBSERVATION"
    assert route_command("Sky 持倉監控").whole_market_required is False
