"""W0 #363: no-network, independently verified old history -> new mobile report."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import copy
import hashlib
import json

from scripts.sky_reuse_verified_historical_artifact import (
    PASS, HISTORY_PASS, verify_history, attach_to_report,
)

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 28, 2, 0, tzinfo=TPE)
SHA = "a" * 40
RUN = "46045172892"
ID = 15222195474


class VerifiedHistoryReuseTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "source"
        self.receipt = root / "receipt"
        self.report = root / "report"
        for p in (self.source, self.receipt, self.report):
            p.mkdir()
        self.history = {
            "schema": "SKY_FUGLE_HISTORICAL_5M_RESEARCH_V1",
            "symbol": "3717", "source_date": "2026-11-27",
            "status": HISTORY_PASS, "completed_bar_count": 1,
            "kbar_evidence_level": "OBSERVATION_ONLY_SPARSE_5M_BARS",
            "research_report_available": True,
            "bars": [{"start_tpe": "2026-11-27T13:30:00+08:00",
                      "open": 10, "high": 11, "low": 9, "close": 10,
                      "volume_lots": 5, "provider_cumulative_average": 10}],
            "independent_vwap_certified": False,
            "executed_trade_time_certified": False,
            "execution_authorized": False, "production_eligible": False,
            "automatic_order": False,
        }
        self.payload = {
            "schema": "SKY_3717_HISTORICAL_ONE_DAY_PROBE_V1",
            "symbol": "3717", "source_date": "2026-11-27",
            "http_status": 200, "row_count": 1,
            "status": HISTORY_PASS,
            "provider_metadata": {
                "symbol": "3717", "exchange": "TWSE", "timeframe": "5"
            },
            "historical_5m_research": self.history,
        }
        self.audit = {
            "schema": "SKY_5M_TRADES_BOUND_SOURCE_V1",
            "symbol": "3717", "observed_at_tpe": NOW.isoformat(),
            "five_minute_status": "HOLD", "trades_status": "HOLD",
            "volume_status": "HOLD", "vwap_status": "HOLD",
            "execution_authorized": False, "production_eligible": False,
            "automatic_order": False,
            "historical_5m_research": {"status": "HOLD_HISTORICAL_5M_SOURCE"},
        }
        self._write_source()
        self._write_report()

    def _write_source(self):
        a = self.source / "3717-5m-source.json"
        a.write_text(json.dumps(self.payload, ensure_ascii=False), encoding="utf-8")
        b = self.source / "3717-5m-source.md"
        b.write_text("historic proof", encoding="utf-8")
        x = {
            "schema": "SKY_SINGLE_STOCK_SAME_RUN_READBACK_V1",
            "run_id": RUN, "attempt": "1", "head_sha": SHA,
            "artifact_id": ID, "symbol": "3717",
            "status": "PASS_ARTIFACT_INTEGRITY_RESEARCH_ONLY",
            "file_count": 2, "execution_authorized": False,
            "automatic_order": False, "production_eligible": False,
            "file_sha256": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (a, b)
            },
        }
        (self.receipt / "receipt.json").write_text(
            json.dumps(x), encoding="utf-8")

    def _write_report(self):
        (self.report / "3717-5m-source.json").write_text(
            json.dumps(self.audit), encoding="utf-8")
        (self.report / "3717.json").write_text(
            json.dumps({
                "schema": "SKY_UNIFIED_SINGLE_STOCK_RESEARCH_V1",
                "symbol": "3717", "observation": {"score_direction": "觀察"},
                "source_audit": self.audit, "execution_authorized": False
            }), encoding="utf-8")

    def verify(self):
        return verify_history(
            self.source, self.receipt, symbol="3717", run_id=RUN,
            head_sha=SHA, artifact_id=ID, observed_at=NOW)

    def test_dated_historical_artifact_reused_without_fugle_and_reports_updated(self):
        ev = self.verify()
        self.assertEqual(ev["status"], PASS)
        self.assertEqual(ev["request_count_for_reuse"], 0)
        result = attach_to_report(
            report_dir=self.report, evidence=ev, symbol="3717")
        self.assertEqual(result["status"], PASS)
        audit = json.loads((self.report / "3717-5m-source.json").read_text())
        unified = json.loads((self.report / "3717.json").read_text())
        self.assertEqual(audit["historical_5m_research"]["status"], HISTORY_PASS)
        self.assertTrue(audit["historical_5m_research"]["reused_no_new_fugle_http"])
        self.assertEqual(unified["source_audit"]["historical_5m_research"]["source_run_id"], RUN)
        self.assertIn("2026-11-27", (self.report / "3717.md").read_text())
        self.assertFalse(unified["execution_authorized"])
        self.assertFalse(audit["historical_5m_research"]["independent_vwap_certified"])

    def test_tampered_source_byte_rejected(self):
        f = self.source / "3717-5m-source.json"
        f.write_text(f.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "DIGEST_MISMATCH"):
            self.verify()

    def test_receipt_identity_wrong_run_sha_or_artifact_rejected(self):
        for changes in ({"run_id": "9999"}, {"head_sha": "b" * 40},
                        {"artifact_id": 4}, {"execution_authorized": True},
                        {"status": "HOLD"}):
            f = self.receipt / "receipt.json"
            original = json.loads(f.read_text())
            f.write_text(json.dumps({**original, **changes}))
            with self.assertRaisesRegex(ValueError, "UNVERIFIED_HISTORICAL_READBACK_IDENTITY"):
                self.verify()
            f.write_text(json.dumps(original))

    def test_foreign_symbol_or_false_vwap_rejected_even_with_matched_digest(self):
        for alter in (
                lambda p: p["provider_metadata"].update(symbol="2330"),
                lambda p: p["historical_5m_research"].update(independent_vwap_certified=True),
                lambda p: p.update(status="PASS_EXECUTION_AUTHORIZED")):
            obj = copy.deepcopy(self.payload)
            alter(obj)
            self.payload = obj
            self._write_source()
            with self.assertRaisesRegex(ValueError, "IDENTITY_OR_SAFETY"):
                self.verify()
            self.payload = {
                "schema": "SKY_3717_HISTORICAL_ONE_DAY_PROBE_V1",
                "symbol": "3717", "source_date": "2026-11-27",
                "http_status": 200, "row_count": 1, "status": HISTORY_PASS,
                "provider_metadata": {
                    "symbol": "3717", "exchange": "TWSE", "timeframe": "5"
                }, "historical_5m_research": self.history,
            }
            self._write_source()

    def test_old_history_is_dated_observation_not_current_trade(self):
        ev = self.verify()
        self.assertFalse(ev["execution_authorized"])
        self.assertFalse(ev["production_eligible"])
        self.assertEqual(ev["source_date"], "2026-11-27")
        self.assertEqual(ev["http_status_original_observation"], 200)

    def test_current_report_must_retain_no_order_flags(self):
        ev = self.verify()
        self.audit["execution_authorized"] = True
        self._write_report()
        with self.assertRaisesRegex(ValueError, "CURRENT_REPORT_NOT_RESEARCH_ONLY"):
            attach_to_report(report_dir=self.report, evidence=ev, symbol="3717")


if __name__ == "__main__":
    import unittest
    unittest.main()
