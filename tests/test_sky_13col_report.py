"""Regression tests for 13-column read-only rendering."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

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

    def test_fugle_ohlc_research_scores_but_no_entry_without_plan(self):
        item = {"symbol": "1101", "name": "台泥", "exchange": "TWSE",
                "source": "Fugle paid bulk snapshot",
                "data_status": "UNVERIFIED_EXECUTION_TIME",
                "last_price": 31.5, "open_price": 30.0,
                "high_price": 32.0, "low_price": 29.8,
                "change_pct": 2.5}
        row = projection(item)
        self.assertIsInstance(row["多方評分"], int)
        self.assertIsInstance(row["空方評分"], int)
        self.assertIn("觀察價 31.50，未驗證", row["即時價"])
        self.assertEqual(row["買進觸發"], "待確認")
        self.assertEqual(row["停利價格"], "待確認")
        self.assertEqual(row["分類"], "X")

    def test_stale_date_cannot_show_paid_observed_price_as_today(self):
        item = {"symbol": "1101", "source": "Fugle paid bulk snapshot",
                "data_status": "SNAPSHOT_DATE_NOT_TODAY",
                "last_price": 33.3}
        self.assertEqual(projection(item)["即時價"], "待確認")

    def test_old_session_rejects_observation_scores(self):
        item = {"symbol": "1101", "source": "Fugle paid bulk snapshot",
                "data_status": "SNAPSHOT_DATE_NOT_TODAY",
                "last_price": 31.5, "open_price": 30.0,
                "high_price": 32.0, "low_price": 29.8}
        self.assertEqual(projection(item)["多方評分"], "—")

    def test_only_existing_strategy_plan_supplies_levels(self):
        from research.sky_daytrade_evidence_bridge import scanner_plans
        scanner = {"deep": [{"symbol": "1101", "strategy_plan": {
            "trigger": 32, "max_entry": 32.2, "stop": 31,
            "target": 34}, "strategy_version": "research"}]}
        plan = scanner_plans(scanner)["1101"]
        item = {"symbol": "1101", "source": "Fugle paid bulk snapshot",
                "data_status": "FRESH_EXECUTED_TRADE", "last_price": 31.5}
        row = projection(item, plan)
        self.assertIn("32.00", row["買進觸發"])
        self.assertIn("31.00", row["停損／失效"])
        self.assertEqual(row["加碼價格"], "待確認")
        self.assertEqual(row["現在動作"], "等待")
        self.assertEqual(projection(item)["買進觸發"], "待確認")

    def test_13col_json_uses_labeled_snapshot_collection_clock(self):
        from research.sky_13col_report import main
        item = {"symbol": "1101", "name": "台泥", "exchange": "TWSE",
                "source": "Fugle paid bulk snapshot", "last_price": 31.2,
                "data_status": "UNVERIFIED_EXECUTION_TIME",
                "snapshot_observed_at": "2026-11-09T11:00:00+08:00",
                "last_trade_time": None}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.json"
            destination = root / "output.json"
            source.write_text(json.dumps(self.source([item])), encoding="utf-8")
            with patch("sys.argv", ["sky_13col_report", "--input", str(source),
                                    "--output", str(root / "out.md"),
                                    "--json-output", str(destination)]):
                main()
            row = json.loads(destination.read_text(encoding="utf-8"))["rows"][0]
            self.assertEqual(row["資料時間"], item["snapshot_observed_at"])
            self.assertEqual(row["資料時間類型"], "快照擷取時間")
            self.assertFalse(row["正式交易資格"])

    def test_nan_never_published(self):
        item = {"symbol": "1101", "last_price": float("nan"),
                "data_status": "FRESH_EXECUTED_TRADE"}
        self.assertEqual(projection(item)["即時價"], "待確認")

    def test_schema_must_match(self):
        with self.assertRaises(ValueError):
            render({"schema": "OTHER", "all_symbols": []})


if __name__ == "__main__":
    unittest.main()
