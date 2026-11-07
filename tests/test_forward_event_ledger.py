import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from research.forward_event_ledger import build_ledger, provisional_event_key

SOURCES = {
    "twse_revenue_latest": [
        {"公司代號": "2330", "資料年月": "11510", "營業收入-當月營收": "120"},
        {"公司代號": "1101", "資料年月": "11510", "營業收入-當月營收": "150"}
    ],
    "tpex_revenue_latest": [
        {"公司代號": "8088", "資料年月": "11510", "營業收入-當月營收": "120"}
    ],
    "twse_material_latest": [
        {"公司代號": "2330", "主旨 ": "測試訊息", "發言日期": "1151108",
         "發言時間": "10:30:00", "說明": "甲"}
    ],
    "tpex_material_latest": [
        {"SecuritiesCompanyCode": "8088", "主旨": "測試訊息", "發言日期": "1151108",
         "發言時間": "11:40:00", "說明": "乙"}
    ],
}


def snapshot(folder, data, observed):
    folder.mkdir(parents=True, exist_ok=True)
    info = {}
    for label, rows in data.items():
        payload = json.dumps(rows, ensure_ascii=False).encode("utf-8")
        (folder / (label + ".raw.json")).write_bytes(payload)
        info[label] = {
            "fetch_status": "CAPTURED",
            "http_status": 200,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "raw_file": label + ".raw.json",
            "observed_at_utc": observed,
        }
    (folder / "manifest.json").write_text(json.dumps({
        "status": "SNAPSHOT_CAPTURED_RESEARCH_ONLY",
        "production_signal": False, "historical_pit_event_count": 0,
        "source_results": info,
    }), encoding="utf-8")


class LedgerTest(unittest.TestCase):
    def test_first_snapshot_records_observation_not_publication(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            snapshot(folder, SOURCES, "2026-11-08T05:40:00+08:00")
            a = build_ledger(folder)
            self.assertEqual(a["unique_provisional_events"], 5)
            self.assertEqual(a["counts"]["added"], 5)
            self.assertEqual(a["eligible_trade_events"], 0)
            self.assertFalse(a["production_signal"])
            self.assertFalse(a["historical_pit_certified"])
            self.assertTrue(all(x["issuer_original_published_at"] is None for x in a["events"].values()))

    def test_repeated_snapshot_does_not_multiply_events(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            snapshot(folder, SOURCES, "2026-11-08T05:40:00+08:00")
            a = build_ledger(folder)
            snapshot(folder, SOURCES, "2026-11-08T06:00:00+08:00")
            b = build_ledger(folder, a)
            self.assertEqual(b["counts"]["unchanged"], 5)
            self.assertEqual(b["unique_provisional_events"], 5)
            self.assertEqual(b["counts"]["added"], 0)

    def test_changed_revenue_creates_revision_not_new_trade(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            snapshot(folder, SOURCES, "2026-11-08T05:40:00+08:00")
            a = build_ledger(folder)
            altered = {k:[dict(x) for x in v] for k, v in SOURCES.items()}
            altered["twse_revenue_latest"][0]["營業收入-當月營收"] = "125"
            snapshot(folder, altered, "2026-11-08T06:00:00+08:00")
            b = build_ledger(folder, a)
            self.assertEqual(b["counts"]["revision"], 1)
            self.assertEqual(b["counts"]["unchanged"], 4)
            self.assertEqual(b["unique_provisional_events"], 5)
            self.assertEqual(b["eligible_trade_events"], 0)

    def test_source_hash_corruption_fails(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            snapshot(folder, SOURCES, "2026-11-08T05:40:00+08:00")
            (folder / "tpex_revenue_latest.raw.json").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                build_ledger(folder)

    def test_no_fake_identity(self):
        with self.assertRaisesRegex(ValueError, "issuer identifier"):
            provisional_event_key("twse_revenue_latest", {"資料年月":"11510"})

    def test_out_of_order_capture_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            snapshot(folder, SOURCES, "2026-11-08T06:00:00+08:00")
            a = build_ledger(folder)
            snapshot(folder, SOURCES, "2026-11-08T05:00:00+08:00")
            with self.assertRaisesRegex(ValueError, "older"):
                build_ledger(folder, a)


if __name__ == "__main__":
    unittest.main()
