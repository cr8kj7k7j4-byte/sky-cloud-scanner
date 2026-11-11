import copy
import unittest

from research.sky_p0r_paper_ledger_readback import audit_paper_ledger


ROW = {
    "paper_trade_id": "paper-1", "signal_id": "signal-1",
    "market_scan_id": "scan-1", "symbol": "2409",
    "market_data_time": "2026-11-11T09:05:00+08:00",
    "entry_time": "2026-11-11T09:10:00+08:00",
    "exit_time": "2026-11-11T10:20:00+08:00",
    "entry_price": 25, "exit_price": 25.5, "shares": 1000,
    "entry_fee_twd": 8.3, "exit_fee_twd": 8.5,
    "sale_tax_twd": 38.3, "slippage_estimate_twd": 25,
    "spread_estimate_twd": 20, "liquidity_impact_estimate_twd": 15,
    "fill_assumption": "NEXT_BAR_OPEN_ESTIMATE",
    "source_type": "PAPER_SIMULATION",
}
SNAP = {
    "mode": "PAPER_ONLY", "observed_at": "2026-11-11T13:30:00+08:00",
    "run_id": "paper-run-1", "scan_id": "scan-1",
    "simulator_version": "test-fixture-only",
    "source_artifact": "synthetic-unit-test.json",
    "journal_scope": "FULL_DAY", "daily_realized_net_pnl_twd": 384.9,
    "account_equity_twd": 500384.9, "cash_twd": 500384.9,
    "consecutive_stops": 0, "open_positions": 0,
    "open_stop_risk_twd": 0, "positions": [],
}


class ReadbackTest(unittest.TestCase):
    def test_consistent_synthetic_fixture_is_not_real_or_proven_source(self):
        r = audit_paper_ledger(SNAP, [ROW])
        self.assertTrue(r["reconciled"])
        self.assertEqual(r["paper_fill_count"], 1)
        self.assertFalse(r["simulated_fill_origin_independently_verified"])
        self.assertFalse(r["market_source_independently_verified"])
        self.assertFalse(r["production_eligible"])
        self.assertFalse(r["live_order_enabled"])
        self.assertEqual(r["trade_action"], "禁止交易")

    def test_no_fills_never_claims_zero_return_or_success(self):
        r = audit_paper_ledger(SNAP, [])
        self.assertFalse(r["reconciled"])
        self.assertIsNone(r["estimated_net_pnl_twd"])

    def test_invalid_or_missing_snapshot_fails_closed(self):
        for snapshot in (None, {}, {"mode": "LIVE"}, {**SNAP, "observed_at": "naive"}):
            with self.subTest(snapshot=snapshot):
                self.assertFalse(audit_paper_ledger(snapshot, [ROW])["reconciled"])

    def test_mismatched_provenance_time_and_costs_block(self):
        for field, value in (("scan_id", "wrong"), ("daily_realized_net_pnl_twd", 999),
                             ("open_positions", 1), ("journal_scope", "PARTIAL")):
            with self.subTest(field=field):
                self.assertFalse(audit_paper_ledger({**SNAP, field: value}, [ROW])["reconciled"])
        for patch in ({"market_scan_id": "another-scan"},
                      {"exit_time": "2026-11-12T09:05:00+08:00"},
                      {"slippage_estimate_twd": None}):
            with self.subTest(patch=patch):
                self.assertFalse(audit_paper_ledger(SNAP, [{**ROW, **patch}])["reconciled"])

    def test_position_risk_must_reconcile(self):
        positions = [{"symbol": "2409", "entry_price": 25, "original_stop": 24,
                      "shares": 1000}]
        r = audit_paper_ledger({**SNAP, "positions": positions,
                                "open_positions": 1, "open_stop_risk_twd": 1000}, [ROW])
        self.assertTrue(r["reconciled"])
        r = audit_paper_ledger({**SNAP, "positions": positions,
                                "open_positions": 1, "open_stop_risk_twd": 0}, [ROW])
        self.assertIn("OPEN_RISK_MISMATCH", r["errors"])


if __name__ == "__main__":
    unittest.main()
