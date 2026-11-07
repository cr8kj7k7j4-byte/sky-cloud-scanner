import unittest
from research.fugle_2026_entitlement_probe import run_probe, summarize_candles


class FakeResponse:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data if data is not None else {"data": []}

    def json(self):
        return self._data


class ProbeTest(unittest.TestCase):
    def test_missing_credential_is_safe(self):
        x = run_probe("", symbols=("1101",), get=lambda *a, **kw: None)
        self.assertEqual(x["results"][0]["status"], "MISSING_CREDENTIAL")
        self.assertFalse(x["all_symbols_retrieved"])

    def test_plan_restricted_does_not_claim_data(self):
        x = run_probe("secret-test", symbols=("1101",),
                      get=lambda *a, **kw: FakeResponse(403))
        self.assertEqual(x["results"][0]["status"], "AUTH_OR_PLAN_RESTRICTED")
        self.assertNotIn("secret-test", str(x))

    def test_valid_single_bar_is_not_whole_market_coverage(self):
        row = {"date": "2026-11-06T09:00:00+08:00", "open": 1, "high": 2,
               "low": 1, "close": 2, "volume": 100}
        x = run_probe("secret-test", symbols=("1101",),
                      get=lambda *a, **kw: FakeResponse(200, {"data": [row]}))
        self.assertTrue(x["all_symbols_retrieved"])
        self.assertFalse(x["all_market_coverage_verified"])
        self.assertFalse(x["complete_period_verified"])
        self.assertFalse(x["backtest_executed"])

    def test_duplicate_timestamp_rejected(self):
        row = {"date": "2026-11-06T09:00:00+08:00", "open": 1, "high": 2,
               "low": 1, "close": 2, "volume": 100}
        with self.assertRaises(ValueError):
            summarize_candles([row, row])


if __name__ == "__main__":
    unittest.main()
