import unittest
from research.disclosure_pit_gate import audit, validate_event


def valid():
    return {
        "symbol": "2330",
        "event_type": "MONTHLY_REVENUE",
        "period": "2026-10",
        "published_at": "2026-11-06T18:35:00+08:00",
        "observed_at": "2026-11-06T18:40:00+08:00",
        "published_at_source": "issuer announcement",
        "source_url": "https://example.org/disclosure/123",
        "market": "TWSE",
        "timestamp_precision": "MINUTE",
        "evidence_kind": "VERIFIED_EXCHANGE_FILING"
    }


class TestDisclosurePITGate(unittest.TestCase):
    def test_valid_structural_event_never_enables_trading(self):
        r = validate_event(valid(), "2026-11-09T09:05:00+08:00")
        self.assertTrue(r["eligible_for_pit_replay"])
        self.assertFalse(r["source_authenticity_independently_verified"])
        self.assertFalse(r["production_signal"])

    def test_future_publication_is_rejected(self):
        r = validate_event(valid(), "2026-11-06T09:05:00+08:00")
        self.assertIn("LOOK_AHEAD_EVENT", r["failed"])

    def test_late_observation_is_rejected(self):
        e = valid()
        e["observed_at"] = "2026-11-09T10:05:00+08:00"
        r = validate_event(e, "2026-11-09T09:05:00+08:00")
        self.assertIn("NOT_OBSERVED_BY_SIGNAL", r["failed"])

    def test_table_date_or_deadline_is_not_publication(self):
        e = valid()
        e["evidence_kind"] = "LATEST_TABLE_DATE_PROXY"
        e["timestamp_precision"] = "DATE"
        r = validate_event(e, "2026-11-09T09:05:00+08:00")
        self.assertIn("PUBLICATION_EVIDENCE_NOT_VERIFIED", r["failed"])
        self.assertIn("PUBLICATION_TIMESTAMP_PRECISION_INSUFFICIENT", r["failed"])

    def test_earnings_and_wrong_market(self):
        e = valid()
        e["event_type"] = "EARNINGS_REPORT"
        e["market"] = "UNKNOWN"
        self.assertIn("UNSUPPORTED_MARKET", validate_event(e, "2026-11-09T09:05:00+08:00")["failed"])

    def test_missing_timestamp_is_rejected(self):
        e = valid()
        e.pop("published_at")
        r = validate_event(e, "2026-11-09T09:05:00+08:00")
        self.assertIn("INVALID_TIMESTAMP", r["failed"])
        self.assertIn("REQUIRED_EVIDENCE_MISSING", r["failed"])

    def test_naive_timestamp_is_rejected(self):
        e = valid()
        e["published_at"] = "2026-11-06T18:35:00"
        self.assertIn("INVALID_TIMESTAMP", validate_event(e, "2026-11-09T09:05:00+08:00")["failed"])

    def test_audit_fail_closed_with_no_data(self):
        result = audit([], "2026-11-09T09:05:00+08:00")
        self.assertEqual(result["structurally_eligible_for_pit"], 0)
        self.assertEqual(result["verified_issuer_filing_times"], 0)
        self.assertEqual(result["research_state"], "INSUFFICIENT_DATA")
        self.assertFalse(result["production_signal"])


if __name__ == "__main__":
    unittest.main()
