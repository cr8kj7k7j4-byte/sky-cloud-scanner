import unittest

from research.sky_postmarket_observation import mark_observation_only


class TestPostmarketObservation(unittest.TestCase):
    def _report(self):
        return {
            "snapshot_status": {"TWSE": "RETURNED", "TPEx": "RETURNED"},
            "snapshot_integrity": {
                "TWSE": {"snapshot_date": "2026-11-25"},
                "TPEx": {"snapshot_date": "2026-11-25"},
            },
            "by_exchange": {
                "TWSE": {"fresh_executed": 1, "fresh_executed_pct": 100.0},
                "TPEx": {"fresh_executed": 1, "fresh_executed_pct": 100.0},
            },
            "fresh_executed_count": 2, "fresh_executed_pct": 100.0,
            "all_symbols": [{
                "symbol": "2330", "name": "test", "exchange": "TWSE",
                "last_price": 100.0, "last_trade_time": "2026-11-25T13:30:00+08:00",
                "data_status": "FRESH_EXECUTED_TRADE", "trade_signal": True,
            }],
            "ranked_observations": [{
                "symbol": "2330", "name": "test", "exchange": "TWSE",
                "last_price": 100.0, "data_status": "FRESH_EXECUTED_TRADE",
                "production_eligible": True,
            }],
        }

    def test_postmarket_never_promotes_historical_snapshot_to_live_trade(self):
        report = mark_observation_only(self._report())
        self.assertEqual(report["research_mode"], "POSTMARKET_RESEARCH_ONLY")
        self.assertEqual(report["source_status"], "OBSERVATION_ONLY")
        self.assertEqual(report["fresh_executed_count"], 0)
        self.assertFalse(report["postmarket_live_execution_certified"])
        self.assertEqual(report["snapshot_data_dates"]["TWSE"], "2026-11-25")
        for group in ("all_symbols", "ranked_observations"):
            row = report[group][0]
            self.assertEqual(row["last_price"], 100.0)
            self.assertEqual(row["data_status"], "POSTMARKET_OBSERVATION_ONLY")
            self.assertFalse(row["production_eligible"])
            self.assertFalse(row["trade_signal"])
            self.assertIsNone(row["required_fields"]["即時價"])
            self.assertEqual(row["required_fields"]["現在動作"], "禁止交易")
        self.assertEqual(report["by_exchange"]["TWSE"]["fresh_executed"], 0)

    def test_missing_market_does_not_count_as_full_market_scan(self):
        report = self._report()
        report["snapshot_status"]["TPEx"] = "MISSING"
        got = mark_observation_only(report)
        self.assertEqual(got["source_status"], "HOLD_INCOMPLETE_SNAPSHOT_SOURCES")
        self.assertFalse(got["production_eligible"])


if __name__ == "__main__":
    unittest.main()
