import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import config  # noqa: E402
from engine import Bar, Signal, simulate_trade, size_shares  # noqa: E402
from metrics import summarize  # noqa: E402


def bar(d, o, h, l, c, v=1_000_000):
    return Bar(d, o, h, l, c, v)


class SizingTests(unittest.TestCase):
    def test_risk_limited(self):
        # per-share risk = 2 + 100*0.0045 = 2.45 -> 100000/2.45 = 40816.3 -> 40816 shares
        self.assertEqual(
            size_shares(100, 98, config.COST_PRIMARY_ROUND_TRIP, max_notional=10**9), 40816)

    def test_notional_binds_before_risk(self):
        # Same stop, default 100,000 notional cap -> 1,000 shares, not 2,040.
        self.assertEqual(size_shares(100, 98, config.COST_PRIMARY_ROUND_TRIP), 1000)

    def test_notional_capped(self):
        # tiny stop -> risk allows many shares, notional cap 100,000 / 100 = 1000
        self.assertEqual(size_shares(100, 99.99, 0.0, one_r=5000, max_notional=100_000), 1000)

    def test_invalid_stop_zero(self):
        self.assertEqual(size_shares(100, 100, 0.0), 0)


class TradeTests(unittest.TestCase):
    def setUp(self):
        self.sig = Signal("T", "long", signal_index=0, stop=98.0, target=104.0, max_accept=102.0)

    def test_target_hit(self):
        bars = [bar("d0", 100, 101, 99, 100),
                bar("d1", 100, 101, 99.5, 100.5),   # entry at open 100
                bar("d2", 101, 105, 100.5, 104.5)]  # high >= 104 -> target
        t = simulate_trade(bars, self.sig, 0.0045, max_hold_bars=5)
        self.assertEqual(t.exit_reason, "target")
        self.assertAlmostEqual(t.exit_price, 104.0)
        self.assertAlmostEqual(t.gross_return, 0.04)
        self.assertAlmostEqual(t.net_return, 0.04 - 0.0045)

    def test_stop_first_on_same_bar(self):
        bars = [bar("d0", 100, 101, 99, 100),
                bar("d1", 100, 101, 99, 100),
                bar("d2", 100, 105, 97, 100)]       # both stop and target touched
        t = simulate_trade(bars, self.sig, 0.0045, max_hold_bars=5)
        self.assertEqual(t.exit_reason, "stop")
        self.assertAlmostEqual(t.exit_price, 98.0)

    def test_gap_down_through_stop_fills_at_open(self):
        bars = [bar("d0", 100, 101, 99, 100),
                bar("d1", 100, 101, 99, 100),
                bar("d2", 95, 96, 94, 95)]
        t = simulate_trade(bars, self.sig, 0.0, max_hold_bars=5)
        self.assertEqual(t.exit_reason, "stop")
        self.assertAlmostEqual(t.exit_price, 95.0)

    def test_entry_not_filled_when_gap_above_max_accept(self):
        bars = [bar("d0", 100, 101, 99, 100),
                bar("d1", 103, 104, 102, 103)]      # open 103 > max_accept 102
        self.assertIsNone(simulate_trade(bars, self.sig, 0.0045))

    def test_entry_bar_target_not_taken(self):
        # Entry bar's high reaches the target, but a daily bar cannot prove the order.
        bars = [bar("d0", 100, 101, 99, 100),
                bar("d1", 100, 110, 98.5, 100),     # entry bar: high 110 >= 104, low 98.5 > stop 98
                bar("d2", 100, 100.5, 99.5, 100)]
        t = simulate_trade(bars, self.sig, 0.0045, max_hold_bars=1)
        self.assertEqual(t.exit_reason, "time")

    def test_entry_bar_stop_is_taken(self):
        # Entry-day low breaks the stop: must exit at the stop, not ignore it.
        bars = [bar("d0", 100, 101, 99, 100),
                bar("d1", 100, 101, 97, 99),        # entry bar low 97 <= stop 98
                bar("d2", 100, 100.5, 99.5, 100)]
        t = simulate_trade(bars, self.sig, 0.0, max_hold_bars=5)
        self.assertEqual(t.exit_reason, "stop")
        self.assertAlmostEqual(t.exit_price, 98.0)

    def test_time_exit(self):
        bars = [bar("d0", 100, 101, 99, 100),
                bar("d1", 100, 101, 99.5, 100),
                bar("d2", 100, 101, 99.5, 100.5)]
        t = simulate_trade(bars, self.sig, 0.0, max_hold_bars=1)
        self.assertEqual(t.exit_reason, "time")
        self.assertAlmostEqual(t.exit_price, 100.5)

    def test_short_target(self):
        sig = Signal("S", "short", signal_index=0, stop=102.0, target=96.0, max_accept=98.0)
        bars = [bar("d0", 100, 101, 99, 100),
                bar("d1", 100, 100.5, 99, 99.5),    # entry at open 100 (>= max_accept 98)
                bar("d2", 99, 99.5, 95, 95.5)]      # low <= 96 -> target
        t = simulate_trade(bars, sig, 0.0, max_hold_bars=5)
        self.assertEqual(t.exit_reason, "target")
        self.assertAlmostEqual(t.gross_return, 0.04)


class MetricsTests(unittest.TestCase):
    def test_summary(self):
        s = summarize([0.04, -0.02, 0.03, -0.01])
        self.assertEqual(s["n"], 4)
        self.assertAlmostEqual(s["expectancy"], 0.01)
        self.assertAlmostEqual(s["profit_factor"], 0.07 / 0.03)
        self.assertAlmostEqual(s["win_rate"], 0.5)
        self.assertAlmostEqual(s["max_drawdown"], -0.02)

    def test_empty(self):
        self.assertEqual(summarize([])["n"], 0)


if __name__ == "__main__":
    unittest.main()
