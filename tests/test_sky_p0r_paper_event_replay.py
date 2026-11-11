import unittest
from research.sky_p0r_paper_event_replay import replay
from research.sky_p0r_paper_ledger_readback import audit_paper_ledger

CTX = {"run_id": "UNIT-TEST", "scan_id": "scan-test", "observed_at": "2026-11-11T13:30:00+08:00",
       "source_artifact": "UNIT_TEST_FIXTURE", "simulator_version": "UNIT_TEST"}
B = {"kind": "ORDER", "event_id": "b", "order_id": "one", "side": "BUY",
     "event_time": "2026-11-11T09:06:00+08:00", "market_scan_id": "scan-test",
     "symbol": "2409", "signal_id": "s", "risk_status": "ALLOW",
     "candidate": {"entry": 25, "stop": 24, "target": 28, "grade": "A+"},
     "execution_assumptions": {"entry_slippage_bps": 5, "exit_slippage_bps": 5,
         "spread_bps": 5, "liquidity_penalty_bps": 5, "fill_probability": 0.8}}
BF = {"kind": "FILL", "event_id": "bf", "order_id": "one", "price": 25, "shares": 1000,
      "event_time": "2026-11-11T09:10:00+08:00", "market_scan_id": "scan-test",
      "fee_twd": 8.3, "original_stop": 24,
      "market_data_time": "2026-11-11T09:05:00+08:00", "fill_assumption": "NEXT_BAR_OPEN_ESTIMATE"}
S = {"kind": "ORDER", "event_id": "s", "order_id": "two", "side": "SELL",
     "event_time": "2026-11-11T10:10:00+08:00", "market_scan_id": "scan-test",
     "symbol": "2409", "signal_id": "s"}
SF = {"kind": "FILL", "event_id": "sf", "order_id": "two", "price": 25.5, "shares": 1000,
      "event_time": "2026-11-11T10:20:00+08:00", "market_scan_id": "scan-test",
      "fee_twd": 8.5, "sale_tax_twd": 38.3, "slippage_estimate_twd": 25,
      "spread_estimate_twd": 20, "liquidity_impact_estimate_twd": 15,
      "fill_assumption": "NEXT_BAR_OPEN_ESTIMATE", "reason": "TARGET"}

class PaperEventReplayTest(unittest.TestCase):
    def test_closed_event_chain_reconciles_but_is_not_source_verified(self):
        snap, fills = replay([B, BF, S, SF], **CTX)
        self.assertEqual(snap["open_positions"], 0)
        self.assertEqual(len(fills), 1)
        self.assertAlmostEqual(snap["cash_twd"], 500384.9)
        self.assertAlmostEqual(snap["daily_realized_net_pnl_twd"], 384.9)
        result = audit_paper_ledger(snap, fills)
        self.assertTrue(result["reconciled"])
        self.assertFalse(result["simulated_fill_origin_independently_verified"])
        self.assertFalse(result["production_eligible"])

    def test_unfilled_order_does_not_invent_a_fill(self):
        snap, fills = replay([B], **CTX)
        self.assertEqual(fills, [])
        self.assertEqual(snap["open_order_count"], 1)
        self.assertEqual(snap["open_positions"], 0)
        self.assertFalse(audit_paper_ledger(snap, fills)["reconciled"])

    def test_blocked_order_never_executes(self):
        bad = {**B, "risk_status": "BLOCK"}
        snap, fills = replay([bad], **CTX)
        self.assertEqual(fills, [])
        self.assertEqual(len(snap["rejected_orders"]), 1)
        with self.assertRaises(ValueError):
            replay([bad, BF], **CTX)

    def test_missing_fill_evidence_and_future_data_block(self):
        for events in ([BF], [B, {**BF, "market_data_time": "2026-11-11T09:20:00+08:00"}],
                       [B, {**BF, "fee_twd": None}], [B, {**BF, "shares": 10000}]):
            with self.subTest(events=events):
                with self.assertRaises(ValueError):
                    replay(events, **CTX)

    def test_claimed_allow_cannot_bypass_canonical_cost_gate(self):
        for patch in ({"execution_assumptions": None},
                      {"candidate": {"entry": 25, "stop": 24, "target": 25.1}},
                      {"candidate": {"entry": 25, "stop": 24, "target": 28},
                       "execution_assumptions": {"entry_slippage_bps": None}}):
            with self.subTest(patch=patch):
                snap, _ = replay([{**B, **patch}], **CTX)
                self.assertEqual(len(snap["rejected_orders"]), 1)
                with self.assertRaises(ValueError):
                    replay([{**B, **patch}, BF], **CTX)

    def test_cost_profile_mismatch_blocks_false_zero_cost(self):
        for mutated in ({**BF, "fee_twd": 0},
                        {**SF, "sale_tax_twd": 0},
                        {**SF, "fee_twd": 0}):
            with self.subTest(mutated=mutated):
                events = [B, mutated] if mutated["order_id"] == "one" else [B, BF, S, mutated]
                with self.assertRaises(ValueError):
                    replay(events, **CTX)

    def test_stop_event_updates_counter(self):
        snap, _ = replay([B, BF, S, {**SF, "reason": "STOP", "price": 24, "fee_twd": 8.0, "sale_tax_twd": 36.0}], **CTX)
        self.assertEqual(snap["consecutive_stops"], 1)

if __name__ == "__main__":
    unittest.main()
