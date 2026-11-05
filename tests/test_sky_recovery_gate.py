import unittest
from datetime import datetime, timezone, timedelta

FIXTURE_NOW = datetime(2026, 11, 4, 16, 0, tzinfo=timezone.utc)
from research.sky_recovery_gate import evaluate


def fixture(trades=0, fills=0, source_ok=False, complete=0, days=5):
    return {
        "generated_at_utc": "2026-11-04T14:48:46+00:00",
        "w4_dashboard": {
            "sample_sufficiency": {"observed": {"samples": 100, "trading_days": days,
                "regime_count": 2 if source_ok else 0, "top_symbol_share": 0.03}},
            "strategy_evidence_integrity": {"eligible_strategy_records": trades,
                "complete_strategy_outcomes_with_modelled_costs": complete,
                "observed_execution_fills": fills},
            "forward_trade_provenance": {"authoritative_forward_rule_source_verified": source_ok,
                "can_certify_strategy_trades": source_ok},
        },
    }


class RecoveryContract(unittest.TestCase):
    def test_ranking_does_not_count_as_trading(self):
        result = evaluate(fixture(), {"decision": "HEALTH_OBSERVED_NOT_FULLY_CERTIFIED"}, now=FIXTURE_NOW)
        self.assertEqual(result["readiness"], "BLOCKED")
        self.assertEqual(result["counts"]["eligible_strategy_trades"], 0)
        self.assertIn("AUTHORITATIVE_STRATEGY_PROVENANCE_BLOCKED", result["reasons"])
        self.assertFalse(result["trade_authorized"])

    def test_engineering_success_does_not_certify_alpha(self):
        result = evaluate(fixture(), {"decision": "HEALTH_FULLY_CERTIFIED", "published_at_utc": "2026-11-04T15:00:00+00:00"}, now=FIXTURE_NOW)
        self.assertIn("STRATEGY_TRADE_SAMPLE_INSUFFICIENT", result["reasons"])

    def test_absent_snapshot_fails_closed(self):
        result = evaluate({}, now=FIXTURE_NOW)
        self.assertIn("STATUS_TIMESTAMP_MISSING_OR_INVALID", result["reasons"])
        self.assertEqual(result["readiness"], "BLOCKED")

    def test_counts_alone_never_promote(self):
        r = evaluate(fixture(trades=220, fills=180, source_ok=True, complete=210, days=25),
                     {"decision": "HEALTH_FULLY_CERTIFIED", "published_at_utc": "2026-11-04T15:00:00+00:00"},
                     {"evidence": {"after_cost_expectancy_r": 0.12}, "published_at_utc": "2026-11-04T15:00:00+00:00"}, now=FIXTURE_NOW)
        self.assertEqual(r["readiness"], "READY_FOR_W0_P0G_REVIEW_ONLY")
        self.assertFalse(r["trade_authorized"])
        self.assertFalse(r["production_promoted"])

    def test_missing_fills_fails(self):
        r = evaluate(fixture(trades=220, source_ok=True, complete=210, days=25),
                     {"decision": "HEALTH_FULLY_CERTIFIED"},
                     {"evidence": {"after_cost_expectancy_r": 0.12}})
        self.assertIn("EXECUTION_FILL_EVIDENCE_MISSING", r["reasons"])

    def test_timestamp_required(self):
        s = fixture()
        s["generated_at_utc"] = "yesterday"
        self.assertIn("STATUS_TIMESTAMP_MISSING_OR_INVALID", evaluate(s, now=FIXTURE_NOW)["reasons"])


    def test_timestamp_freshness_is_required(self):
        s = fixture(trades=220, fills=180, source_ok=True, complete=210, days=25)
        result = evaluate(s, {"decision": "HEALTH_FULLY_CERTIFIED",
                              "published_at_utc": "2026-11-04T15:00:00+00:00"},
                          {"evidence": {"after_cost_expectancy_r": 0.12},
                           "published_at_utc": "2026-11-04T15:00:00+00:00"},
                          now=FIXTURE_NOW + timedelta(days=3))
        self.assertEqual(result["readiness"], "BLOCKED")
        self.assertIn("STATUS_STALE_OR_FUTURE", result["reasons"])

    def test_future_timestamp_is_not_accepted(self):
        s = fixture()
        s["generated_at_utc"] = "2026-11-06T17:00:00+00:00"
        result = evaluate(s, now=FIXTURE_NOW)
        self.assertIn("STATUS_STALE_OR_FUTURE", result["reasons"])

    def test_health_verdict_without_time_fails(self):
        s = fixture(trades=220, fills=180, source_ok=True, complete=210, days=25)
        result = evaluate(s, {"decision": "HEALTH_FULLY_CERTIFIED"},
                          {"evidence": {"after_cost_expectancy_r": 0.12},
                           "published_at_utc": "2026-11-04T15:00:00+00:00"},
                          now=FIXTURE_NOW)
        self.assertIn("HEALTH_STATUS_STALE_OR_UNDATED", result["reasons"])


if __name__ == "__main__":
    unittest.main()
