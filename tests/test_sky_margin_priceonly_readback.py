"""Offline evidence checks for SKY維持率 dated A1 reference observations."""
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from research.sky_full_universe_information import build as build_report
from scripts.sky_margin_priceonly_readback import build

TPE = ZoneInfo("Asia/Taipei")


class MarginExistingA1ReadbackTests(unittest.TestCase):
    def report(self):
        observed = datetime(2026, 11, 27, 13, 30, tzinfo=TPE)
        report = build_report([
            {"symbol": "1101", "name": "A", "exchange": "TWSE"},
            {"symbol": "1102", "name": "B", "exchange": "TWSE"},
            {"symbol": "8089", "name": "C", "exchange": "TPEx"},
        ], {
            "TSE": {"date": "2026-11-27", "data": [
                {"symbol": "1101", "lastPrice": 35, "tradeVolume": 500, "changePercent": 2.5},
                {"symbol": "1102", "lastPrice": 120, "tradeVolume": 300, "changePercent": 5.0},
            ]},
            "OTC": {"date": "2026-11-27", "data": [
                {"symbol": "8089", "lastPrice": 20, "tradeVolume": 90, "changePercent": 1.0},
            ]},
        }, observed)
        return report

    def test_price_only_weekend_research_from_dated_full_universe(self):
        report = self.report()
        out = build(report, now=datetime(2026, 11, 28, 1, 10, tzinfo=TPE),
                    source={"source_run_id": "987", "source_head_sha": "a"*40,
                            "source_artifact_id": 12, "source_json_sha256": "b"*64})
        self.assertEqual(out["status"], "DATED_A1_PRICE_RESEARCH_ONLY")
        self.assertEqual(out["source_freshness_status"], "STALE_SOURCE")
        self.assertEqual(out["official_universe_count"], 3)
        self.assertEqual(out["price_below_100_observation_count"], 2)
        self.assertEqual([row["symbol"] for row in out["preview"]], ["1101", "8089"])
        self.assertEqual(out["provider_snapshot_date"], "2026-11-27")
        for item in out["preview"]:
            self.assertFalse(item["executed_trade_verified"])
            self.assertFalse(item["margin_maintenance_ratio_verified"])
            self.assertFalse(item["production_eligible"])
            self.assertEqual(item["action"], "觀察")
        self.assertFalse(out["source_date_official_session_certified"])
        self.assertFalse(out["fugle_a2_verified"])
        self.assertFalse(out["production_eligible"])
        self.assertEqual(out["trade_action"], "禁止交易")

    def test_old_future_trial_and_missing_prices_do_not_become_candidates(self):
        report = self.report()
        for row in report["all_symbols"]:
            row["snapshot_source_date"] = "2026-10-01"
        report["all_symbols"][0]["snapshot_source_date"] = "2026-11-29"
        report["all_symbols"][1]["snapshot_source_date"] = "2026-11-27"
        report["all_symbols"][2]["snapshot_source_date"] = "2026-11-27"
        report["all_symbols"][2]["snapshot_is_trial"] = True
        out = build(report, now=datetime(2026, 11, 28, 1, 10, tzinfo=TPE), source={})
        self.assertEqual(out["status"], "HOLD_NO_RECENT_DATED_OBSERVATIONS")
        self.assertEqual(out["price_below_100_observation_count"], 0)
        self.assertEqual(out["preview"], [])
        self.assertFalse(out["automatic_order"])

    def test_incomplete_or_duplicate_official_universe_rejected(self):
        report = self.report()
        report["universe_count"] += 1
        with self.assertRaisesRegex(ValueError, "UNIVERSE_COUNT_MISMATCH"):
            build(report, now=datetime(2026, 11, 28, 1, 10, tzinfo=TPE), source={})

    def test_existing_margin_owner_workflow_has_same_run_artifact_readback(self):
        workflow = Path(".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        job = workflow.split("  margin_readonly_command:", 1)[1]
        job = job.split("  w0_run_discovery:", 1)[0]
        self.assertIn("github.event.comment.body == 'SKY維持率'", job)
        self.assertIn("github.event.comment.user.login == github.repository_owner", job)
        self.assertIn("scripts.sky_margin_priceonly_readback", job)
        self.assertIn("MARGIN_PRICEONLY_SAME_RUN_HASH_MISMATCH", job)
        self.assertIn("MARGIN_PRICEONLY_READBACK_GUARD", job)
        self.assertIn("SKY_MARGIN_PRICEONLY_INDEPENDENT_READBACK", job)
        self.assertNotIn("FUGLE_API_KEY", job)
        self.assertNotIn("sky_paid_fugle_api_guard", job)


if __name__ == "__main__":
    unittest.main()
