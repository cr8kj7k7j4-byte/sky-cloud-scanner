"""Offline-only monthly Fugle pacing and HTTP failure regression."""
import unittest
from unittest.mock import patch

from src import fugle


class FugleMonthlyRateTests(unittest.TestCase):
    def setUp(self):
        fugle._MONTHLY_LAST_REQUEST.clear()

    def test_monthly_request_does_not_create_endpoint_atomic_ref(self):
        with patch.dict("os.environ", {"SKY_FUGLE_MONTHLY_RATE_CONTROL": "1"}, clear=True), \
             patch.object(fugle, "_headers", return_value={"X-API-KEY": "test"}), \
             patch.object(fugle, "_monthly_pace") as pace, \
             patch.object(fugle, "_fetch_json", return_value={"date": "2026-11-27"}) as fetch, \
             patch("research.sky_fugle_atomic_ref_claim.guard_fugle_request",
                   side_effect=AssertionError("legacy endpoint claim must not run")):
            self.assertEqual(fugle.get_quote("2330"), {"date": "2026-11-27"})
            pace.assert_called_once_with("/intraday/quote/2330")
            fetch.assert_called_once()

    def test_monthly_and_atomic_modes_conflict_fail_closed(self):
        with patch.dict("os.environ", {"SKY_FUGLE_MONTHLY_RATE_CONTROL": "1",
                                       "SKY_PAID_ATOMIC_ENFORCE": "1"}, clear=True), \
             patch.object(fugle, "_headers", return_value={"X-API-KEY": "test"}):
            with self.assertRaisesRegex(RuntimeError, "CONFLICTING_FUGLE_BILLING_GUARDS"):
                fugle.get_quote("2330")

    def test_per_family_pacing_and_unknown_endpoint(self):
        with patch.object(fugle.time, "monotonic", side_effect=[1., 1., 1.01, 1.01]), \
             patch.object(fugle.time, "sleep") as sleep:
            fugle._monthly_pace("/intraday/quote/2330")
            fugle._monthly_pace("/intraday/quote/2317")
            sleep.assert_called_once()
            self.assertGreaterEqual(sleep.call_args.args[0], 0.10)
        with self.assertRaisesRegex(RuntimeError, "UNSUPPORTED_MONTHLY_FUGLE_ENDPOINT"):
            fugle._monthly_pace("/unknown/operation")

    def test_provider_429_does_not_retry(self):
        import requests
        response = requests.Response()
        response.status_code = 429
        response.url = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/2330"
        with patch.object(fugle.requests, "get", return_value=response) as get:
            with self.assertRaises(requests.HTTPError):
                fugle._fetch_json(response.url, None, {"X-API-KEY": "test"},
                                  "/intraday/quote/2330")
            get.assert_called_once()


if __name__ == "__main__":
    unittest.main()
