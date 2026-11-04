from datetime import date, datetime
from zoneinfo import ZoneInfo
from src import swing_v11_live_scanner as scan

ROWS = [{"Date": "1150101", "Name": "放假", "Description": "放假"}]


def test_friday_is_valid_for_monday():
    r = scan.signal_date_guard("2026-10-30", date(2026, 11, 2), ROWS)
    assert r == {"status": "PASS", "fresh": True, "expected_signal_date": "2026-10-30"}


def test_stale_and_future_are_blocked():
    for signal in ("2026-10-22", "2026-11-03"):
        r = scan.signal_date_guard(signal, date(2026, 11, 2), ROWS)
        assert r["status"] == "STALE_OR_FUTURE_SIGNAL"
        assert not r["fresh"]


def test_closed_invalid_and_unknown_calendar_are_blocked():
    assert scan.signal_date_guard("2026-10-30", date(2026, 11, 1), ROWS)["status"] == "MARKET_CLOSED"
    assert scan.signal_date_guard("not-a-date", date(2026, 11, 2), ROWS)["status"] == "INVALID_SIGNAL_DATE"
    assert scan.signal_date_guard("2026-10-30", date(2026, 11, 2), [])["status"] == "CALENDAR_YEAR_UNVERIFIED"
    ambiguous = ROWS + [{"Date": "1151102", "Name": "特殊安排", "Description": "待確認"}]
    assert scan.signal_date_guard("2026-10-30", date(2026, 11, 2), ambiguous)["status"] == "CALENDAR_UNVERIFIED"


def test_calendar_api_error_blocks(monkeypatch):
    def error():
        raise TimeoutError()
    monkeypatch.setattr(scan, "fetch_calendar", error)
    assert scan.load_signal_date_guard("2026-10-30", date(2026, 11, 2))["status"] == "CALENDAR_UNAVAILABLE"


def test_stale_history_produces_no_tradable_candidates(monkeypatch, tmp_path):
    class Clock:
        @classmethod
        def now(cls, tz):
            return datetime(2026, 11, 2, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
    monkeypatch.setattr(scan, "datetime", Clock)
    monkeypatch.setattr(scan, "OUT", tmp_path)
    monkeypatch.setattr(scan, "load_daily_history", lambda _: {"1111": []})
    monkeypatch.setattr(scan, "choose_signal_date", lambda _: ("2026-10-22", {"max_cross_section": 20}))
    monkeypatch.setattr(scan, "fetch_calendar", lambda: ROWS)
    monkeypatch.setattr(scan, "build_signal_cross_section", lambda *_: ([{"symbol": "1111"}], 0.6))
    monkeypatch.setattr(scan, "frozen_signal_pass", lambda _: (True, []))
    monkeypatch.setattr(scan, "load_official_universe", lambda: ([{"symbol": "1111"}], {"twse": 1091, "tpex": 892}))
    calls = []
    def quotes(candidates, universe, now=None):
        calls.append(candidates)
        return {}, [], {"requested": 0, "mis": 0, "fugle": 0, "missing": 0}
    monkeypatch.setattr(scan, "fetch_candidate_live_quotes", quotes)
    result = scan.run("unused")
    assert calls == [[]]
    assert result["candidate_count"] == 0
    assert result["signal_date_guard"]["status"] == "STALE_OR_FUTURE_SIGNAL"
    assert result["quote_coverage_pct"] is None
    assert "禁止交易" in (tmp_path / "latest.txt").read_text()
