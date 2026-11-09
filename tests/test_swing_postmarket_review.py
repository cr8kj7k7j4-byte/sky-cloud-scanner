import unittest

from src.swing_postmarket_review import review_rows, render


class SwingPostmarketReviewTests(unittest.TestCase):
    def test_indicative_quotes_and_all_thirteen_columns(self):
        scan = {"generated_at": "2026-11-09T11:46:00+08:00", "snapshot_coverage_pct": 95.92,
                "quote_coverage_pct": 0, "unverified_snapshot_observation_count": 1}
        full = {"observed_symbols": 1, "data": [{
            "symbol": "2303", "name": "聯電", "indicative_last_price": 98.2,
            "last_trade_timestamp": None,
        }]}
        rows = review_rows(scan, full)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]), 13)
        self.assertEqual(rows[0][2], "98.2（未驗證快照）")
        self.assertEqual(rows[0][10], "觀察")
        report = render(scan, full)
        self.assertIn("🔴 禁止新進場", report)
        self.assertIn("多方評分", report)
        self.assertIn("未驗證快照", report)
        self.assertNotIn("A+", report)

    def test_empty_report_matches_required_placeholder(self):
        rows = review_rows({})
        self.assertEqual(len(rows[0]), 13)
        self.assertEqual(rows[0][1], "暫無合格候選")
        self.assertEqual(rows[0][3], "X")
        self.assertEqual(rows[0][10], "等待")
        self.assertIn("暫無合格候選", render({}))


if __name__ == "__main__":
    unittest.main()
