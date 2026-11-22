import csv
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import fetch_fugle_daily  # noqa: E402
import run_backtest  # noqa: E402
from engine import Bar  # noqa: E402
from strategy import brk20_signals  # noqa: E402


def synthetic_bars():
    """80 gently rising bars, then a breakout on bar index 80 and a clean target on 81."""
    rows = []
    start_date = 2025
    for i in range(80):
        c = 50 + i * 0.01
        rows.append(("d%03d" % i, c - 0.01, c + 0.05, c - 0.05, c, 2_000_000))
    # index 80: signal bar. close 51.00 > 20-day high (~50.84) and > MA60 (~50.4).
    rows.append(("d080", 50.80, 51.10, 50.95, 51.00, 2_000_000))
    # index 81: entry open 51.02 <= trigger*1.005 (~51.09). Target = 51.02 + 2*0.07 = 51.16.
    # Entry bar low 51.00 > stop 50.95, so no stop; target is not taken on the entry bar.
    rows.append(("d081", 51.02, 51.10, 51.00, 51.05, 2_000_000))
    # index 82: opens below target 51.16, high 51.50 -> target fills at 51.16.
    rows.append(("d082", 51.10, 51.50, 51.05, 51.40, 2_000_000))
    return [Bar(*r) for r in rows]


class StrategyTests(unittest.TestCase):
    def test_breakout_signal_detected(self):
        bars = synthetic_bars()
        sigs = brk20_signals("TEST", bars)
        self.assertTrue(any(s.signal_index == 80 for s in sigs))

    def test_low_volume_filtered(self):
        bars = [Bar(b.date, b.open, b.high, b.low, b.close, 100) for b in synthetic_bars()]
        self.assertEqual(brk20_signals("TEST", bars), [])


class FetchHelperTests(unittest.TestCase):
    def test_url_has_documented_parameters(self):
        url = fetch_fugle_daily.build_url("2330", "2025-01-01", "2025-12-31")
        self.assertIn("/marketdata/v1.0/stock/historical/candles/2330", url)
        self.assertIn("timeframe=D", url)
        self.assertIn("from=2025-01-01", url)
        self.assertIn("to=2025-12-31", url)

    def test_404_means_no_data_not_fatal(self):
        import io
        import unittest.mock as mock
        err = fetch_fugle_daily.urllib.error.HTTPError(
            "u", 404, "Not Found", {}, io.BytesIO(b""))
        with mock.patch.object(fetch_fugle_daily.urllib.request, "urlopen", side_effect=err):
            self.assertEqual(fetch_fugle_daily.fetch_chunk("3717", "2024-09-01", "2024-12-31", "k"), [])

    def test_chunks_are_under_one_year(self):
        from datetime import date
        for s, e in fetch_fugle_daily.CHUNKS:
            d0 = date.fromisoformat(s)
            d1 = date.fromisoformat(e)
            self.assertLess((d1 - d0).days, 366)

    def test_universe_keeps_ordinary_stocks_only(self):
        payload = {"data": [
            {"symbol": "2330", "type": "EQUITY"},
            {"symbol": "0050", "type": "EQUITY"},     # ETF, excluded
            {"symbol": "00878", "type": "EQUITY"},    # ETF, excluded
            {"symbol": "2330A", "type": "EQUITY"},    # not 4 digits, excluded
            {"symbol": "1101", "type": "INDEX"},      # wrong type, excluded
            {"symbol": "6488", "type": "EQUITY"},
        ]}
        self.assertEqual(fetch_fugle_daily.parse_universe(payload), ["2330", "6488"])

    def test_skips_incomplete_rows_without_fabricating(self):
        rows = fetch_fugle_daily.to_rows([
            {"date": "2025-01-02T00:00:00", "open": None, "high": 1, "low": 1, "close": None, "volume": 0},
            {"date": "2025-01-03", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], "2025-01-03")


class PipelineTests(unittest.TestCase):
    def test_end_to_end_on_synthetic_csv(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "TEST.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["date", "open", "high", "low", "close", "volume"])
                for b in synthetic_bars():
                    w.writerow([b.date, b.open, b.high, b.low, b.close, b.volume])
            out = run_backtest.run(d, cost_rate=0.0045)["trades"]
            self.assertEqual(len(out), 1)
            day, tr = out[0]
            self.assertEqual(day, "d080")
            self.assertEqual(tr.exit_reason, "target")
            self.assertAlmostEqual(tr.exit_price, 51.16)

    def test_promotion_never_passes_in_v1(self):
        empty = {k: {"n": 0, "expectancy": None, "profit_factor": None,
                     "win_rate": None, "max_drawdown": None}
                 for k in ("train", "validation", "research_test_2026")}
        verdict = run_backtest.promotion_check(empty, empty)
        self.assertNotEqual(verdict["PASS_RESEARCH"], True)
        self.assertTrue(verdict["PASS_RESEARCH"].startswith(("NOT_EVALUABLE", "FAIL")))


if __name__ == "__main__":
    unittest.main()
