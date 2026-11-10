import unittest
from research.sky_snapshot_candidates import screen


class StageOneSnapshotTests(unittest.TestCase):
    def row(self, symbol, **overrides):
        row = {
            "symbol": symbol, "name": "test", "exchange": "TWSE",
            "source": "Fugle paid bulk snapshot", "last_price": 50.0,
            "volume": 400, "change_pct": 1.0,
            "snapshot_source_date": "2026-11-10",
            "snapshot_observed_at": "2026-11-10T09:12:00+08:00",
            "snapshot_is_trial": False,
            "last_trade_time": None, "data_status": "UNVERIFIED_EXECUTION_TIME",
        }
        row.update(overrides)
        return row

    def report(self, rows):
        return {"schema": "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1",
                "checked_at_tpe": "2026-11-10T09:12:00+08:00",
                "universe_count": len(rows), "all_symbols": rows}

    def test_two_markets_and_no_execution_claim(self):
        rows = [self.row("1101"), self.row("8089", exchange="TPEx")]
        r = screen(self.report(rows))
        self.assertEqual(r["candidate_count"], 2)
        self.assertEqual(r["by_exchange"]["TPEx"]["candidates"], 1)
        self.assertFalse(r["production_eligible"])
        self.assertTrue(all(x["action"] == "等待" for x in r["candidates"]))
        self.assertTrue(all(x["classification"] == "未分級" for x in r["candidates"]))
        self.assertTrue(all(not x["executed_trade_verified"] for x in r["candidates"]))

    def test_stale_and_trial_and_price_and_volume_blocked(self):
        rows = [self.row("1101", snapshot_source_date="2026-11-09"),
                self.row("1102", snapshot_is_trial=True),
                self.row("1103", last_price=100.0),
                self.row("1104", volume=0),
                self.row("1105", last_price=None),
                self.row("1106", source="NO_SNAPSHOT_ROW")]
        r = screen(self.report(rows))
        self.assertEqual(r["candidate_count"], 0)
        self.assertEqual(sum(r["excluded_reasons"].values()), 6)

    def test_reject_duplicate_universe(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SYMBOL"):
            screen(self.report([self.row("1101"), self.row("1101")]))

    def test_reject_naive_report_time(self):
        report = self.report([self.row("1101")])
        report["checked_at_tpe"] = "2026-11-10T09:12:00"
        with self.assertRaisesRegex(ValueError, "NAIVE_CHECKED_AT"):
            screen(report)

    def test_reject_fabricated_coverage(self):
        report = self.report([self.row("1101")])
        report["universe_count"] = 4
        with self.assertRaisesRegex(ValueError, "UNIVERSE_INCOMPLETE"):
            screen(report)

    def test_cannot_raise_price_limit(self):
        with self.assertRaisesRegex(ValueError, "INVALID_PRICE_LIMIT"):
            screen(self.report([self.row("1101")]), max_price=101)

if __name__ == "__main__":
    unittest.main()
