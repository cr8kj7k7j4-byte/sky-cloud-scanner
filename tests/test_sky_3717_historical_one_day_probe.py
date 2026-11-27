"""W0 #363: repeated authorized HTTP requests never become evidence gating."""
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from scripts.sky_3717_historical_one_day_probe import run, RecordingSession
from src.sky_historical_5m_research import PASS, HOLD

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 28, 1, 50, tzinfo=TPE)


class FakeResponse:
    def __init__(self, status, obj):
        self.status_code = status
        self.obj = obj
    def raise_for_status(self):
        import requests
        if self.status_code >= 400:
            raise requests.HTTPError("MOCK_HTTP_ERROR")
    def json(self):
        return self.obj


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []
    def get(self, url, *, params, headers, timeout):
        self.calls.append((url, params, timeout))
        return self.response


class HistoricalOneDayTests(unittest.TestCase):
    def check(self, obj, status=200):
        fake = FakeTransport(FakeResponse(status, obj))
        with patch.dict("os.environ", {"SKY_FUGLE_MONTHLY_RATE_CONTROL": "1",
                                         "SKY_PAID_ATOMIC_ENFORCE": "0"}), \
             patch("src.fugle.FUGLE_API_KEY", "OFFLINE_FAKE_TEST_KEY"), \
             patch("src.fugle._monthly_pace"):
            value = run(session=RecordingSession(fake), observed_at=NOW)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0][1]["from"], "2026-11-27")
        self.assertEqual(fake.calls[0][1]["to"], "2026-11-27")
        self.assertEqual(fake.calls[0][1]["timeframe"], "5")
        self.assertFalse(value["execution_authorized"])
        self.assertFalse(value["production_eligible"])
        self.assertFalse(value["independent_vwap_certified"])
        return value

    def test_success_realistic_data_without_identity_is_not_fabricated(self):
        a = self.check({"data": [{
            "date": "2026-11-27T09:00:00+08:00",
            "open": 18, "high": 18.5, "low": 17.9,
            "close": 18.2, "volume": 5, "average": 18.1
        }]})
        self.assertEqual(a["http_status"], 200)
        self.assertEqual(a["row_count"], 1)
        self.assertEqual(a["status"], HOLD)
        self.assertEqual(a["reason"], "HISTORICAL_IDENTITY_MISMATCH")
        self.assertEqual(len(a["provider_bars_sha256"]), 64)

    def test_full_metadata_pass_still_not_trade_certified(self):
        a = self.check({"symbol": "3717", "exchange": "TWSE", "timeframe": "5",
                        "data": [{
                            "date": "2026-11-27T13:30:00+08:00",
                            "open": 18, "high": 18.5, "low": 17.9,
                            "close": 18.2, "volume": 5, "average": 18.1
                        }]})
        self.assertEqual(a["status"], PASS)
        self.assertEqual(a["request_count"], 1)
        self.assertEqual(a["five_minute_status"], "HOLD_LIVE_TRADES_NOT_CERTIFIED")
        self.assertFalse(a["historical_5m_research"]["independent_vwap_certified"])

    def test_provider_denied_and_limited_fail_closed_no_retry(self):
        for code in (401, 403, 404, 429, 500):
            a = self.check({"error": "secret need not be printed"}, status=code)
            self.assertEqual(a["http_status"], code)
            self.assertEqual(a["request_count"], 1)
            self.assertEqual(a["status"], HOLD)
            self.assertEqual(a["reason"], "PROVIDER_HTTP_" + str(code))
            self.assertNotIn("secret", str(a))

    def test_scope_denial_never_sends_paid_request(self):
        s = RecordingSession(FakeTransport(FakeResponse(200, {"data": []})))
        for symbol, day in (("2330", "2026-11-27"),
                            ("3717", "2026-11-26"),
                            ("3717", "2026-11-28")):
            a = run(symbol=symbol, source_date=day, session=s, observed_at=NOW)
            self.assertEqual(a["status"], HOLD)
            self.assertEqual(a["request_count"], 0)
        self.assertEqual(s.request_count, 0)

    def test_repeated_explicit_observations_same_session_allowed(self):
        f = FakeTransport(FakeResponse(200, {
            "symbol": "3717", "exchange": "TWSE", "timeframe": "5",
            "data": [{
                "date": "2026-11-27T13:30:00+08:00",
                "open": 18, "high": 18.5, "low": 17.9,
                "close": 18.2, "volume": 5, "average": 18.1,
            }]
        }))
        s = RecordingSession(f)
        with patch.dict("os.environ", {"SKY_FUGLE_MONTHLY_RATE_CONTROL": "1",
                                         "SKY_PAID_ATOMIC_ENFORCE": "0"}), \
             patch("src.fugle.FUGLE_API_KEY", "OFFLINE_FAKE_TEST_KEY"), \
             patch("src.fugle._monthly_pace") as pacing:
            observations = [run(session=s, observed_at=NOW) for _ in range(3)]
        self.assertEqual(len(f.calls), 3)
        self.assertEqual(pacing.call_count, 3)
        self.assertEqual([o["request_count"] for o in observations], [1, 2, 3])
        self.assertTrue(all(o["status"] == PASS for o in observations))
        self.assertTrue(all(not o["http_request_count_is_evidence_gate"] for o in observations))
        self.assertTrue(all(not o["execution_authorized"] for o in observations))

    def test_provider_error_then_new_user_observation_not_permanently_blocked(self):
        class Responses:
            def __init__(self):
                self.calls = 0
            def get(self, url, *, params, headers, timeout):
                self.calls += 1
                if self.calls == 1:
                    return FakeResponse(429, {"error": "rate_limited"})
                return FakeResponse(200, {
                    "symbol": "3717", "exchange": "TWSE", "timeframe": "5", "data": []
                })
        fake = Responses()
        s = RecordingSession(fake)
        with patch.dict("os.environ", {"SKY_FUGLE_MONTHLY_RATE_CONTROL": "1",
                                         "SKY_PAID_ATOMIC_ENFORCE": "0"}), \
             patch("src.fugle.FUGLE_API_KEY", "OFFLINE_FAKE_TEST_KEY"), \
             patch("src.fugle._monthly_pace") as pacing:
            first = run(session=s, observed_at=NOW)
            second = run(session=s, observed_at=NOW)
        self.assertEqual(first["reason"], "PROVIDER_HTTP_429")
        self.assertEqual(second["status"], "OBSERVATION_ONLY_NO_5M_BARS")
        self.assertEqual(fake.calls, 2)
        self.assertEqual(pacing.call_count, 2)
        self.assertFalse(second["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
