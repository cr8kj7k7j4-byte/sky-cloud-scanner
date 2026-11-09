"""Prevent false-success daytrade report Artifacts and quote promotion."""
import unittest

from research.sky_13col_report import render, projection
from research.verify_13col_artifact import validate


class TestDaytradeArtifactIntegrity(unittest.TestCase):
    def source(self):
        items = [
            {"exchange": "TWSE", "symbol": "1101", "name": "台泥",
             "source": "Fugle paid bulk snapshot",
             "data_status": "UNVERIFIED_EXECUTION_TIME",
             "last_price": 31.2, "open_price": 30.9,
             "high_price": 31.5, "low_price": 30.5,
             "change_pct": 1.1},
            {"exchange": "TPEx", "symbol": "8088", "name": "測試",
             "source": "NO_SNAPSHOT_ROW", "data_status": "MISSING_QUOTE",
             "last_price": None},
        ]
        return {"schema": "SKY_INFORMATION_FIRST_FULL_UNIVERSE_V1",
                "checked_at_tpe": "2026-11-09T21:24:00+08:00",
                "universe_count": 2, "observed_price_count": 1,
                "fresh_executed_count": 0, "all_symbols": items}

    def out(self, src):
        rows = []
        from research.sky_daytrade_evidence_bridge import observation_evidence
        for item in src["all_symbols"]:
            row = projection(item)
            row["資料來源"] = item["source"]
            row["資料時間"] = item.get("last_trade_time")
            row["資料狀態"] = item["data_status"]
            row["研究分數狀態"] = observation_evidence(item)["status"]
            row["正式交易資格"] = False
            rows.append(row)
        return {"schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                "checked_at_tpe": src["checked_at_tpe"],
                "universe_count": len(rows), "row_count": len(rows),
                "rows": rows, "production_eligible": False}

    def test_all_rows_provenance_and_no_trade(self):
        src = self.source()
        result = validate(src, self.out(src), render(src))
        self.assertEqual(result["json_rows"], 2)
        self.assertTrue(result["research_only"])

    def test_source_must_be_paid(self):
        src = self.source()
        report = self.out(src)
        report["rows"][0]["資料來源"] = "TWSE MIS"
        with self.assertRaisesRegex(ValueError, "DATA_SOURCE_STATUS_MISMATCH"):
            validate(src, report, render(src))

    def test_reject_incomplete_report(self):
        src = self.source()
        report = self.out(src)
        report["rows"] = report["rows"][:1]
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_13COL_UNIVERSE"):
            validate(src, report, render(src))

    def test_reject_unverified_price_without_label(self):
        src = self.source()
        report = self.out(src)
        report["rows"][0]["即時價"] = "31.20"
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_PRICE_LABEL_MISSING"):
            validate(src, report, render(src))

    def test_reject_markdown_truncation(self):
        src = self.source()
        with self.assertRaisesRegex(ValueError, "MARKDOWN_ROW_COUNT_MISMATCH"):
            validate(src, self.out(src), render(src, limit=1))


if __name__ == "__main__":
    unittest.main()
