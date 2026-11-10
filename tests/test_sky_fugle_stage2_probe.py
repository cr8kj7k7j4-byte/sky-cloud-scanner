import unittest
from src.sky_fugle_stage2_probe import check

class FakeResponse:
    def __init__(self, status, payload):
        self.status_code = status
        self.payload = payload
    def json(self):
        return self.payload

class Stage2ProbeTests(unittest.TestCase):
    def test_429_is_rate_limited(self):
        r = check(FakeResponse(429, {}), "quote_2330_TSE", quote=True)
        self.assertEqual(r["outcome"], "RATE_LIMITED")
        self.assertFalse(r["api_accessible"])
    def test_403_is_plan_restricted(self):
        self.assertEqual(check(FakeResponse(403, {}), "quote_8089_OTC", quote=True)["outcome"], "PLAN_RESTRICTED")
    def test_snapshot_rows(self):
        r = check(FakeResponse(200, {"date": "2026-11-10", "data": [{"symbol":"2330"}]}), "snapshot_TSE")
        self.assertEqual(r["row_count"], 1)
        self.assertEqual(r["outcome"], "AVAILABLE")
    def test_quote_without_time_cannot_pass(self):
        q = {"date": "2026-11-10", "lastTrade": {"price": 1000}}
        r = check(FakeResponse(200, q), "quote_2330_TSE", quote=True)
        self.assertFalse(r["last_trade_time_field_present"])
        self.assertEqual(r["outcome"], "MISSING_EXECUTED_TRADE_TIME")

if __name__ == "__main__":
    unittest.main()
