import unittest
from research.sky_paper_trade_trace import evaluate_paper_journal

ROW = {
    "paper_trade_id": "p-001", "signal_id": "signal-001",
    "market_scan_id": "scan-001", "symbol": "2409",
    "market_data_time": "2026-11-10T09:05:00+08:00",
    "entry_time": "2026-11-10T09:10:00+08:00",
    "exit_time": "2026-11-10T10:20:00+08:00",
    "entry_price": 25, "exit_price": 25.5, "shares": 1000,
    "entry_fee_twd": 8.3, "exit_fee_twd": 8.5, "sale_tax_twd": 38.3,
    "slippage_estimate_twd": 25, "spread_estimate_twd": 20,
    "liquidity_impact_estimate_twd": 15,
    "fill_assumption": "NEXT_BAR_OPEN_ESTIMATE", "source_type": "PAPER_SIMULATION",
}


class TraceTest(unittest.TestCase):
    def test_no_trades_no_fake_performance(self):
        r = evaluate_paper_journal([])
        self.assertEqual(r["paper_journal_status"], "INSUFFICIENT_DATA")
        self.assertIsNone(r["paper_net_pnl_estimate_twd"])
        self.assertFalse(r["real_execution_quality_verified"])

    def test_valid_cost_reconciliation_still_not_market_certified(self):
        r = evaluate_paper_journal([ROW])
        self.assertEqual(r["trade_count"], 1)
        self.assertEqual(r["paper_net_pnl_estimate_twd"], 385.9)
        self.assertTrue(r["paper_cost_arithmetic_reconciled"])
        self.assertFalse(r["after_cost_paper_performance_verified"])
        self.assertFalse(r["market_scan_source_verified"])
        self.assertFalse(r["live_trading_enabled"])

    def test_no_assumed_zero_costs(self):
        for field in ("entry_fee_twd", "exit_fee_twd", "sale_tax_twd",
                      "slippage_estimate_twd", "spread_estimate_twd",
                      "liquidity_impact_estimate_twd"):
            with self.subTest(field=field):
                d = dict(ROW)
                del d[field]
                r = evaluate_paper_journal([d])
                self.assertEqual(r["paper_journal_status"], "REJECTED_INCOMPLETE_OR_INVALID")
                self.assertIsNone(r["paper_net_pnl_estimate_twd"])

    def test_no_fake_fill_or_timezone(self):
        for edit in ({"source_type": "BROKER_FILL"},
                     {"fill_assumption": "REAL_EXECUTED"},
                     {"entry_time": "2026-11-10T09:03:00+08:00"},
                     {"exit_time": "2026-11-10T09:06:00+08:00"},
                     {"market_data_time": "2026-11-10T09:05:00"},
                     {"shares": -1000}):
            with self.subTest(edit=edit):
                r = evaluate_paper_journal([{**ROW, **edit}])
                self.assertEqual(r["paper_journal_status"], "REJECTED_INCOMPLETE_OR_INVALID")

    def test_duplicate_and_invalid_row_reject_all_aggregate(self):
        d = dict(ROW)
        d["paper_trade_id"] = ROW["paper_trade_id"]
        r = evaluate_paper_journal([ROW, d])
        self.assertEqual(r["paper_journal_status"], "REJECTED_INCOMPLETE_OR_INVALID")
        self.assertIsNone(r["paper_net_pnl_estimate_twd"])

    def test_one_invalid_record_disables_total(self):
        d = {**ROW, "paper_trade_id": "p-002", "exit_price": None}
        r = evaluate_paper_journal([ROW, d])
        self.assertEqual(r["trade_count"], 1)
        self.assertIsNone(r["paper_net_pnl_estimate_twd"])
        self.assertFalse(r["paper_cost_arithmetic_reconciled"])


if __name__ == "__main__":
    unittest.main()
