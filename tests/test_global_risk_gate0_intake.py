import unittest
from research.global_risk_gate0.audit import audit, REQUIRED, FIELDS


def sample():
    return {"sources": [{"name": name, **{field: "evidence pending review" for field in FIELDS}}
                        for name in REQUIRED],
            "observations": [{"name": name, "taiwan_session": "2026-11-05",
                              "us_session": "2026-11-04",
                              "published_at": "2026-11-04T16:00:00-05:00",
                              "available_at": "2026-11-04T16:01:00-05:00",
                              "record_evidence": "pending independent verification"}
                             for name in ("SOX", "NASDAQ100", "VIX")]}


class Gate0IntakeTest(unittest.TestCase):
    def test_complete_claims_never_pass_gate(self):
        result = audit(sample())
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["gate0"], "NOT_PROVEN")

    def test_late_and_naive_timestamps_fail_closed(self):
        for value in ("2026-11-05T08:30:01+08:00", "2026-11-05T08:00:00"):
            data = sample()
            data["observations"][0]["available_at"] = value
            self.assertEqual(audit(data)["status"], "HOLD")

    def test_missing_and_duplicate_inputs_fail(self):
        data = sample()
        data["observations"][0] = data["observations"][1].copy()
        self.assertEqual(audit(data)["status"], "HOLD")

    def test_absent_or_malformed_manifest_fails(self):
        for data in ({}, [], {"sources": [None], "observations": [None]}):
            self.assertEqual(audit(data)["status"], "HOLD")

    def test_publication_order_checked(self):
        data = sample()
        data["observations"][0]["available_at"] = "2026-11-04T15:00:00-05:00"
        self.assertEqual(audit(data)["status"], "HOLD")


if __name__ == "__main__":
    unittest.main()
