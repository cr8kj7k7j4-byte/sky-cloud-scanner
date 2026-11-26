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

    def test_historical_reader_accepts_only_matching_same_run_readback(self):
        import json
        import tempfile
        from datetime import datetime, timezone
        from pathlib import Path
        from src.sky_swing_historical_reader import read_historical_observation
        from src.swing_two_track_acceptance import assess

        timestamp = "2026-11-26T13:40:00+08:00"
        scan = {
            "mode": "swing", "production_strategy": "Sky Swing V1.0",
            "generated_at": timestamp, "universe_count": 2, "quote_count": 0,
            "snapshot_coverage_pct": 100.0, "quote_coverage_pct": 0,
            "unverified_snapshot_observation_count": 2,
            "snapshot_exchange_counts": {"TWSE": 1, "TPEx": 1},
            "source_health": {"official_universe": {"twse": 1, "tpex": 1}},
            "observations_are_trade_signals": False,
            "trade_decision": "禁止新進場", "candidates": [],
        }
        snapshot = {
            "source": "Fugle bulk snapshot",
            "generated_at": timestamp, "observed_symbols": 2,
            "data": [
                {"symbol": "1111", "exchange": "TWSE", "source": "Fugle bulk snapshot",
                 "snapshot_date": "2026-11-26", "strategy_signal": False,
                 "production_eligible": False, "indicative_last_price": 10},
                {"symbol": "2222", "exchange": "TPEx", "source": "Fugle bulk snapshot",
                 "snapshot_date": "2026-11-26", "strategy_signal": False,
                 "production_eligible": False, "indicative_last_price": 11},
            ],
        }
        receipt = {
            "status": "PASS_ARTIFACT_INTEGRITY_RESEARCH_ONLY",
            "run_id": "12345", "head_sha": "a" * 40,
            "mode": "swing", "artifact_name": "sky-swing-live-12345",
            "artifact_id": 9001, "data_timestamp": timestamp,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, obj in (
                ("latest_swing.json", scan),
                ("snapshot_observations_swing.json", snapshot),
                ("two_track_acceptance.json", assess(scan, snapshot)),
            ):
                (root / name).write_text(json.dumps(obj), encoding="utf-8")
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            params = {
                "expected_run_id": "12345", "expected_head_sha": "a" * 40,
                "expected_trade_date": "2026-11-26",
                "observed_at": datetime(2026, 11, 27, tzinfo=timezone.utc),
            }
            ok = read_historical_observation(root, receipt_path, **params)
            self.assertEqual(ok["status"], "PASS_HISTORICAL_RESEARCH_OBSERVATION_ONLY")
            self.assertFalse(ok["new_entry_authorized"])
            self.assertIn("未驗證快照", ok["text"])

            wrong_run = read_historical_observation(
                root, receipt_path, **{**params, "expected_run_id": "99999"}
            )
            self.assertEqual(wrong_run["status"], "HOLD_EVIDENCE")
            self.assertEqual(wrong_run["reason"], "RECEIPT_IDENTITY_MISMATCH")
            old_day = read_historical_observation(
                root, receipt_path, **{**params, "expected_trade_date": "2026-11-25"}
            )
            self.assertEqual(old_day["status"], "HOLD_EVIDENCE")
            scan["observations_are_trade_signals"] = True
            (root / "latest_swing.json").write_text(json.dumps(scan), encoding="utf-8")
            unsafe = read_historical_observation(root, receipt_path, **params)
            self.assertEqual(unsafe["status"], "HOLD_EVIDENCE")

    def test_historical_reader_missing_source_fails_closed(self):
        from datetime import datetime, timezone
        from src.sky_swing_historical_reader import read_historical_observation
        result = read_historical_observation(
            "/this/path/does/not/exist", "/another/missing/receipt",
            expected_run_id="1", expected_head_sha="a" * 40,
            observed_at=datetime.now(timezone.utc),
        )
        self.assertEqual(result["status"], "HOLD_EVIDENCE")
        self.assertIsNone(result["text"])


if __name__ == "__main__":
    unittest.main()
