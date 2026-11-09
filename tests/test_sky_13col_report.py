"""Regression tests for 13-column read-only rendering."""
import unittest

from research.sky_13col_report import COLUMNS, projection, render


class TestSky13Col(unittest.TestCase):
    def source(self, items):
        return {"schema": "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1",
                "checked_at_tpe": "2026-11-09T11:00:00+08:00",
                "universe_count": len(items), "observed_price_count": len(items),
                "fresh_executed_count": 0, "all_symbols": items}

    def test_unverified_price_never_called_live(self):
        item = {"symbol": "1101", "name": "台泥", "last_price": 31.2,
                "data_status": "UNVERIFIED_EXECUTION_TIME"}
        projected = projection(item)
        self.assertEqual(projected["即時價"], "待確認")
        self.assertEqual(projected["現在動作"], "等待")
        self.assertEqual(projected["多方評分"], "—")
        self.assertEqual(len(projected), 13)

    def test_fresh_price_is_observed_not_trade_approval(self):
        item = {"symbol": "1101", "name": "台泥", "last_price": 31.2,
                "data_status": "FRESH_EXECUTED_TRADE"}
        projected = projection(item)
        self.assertEqual(projected["即時價"], "31.20")
        self.assertEqual(projected["分類"], "X")
        self.assertEqual(projected["方向"], "不交易")

    def test_empty_source_fallback(self):
        md = render(self.source([]))
        self.assertIn("暫無合格候選", md)
        self.assertIn("禁止新進場", md)
        self.assertTrue(all(x in md for x in COLUMNS))

    def test_full_universe_is_default_even_with_ranked_preview(self):
        items = [{"symbol": str(1000 + i), "exchange": "TWSE", "name": f"股{i}",
                  "last_price": 25.0, "data_status": "UNVERIFIED_EXECUTION_TIME"}
                 for i in range(45)]
        report = self.source(items)
        report["ranked_observations"] = items[:5]
        md = render(report)
        self.assertEqual(md.count("| X | 不交易 |"), 45)
        self.assertIn("| 1044 | 股44 |", md)
        preview = render(report, limit=30)
        self.assertEqual(preview.count("| X | 不交易 |"), 30)
        self.assertNotIn("| 1044 | 股44 |", preview)

    def test_nan_never_published(self):
        item = {"symbol": "1101", "last_price": float("nan"),
                "data_status": "FRESH_EXECUTED_TRADE"}
        self.assertEqual(projection(item)["即時價"], "待確認")

    def test_schema_must_match(self):
        with self.assertRaises(ValueError):
            render({"schema": "OTHER", "all_symbols": []})


if __name__ == "__main__":
    unittest.main()
