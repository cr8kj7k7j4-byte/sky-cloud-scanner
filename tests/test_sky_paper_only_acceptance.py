import unittest

from research.sky_paper_only_acceptance import audit_status, cadence_slots, paper_gate

GOOD_LEDGER = {
    "mode": "PAPER_ONLY", "daily_realized_net_pnl_twd": 0,
    "consecutive_stops": 0, "open_positions": 0,
    "open_stop_risk_twd": 0, "proposed_entry": 50,
    "proposed_stop": 49, "proposed_notional_twd": 50000,
}
GOOD_COST = {"execution_cost_complete": True,
             "after_cost_rr_certified": True, "after_cost_rr": 2.0}


class PaperOnlyAcceptanceTest(unittest.TestCase):
    def test_paper_only_normal_never_authorizes_live(self):
        r = paper_gate(GOOD_LEDGER, GOOD_COST)
        self.assertTrue(r["paper_eligible"])
        self.assertFalse(r["production_eligible"])
        self.assertFalse(r["live_order_enabled"])
        self.assertEqual(r["live_trade_action"], "禁止交易")

    def test_two_stops_hard_block_paper(self):
        r = paper_gate({**GOOD_LEDGER, "consecutive_stops": 2}, GOOD_COST)
        self.assertFalse(r["paper_eligible"])
        self.assertIn("TWO_CONSECUTIVE_STOPS", r["reasons"])

    def test_daily_net_loss_ten_thousand_hard_block(self):
        r = paper_gate({**GOOD_LEDGER, "daily_realized_net_pnl_twd": -10000}, GOOD_COST)
        self.assertIn("DAILY_LOSS_STOP", r["reasons"])

    def test_missing_cost_not_assumed_zero(self):
        for cost in (None, {}, {"execution_cost_complete": False},
                     {"execution_cost_complete": True, "after_cost_rr_certified": False}):
            with self.subTest(cost=cost):
                r = paper_gate(GOOD_LEDGER, cost)
                self.assertFalse(r["paper_eligible"])
                self.assertIn("AFTER_COST_RR_NOT_CERTIFIED", r["reasons"])

    def test_missing_paper_ledger_not_assumed_empty_account(self):
        for ledger in (None, {}, {**GOOD_LEDGER, "mode": "LIVE"},
                       {**GOOD_LEDGER, "open_positions": None}):
            with self.subTest(ledger=ledger):
                r = paper_gate(ledger, GOOD_COST)
                self.assertFalse(r["paper_eligible"])

    def test_position_and_portfolio_cap_fail_closed(self):
        cases = [
            ({"open_positions": 3}, "MAX_POSITIONS"),
            ({"open_stop_risk_twd": 15000}, "PORTFOLIO_HEAT_LIMIT"),
            ({"proposed_notional_twd": 100001}, "SINGLE_STOCK_CAP"),
            ({"proposed_notional_twd": 100000, "proposed_stop": 45}, "SINGLE_TRADE_RISK_LIMIT"),
            ({"proposed_stop": 51}, "INVALID_LONG_STOP_DIRECTION"),
        ]
        for changes, marker in cases:
            with self.subTest(changes=changes):
                self.assertIn(marker, paper_gate({**GOOD_LEDGER, **changes}, GOOD_COST)["reasons"])

    def test_cost_after_rr_minimum(self):
        r = paper_gate(GOOD_LEDGER, {**GOOD_COST, "after_cost_rr": 1.4})
        self.assertIn("AFTER_COST_RR_BELOW_THRESHOLD", r["reasons"])

    def test_exactly_fifty_five_expected_intraday_slots(self):
        x = cadence_slots()
        self.assertEqual(len(x), 55)
        self.assertEqual(x[0], "09:00")
        self.assertEqual(x[-1], "13:30")
        self.assertEqual(len(x), len(set(x)))

    def test_research_scan_success_does_not_certify_schedule_or_performance(self):
        result = audit_status({
            "scan_id": "synthetic-test", "run_url": "https://example.org/run",
            "data_timestamp": "2026-11-10T12:30:00+08:00",
            "stage2_verified_executed_count": 12,
            "candidate_chain_vwap_certified": 0,
        })
        self.assertTrue(result["market_data_timestamp_valid"])
        self.assertFalse(result["broker_account_required_for_research"])
        self.assertFalse(result["paper_fills_provided"])
        self.assertFalse(result["paper_after_cost_performance_verified"])
        self.assertEqual(result["paper_performance_verdict"], "INSUFFICIENT_DATA")
        self.assertEqual(result["schedule_reliability_verdict"], "INSUFFICIENT_DATA")
        self.assertFalse(result["production_eligible"])

    def test_paper_performance_needs_ledger_cost_and_independent_sources(self):
        ledger = {
            "reconciled": True, "paper_fill_count": 1,
            "paper_cost_arithmetic_reconciled": True,
        }
        signal = {"verified_github_provenance": {"github_metadata_verified": True}}
        market = {"source_artifact_verified": True}
        result = audit_status({}, paper_readback=ledger,
                              signal_source=signal, market_source=market)
        self.assertTrue(result["paper_fills_provided"])
        self.assertTrue(result["paper_after_cost_performance_verified"])
        self.assertEqual(result["paper_performance_verdict"],
                         "VERIFIED_PAPER_ESTIMATE_RESEARCH_ONLY")
        self.assertFalse(result["production_eligible"])
        for bad_signal, bad_market, bad_ledger in (
            ({}, market, ledger),
            (signal, {}, ledger),
            (signal, market, {**ledger, "paper_cost_arithmetic_reconciled": False}),
            (signal, market, {**ledger, "reconciled": False}),
            (signal, market, {**ledger, "paper_fill_count": 0}),
        ):
            with self.subTest(signal=bad_signal, market=bad_market, ledger=bad_ledger):
                bad = audit_status({}, paper_readback=bad_ledger,
                                   signal_source=bad_signal, market_source=bad_market)
                self.assertFalse(bad["paper_after_cost_performance_verified"])
                self.assertEqual(bad["paper_performance_verdict"], "INSUFFICIENT_DATA")

    def test_invalid_timestamp_keeps_unverified(self):
        self.assertFalse(audit_status({"data_timestamp": "not-a-time"})["market_data_timestamp_valid"])


if __name__ == "__main__":
    unittest.main()
