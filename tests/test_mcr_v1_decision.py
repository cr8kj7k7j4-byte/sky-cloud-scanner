import unittest
from dataclasses import replace
from datetime import date, datetime
from zoneinfo import ZoneInfo
from research.mcr_v1_decision import Input, decide, net_rr

def base():
    return Input(
        symbol="TEST", observed_at=datetime(2026, 11, 9, 10, 20, tzinfo=ZoneInfo("Asia/Taipei")),
        price=50.2, prev_trading_date=date(2026, 11, 6), margin_data_date=date(2026, 11, 6),
        margin_ratio=125, margin_balance_lots=1000, previous_close=50, vwap=50.0,
        bid=50.15, ask=50.2, volume_ratio_1m=1.8,
        forced_selloff_observed=True, seller_exhaustion_confirmed=True,
        consecutive_buy_snapshots=True, market_gate_ok=True, phase="P3",
        breakout_level=50.1, retest_low=49.5, resistance_1=52.0, resistance_2=53.0,
        data_fresh_seconds=8, is_daytrade_eligible=True, is_price_limit_locked=False,
        available_cash=100000, portfolio_open_risk=0, open_positions=0,
        daily_net_pnl=0, consecutive_stops=0, execution_cost_covered=True)

class MCRTests(unittest.TestCase):
    def test_ready_is_research_only_and_lot_limited(self):
        result = decide(base())
        self.assertEqual(result.state, "RESEARCH_READY")
        self.assertTrue(result.research_only)
        self.assertEqual(result.quantity_shares, 1000)
        self.assertGreaterEqual(result.rr_primary, 1.5)
        self.assertGreaterEqual(result.rr_stress, 2.0)

    def test_low_margin_alone_never_buys(self):
        r = decide(replace(base(), consecutive_buy_snapshots=False))
        self.assertEqual(r.state, "等待")
        self.assertEqual(r.quantity_shares, 0)

    def test_no_lookahead_margin(self):
        self.assertEqual(decide(replace(base(), margin_data_date=date(2026, 11, 9))).state,"禁止交易")

    def test_daily_kill_switch(self):
        self.assertEqual(decide(replace(base(), consecutive_stops=2)).state,"禁止交易")

    def test_stale_quote(self):
        self.assertEqual(decide(replace(base(), data_fresh_seconds=50)).state,"禁止交易")

    def test_unverified_execution(self):
        self.assertEqual(decide(replace(base(), execution_cost_covered=False)).state,"禁止交易")

    def test_bad_rr(self):
        self.assertEqual(decide(replace(base(), resistance_1=50.8, resistance_2=51)).state,"等待")

    def test_stop_risk_too_large(self):
        self.assertEqual(decide(replace(base(), retest_low=48)).state,"禁止交易")

    def test_outside_price_cap(self):
        self.assertEqual(decide(replace(base(), price=105)).state,"禁止交易")

    def test_no_cash(self):
        self.assertEqual(decide(replace(base(), available_cash=30000)).state,"禁止交易")

    def test_cost_math(self):
        self.assertLess(net_rr(50, 49, 52, .0065), net_rr(50, 49, 52, .0045))

if __name__ == "__main__":
    unittest.main()
