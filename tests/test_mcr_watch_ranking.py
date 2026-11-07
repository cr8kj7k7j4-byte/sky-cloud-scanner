import unittest
from research.mcr_watch_ranking import build_watchlist


class WatchlistRankingTests(unittest.TestCase):
    def setUp(self):
        self.margin = {
            str(1000 + i): {"stock_id": str(1000 + i), "date": "2026-11-06",
                            "margin_maintenance": 120, "margin_balance": 200}
            for i in range(250)
        }

    def test_all_rows_not_top_n(self):
        first = build_watchlist(self.margin, page_size=200)
        second = build_watchlist(self.margin, page=2, page_size=200)
        self.assertEqual(first["total"], 250)
        self.assertEqual(first["total_pages"], 2)
        self.assertEqual(len(first["rows"]) + len(second["rows"]), 250)
        self.assertTrue(all(not r["trade_eligible"] for r in first["rows"]))

    def test_volume_descending(self):
        snapshots = [
            {"stock_id": "1001", "total_volume": 500, "close": 40, "date": "2026-11-09 09:10:00"},
            {"stock_id": "1002", "total_volume": 1000, "close": 20, "date": "2026-11-09 09:10:00"},
        ]
        feed = build_watchlist(self.margin, snapshots, sort_by="volume")
        self.assertEqual([r["stock_id"] for r in feed["rows"][:2]], ["1002", "1001"])

    def test_unverified_ev_never_inferred(self):
        evidence = {"1001": {"net_expectancy_per_trade_pct": 999}}
        feed = build_watchlist(self.margin, evidence=evidence)
        self.assertEqual(feed["sort_effective"], "volume")
        self.assertTrue(all(r["net_expectancy_per_trade_pct"] is None for r in feed["rows"]))

    def test_verified_ev_is_first_and_audited(self):
        evidence = {"1001": {
            "verification": "PASS", "point_in_time": True,
            "costs_included": True, "out_of_sample": True,
            "forward_trading_days": 20, "independent_trades": 200,
            "market_regimes": 2, "data_completeness_pct": 95,
            "max_symbol_concentration_pct": 20,
            "net_expectancy_per_trade_pct": 0.18,
        }}
        feed = build_watchlist(self.margin, evidence=evidence)
        self.assertEqual(feed["rows"][0]["stock_id"], "1001")
        self.assertTrue(feed["rows"][0]["expectancy_verified"])
        self.assertFalse(feed["rows"][0]["trade_eligible"])

    def test_stale_margin_not_included(self):
        self.margin["1001"]["margin_maintenance"] = 135
        feed = build_watchlist(self.margin)
        self.assertEqual(feed["total"], 249)

    def test_pagination_invalid(self):
        with self.assertRaises(ValueError):
            build_watchlist(self.margin, page=0)


if __name__ == "__main__":
    unittest.main()
