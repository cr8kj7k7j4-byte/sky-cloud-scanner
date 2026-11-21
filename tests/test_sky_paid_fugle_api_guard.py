import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from research.sky_paid_fugle_api_guard import (
    artifact_name, check_reservation, prepare, slots, workflow_request_scope,
    verify_uploaded_reservation,
)


class FugleGuardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 11, 5, 10, 20, tzinfo=timezone.utc)

    def test_empty_reservations_permit_only_preflight(self):
        allowed, reason = check_reservation("fugle-global", self.now, lambda name: [])
        self.assertTrue(allowed)
        self.assertEqual(reason, "CLEAR")

    def test_same_window_claim_blocks(self):
        name = artifact_name("fugle-global", slots(self.now)[0])
        def lookup(key):
            return [{"created_at": self.now.isoformat()}] if key == name else []
        self.assertEqual(check_reservation("fugle-global", self.now, lookup),
                         (False, "RECENT_RESERVATION"))

    def test_previous_window_recent_claim_blocks(self):
        name = artifact_name("fugle-global", slots(self.now)[1])
        def lookup(key):
            return [{"created_at": (self.now - timedelta(seconds=25)).isoformat()}] if key == name else []
        self.assertFalse(check_reservation("fugle-global", self.now, lookup)[0])

    def test_old_previous_window_expired(self):
        old = (self.now - timedelta(seconds=310)).isoformat()
        self.assertTrue(check_reservation("fugle-global", self.now,
                        lambda name: [{"created_at": old}])[0])

    def test_different_scope_different_name(self):
        self.assertNotEqual(artifact_name("a", 3), artifact_name("b", 3))

    def test_api_failure_never_returns_approval(self):
        def fail(name):
            raise RuntimeError("API_UNAVAILABLE")
        with self.assertRaisesRegex(RuntimeError, "API_UNAVAILABLE"):
            check_reservation("fugle-global", self.now, fail)

    def test_malformed_response_rejected(self):
        for response in (None, {}, [None], [{"created_at": "invalid"}]):
            with self.subTest(response=response):
                with self.assertRaises((RuntimeError, ValueError)):
                    check_reservation("fugle-global", self.now, lambda name: response)

    def test_naive_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "NAIVE_TIMESTAMP"):
            slots(datetime(2026, 11, 11))

    def test_distinct_inputs_do_not_block_unrelated_requests(self):
        a = workflow_request_scope("Sky Report", {"inputs": {"symbols": "2330"}})
        b = workflow_request_scope("Sky Report", {"inputs": {"symbols": "2317"}})
        c = workflow_request_scope("Other Workflow", {"inputs": {"symbols": "2330"}})
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(a, workflow_request_scope("Sky Report", {"inputs": {"symbols": "2330"}}))
        self.assertTrue(len(a) < 128)

    def test_invalid_workflow_context_blocks_paid_requests(self):
        with self.assertRaises(ValueError):
            workflow_request_scope("", {"inputs": {}})
        with self.assertRaises(ValueError):
            workflow_request_scope("Sky", {"inputs": "not a mapping"})

    def test_artifact_zip_must_match_unique_nonce_not_only_run_id(self):
        with TemporaryDirectory() as td:
            _, name, local = prepare("sky:mock:same", self.now, lambda n: [],
                                      "424242", Path(td))
            artifact = {"id": 91, "workflow_run": {"id": 424242}, "expired": False}
            def lookup(candidate):
                self.assertEqual(candidate, name)
                return [artifact]
            self.assertEqual(verify_uploaded_reservation(
                "sky:mock:same", "424242", self.now, local, lookup,
                lambda aid: dict(local)), name)
            wrong_nonce = dict(local, claim_nonce="0" * 32)
            with self.assertRaisesRegex(RuntimeError, "ARTIFACT_CLAIM_CONTENT_MISMATCH_claim_nonce"):
                verify_uploaded_reservation(
                    "sky:mock:same", "424242", self.now, local, lookup,
                    lambda aid: wrong_nonce)
            with self.assertRaisesRegex(RuntimeError, "CLAIM_SCOPE_MISMATCH"):
                verify_uploaded_reservation(
                    "sky:mock:other", "424242", self.now, local, lambda n: [], lambda aid: {})
            with self.assertRaisesRegex(RuntimeError, "CLAIM_EXPIRED_OR_FUTURE"):
                verify_uploaded_reservation(
                    "sky:mock:same", "424242", self.now + timedelta(seconds=301),
                    local, lookup, lambda aid: dict(local))

    def test_receipt_without_secrets_or_market_data(self):
        with TemporaryDirectory() as td:
            allowed, name, receipt = prepare("fugle-global", self.now, lambda name: [],
                                              "111", Path(td))
            self.assertTrue(allowed)
            self.assertEqual(name, artifact_name("fugle-global", slots(self.now)[0]))
            self.assertFalse(receipt["production_eligible"])
            self.assertFalse(receipt["automatic_order"])
            self.assertIn("CLAIM_REQUIRED", receipt["status"])
            self.assertTrue((Path(td) / "claim.json").exists())


if __name__ == "__main__":
    unittest.main()
