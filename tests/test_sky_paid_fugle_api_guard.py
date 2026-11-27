import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from research.sky_paid_fugle_api_guard import (
    artifact_name, check_reservation, prepare, slots, workflow_request_scope,
    verify_uploaded_reservation, prepare_monthly, monthly_artifact_name,
)


class FugleGuardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 11, 5, 10, 20, tzinfo=timezone.utc)

    def test_cross_workflow_same_scope_second_request_blocked_without_paid_call(self):
        scope = "sky:live:wholemarket"
        claimed = []
        paid_calls = []
        def lookup(name):
            return [dict(created_at=self.now.isoformat())] if name in claimed else []
        with TemporaryDirectory() as td:
            allowed, name, receipt = prepare(scope, self.now, lookup, "run-A", Path(td))
        self.assertTrue(allowed)
        claimed.append(name)
        second_allowed, reason = check_reservation(scope, self.now, lookup)
        if second_allowed:
            paid_calls.append("UNEXPECTED_PAID_REQUEST")
        self.assertFalse(second_allowed)
        self.assertEqual(reason, "RECENT_RESERVATION")
        self.assertEqual(paid_calls, [])

    def test_two_workflow_entries_share_claim_and_never_issue_second_paid_call(self):
        """Deterministic offline A/B workflow race: zero external or paid API."""
        scope = "sky:live:wholemarket"
        claims = {}
        paid_calls = []
        workflow_names = ("Sky Chat On-Demand Scan Bridge", "Sky Cloud Scanner v0.5 + P0-R")

        def lookup(name):
            return claims.get(name, [])

        with TemporaryDirectory() as td:
            for index, workflow in enumerate(workflow_names):
                allowed, name, receipt = prepare(
                    scope, self.now + timedelta(seconds=index), lookup,
                    workflow, Path(td) / str(index))
                if allowed:
                    claims.setdefault(name, []).append({
                        "created_at": (self.now + timedelta(seconds=index)).isoformat()
                    })
                    paid_calls.append(workflow)
                else:
                    self.assertEqual(receipt["status"], "DUPLICATE_BLOCKED")
                    self.assertEqual(receipt["reason"], "RECENT_RESERVATION")
        self.assertEqual(paid_calls, [workflow_names[0]])

    def test_cross_workflow_claim_blocks_across_utc_slot_boundary(self):
        scope = "sky:live:wholemarket"
        first = datetime(2026, 11, 11, 5, 9, 59, tzinfo=timezone.utc)
        second = first + timedelta(seconds=2)
        first_name = artifact_name(scope, slots(first)[0])
        self.assertNotEqual(slots(first)[0], slots(second)[0])
        self.assertEqual(check_reservation(
            scope, second, lambda name: [
                {"created_at": first.isoformat()}] if name == first_name else []),
            (False, "RECENT_RESERVATION"))

    def test_cross_workflow_artifact_lookup_error_fails_closed(self):
        scope = "sky:live:wholemarket"
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, "ARTIFACT_LOOKUP_UNAVAILABLE"):
                prepare(scope, self.now,
                        lambda name: (_ for _ in ()).throw(
                            RuntimeError("ARTIFACT_LOOKUP_UNAVAILABLE")),
                        "workflow-B", Path(td))

    def test_future_or_corrupt_reservation_never_authorizes_paid_request(self):
        name = artifact_name("sky:live:wholemarket", slots(self.now)[0])
        for timestamp in ("not-a-time", "2026-11-11T05:10:20",
                          (self.now + timedelta(minutes=2)).isoformat()):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises((RuntimeError, ValueError)):
                    check_reservation("sky:live:wholemarket", self.now,
                                      lambda key: [dict(created_at=timestamp)] if key == name else [])

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

    def test_uploaded_claim_naive_or_malformed_timestamp_fails_closed(self):
        with TemporaryDirectory() as td:
            _, name, local = prepare("sky:mock:same", self.now, lambda n: [],
                                      "424242", Path(td))
            artifact = {"id": 91, "workflow_run": {"id": 424242}, "expired": False}
            for timestamp, reason in (
                ("2026-11-11T05:10:20", "CLAIM_TIMEZONE_REQUIRED"),
                ("invalid-date", "INVALID_CLAIM_TIMESTAMP"),
            ):
                with self.subTest(timestamp=timestamp):
                    altered = dict(local, checked_at_utc=timestamp)
                    with self.assertRaisesRegex(RuntimeError, reason):
                        verify_uploaded_reservation(
                            "sky:mock:same", "424242", self.now, altered,
                            lambda candidate: [artifact] if candidate == name else [],
                            lambda aid: dict(altered))
            with self.assertRaisesRegex(RuntimeError, "VERIFY_TIMEZONE_REQUIRED"):
                verify_uploaded_reservation(
                    "sky:mock:same", "424242", self.now.replace(tzinfo=None),
                    local, lambda candidate: [artifact] if candidate == name else [],
                    lambda aid: dict(local))

    def test_remote_reservation_requires_valid_artifact_id_and_document(self):
        with TemporaryDirectory() as td:
            _, name, local = prepare("sky:mock:same", self.now, lambda n: [],
                                      "424242", Path(td))
            for bad_id in (None, "91", True, 0, -1):
                with self.subTest(artifact_id=bad_id):
                    artifact = {"id": bad_id, "workflow_run": {"id": 424242},
                                "expired": False}
                    with self.assertRaisesRegex(RuntimeError, "INVALID_OWN_RESERVATION_ARTIFACT_ID"):
                        verify_uploaded_reservation(
                            "sky:mock:same", "424242", self.now, local,
                            lambda candidate: [artifact] if candidate == name else [],
                            lambda aid: dict(local))
            artifact = {"id": 91, "workflow_run": {"id": 424242}, "expired": False}
            for bad_document in (None, [], "not-a-claim", True):
                with self.subTest(remote=bad_document):
                    with self.assertRaisesRegex(RuntimeError, "INVALID_REMOTE_CLAIM_DOCUMENT"):
                        verify_uploaded_reservation(
                            "sky:mock:same", "424242", self.now, local,
                            lambda candidate: [artifact] if candidate == name else [],
                            lambda aid: bad_document)

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

    def test_matching_local_and_remote_safety_flag_tampering_is_rejected(self):
        """Equal ZIP and local receipts cannot override research-only safety."""
        with TemporaryDirectory() as td:
            _, name, claim = prepare("sky:mock:same", self.now, lambda n: [],
                                      "424242", Path(td))
            artifact = {"id": 91, "workflow_run": {"id": 424242}, "expired": False}
            for changed in (
                {"production_eligible": True},
                {"automatic_order": True},
                {"production_eligible": None},
                {"automatic_order": None},
            ):
                with self.subTest(changed=changed):
                    altered = dict(claim, **changed)
                    with self.assertRaisesRegex(RuntimeError, "INVALID_LOCAL_CLAIM_SAFETY_FLAGS"):
                        verify_uploaded_reservation(
                            "sky:mock:same", "424242", self.now, altered,
                            lambda candidate: [artifact] if candidate == name else [],
                            lambda aid: dict(altered))
            altered = dict(claim, reason="UNVERIFIED")
            with self.assertRaisesRegex(RuntimeError, "INVALID_LOCAL_CLAIM_REASON"):
                verify_uploaded_reservation(
                    "sky:mock:same", "424242", self.now, altered,
                    lambda candidate: [artifact] if candidate == name else [],
                    lambda aid: dict(altered))

    def test_remote_claim_metadata_tampering_is_rejected(self):
        """A matching nonce alone must not certify altered claim safety fields."""
        with TemporaryDirectory() as td:
            _, name, local = prepare("sky:mock:same", self.now, lambda n: [],
                                      "424242", Path(td))
            artifact = {"id": 91, "workflow_run": {"id": 424242}, "expired": False}
            for key, altered_value in (
                ("checked_at_utc", "2026-11-11T05:09:00+00:00"),
                ("production_eligible", True),
                ("automatic_order", True),
                ("reason", "UNVERIFIED"),
            ):
                with self.subTest(key=key):
                    remote = dict(local, **{key: altered_value})
                    with self.assertRaisesRegex(
                        RuntimeError, "ARTIFACT_CLAIM_CONTENT_MISMATCH_" + key
                    ):
                        verify_uploaded_reservation(
                            "sky:mock:same", "424242", self.now, local,
                            lambda candidate: [artifact] if candidate == name else [],
                            lambda aid: remote)

    def test_competing_workflow_claim_fails_closed_before_paid_call(self):
        with TemporaryDirectory() as td:
            _, name, local = prepare("sky:mock:same", self.now, lambda n: [],
                                      "424242", Path(td))
            own = {"id": 91, "workflow_run": {"id": 424242}, "expired": False}
            other = {"id": 92, "workflow_run": {"id": 999999}, "expired": False}
            with self.assertRaisesRegex(RuntimeError, "COMPETING_RESERVATION_CLAIM"):
                verify_uploaded_reservation(
                    "sky:mock:same", "424242", self.now, local,
                    lambda candidate: [own, other] if candidate == name else [],
                    lambda aid: dict(local))
            with self.assertRaisesRegex(RuntimeError, "INVALID_RESERVATION_ARTIFACT_LIST"):
                verify_uploaded_reservation(
                    "sky:mock:same", "424242", self.now, local,
                    lambda candidate: [own, None] if candidate == name else [],
                    lambda aid: dict(local))

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


class MonthlyBillingRateGuardTests(unittest.TestCase):
    """Monthly subscription must not enforce a cross-command 300s cooldown."""

    def test_distinct_runs_same_second_have_separate_receipts(self):
        now = datetime(2026, 11, 27, 3, 55, tzinfo=timezone.utc)
        with TemporaryDirectory() as td:
            a = prepare_monthly("sky:live:wholemarket", now, "111", "1", Path(td))
            b = prepare_monthly("sky:live:wholemarket", now, "222", "1", Path(td))
        self.assertTrue(a[0] and b[0])
        self.assertNotEqual(a[1], b[1])
        self.assertEqual(a[2]["billing_control"], "MONTHLY_RATE_LIMIT_ONLY")
        self.assertEqual(b[2]["reason"], "CLEAR")

    def test_monthly_receipt_requires_exact_same_run_zip(self):
        now = datetime(2026, 11, 27, 3, 55, tzinfo=timezone.utc)
        with TemporaryDirectory() as td:
            _, name, local = prepare_monthly(
                "sky:live:wholemarket", now, "111", "2", Path(td))
            own = {"id": 91, "workflow_run": {"id": 111}, "expired": False}
            lookup = lambda candidate: [own] if candidate == name else []
            self.assertEqual(verify_uploaded_reservation(
                "sky:live:wholemarket", "111", now, local, lookup,
                lambda aid: dict(local), monthly=True, attempt="2"), name)
            with self.assertRaisesRegex(RuntimeError, "MONTHLY_RATE_CONTROL_RECEIPT_REQUIRED"):
                verify_uploaded_reservation(
                    "sky:live:wholemarket", "111", now, local, lookup,
                    lambda aid: dict(local), monthly=True, attempt="1")
            with self.assertRaisesRegex(RuntimeError, "ARTIFACT_CLAIM_CONTENT_MISMATCH_claim_nonce"):
                verify_uploaded_reservation(
                    "sky:live:wholemarket", "111", now, local, lookup,
                    lambda aid: dict(local, claim_nonce="0"*32),
                    monthly=True, attempt="2")

    def test_invalid_monthly_attempt_is_rejected(self):
        for run_id, attempt in (("", "1"), ("a", "1"), ("123", "0"), ("123", "x")):
            with self.assertRaises(ValueError):
                monthly_artifact_name("scope", run_id, attempt)


class PaidWorkflowWiringRegressionTests(unittest.TestCase):
    """Offline guard against removing paid preflight from the four live entrypoints."""

    WORKFLOWS = (
        ".github/workflows/scan.yml",
        ".github/workflows/sky-chat-bridge.yml",
        ".github/workflows/sky-full-market-private.yml",
        ".github/workflows/sky-fugle-stage2-probe.yml",
    )

    def test_paid_workflows_share_one_serial_concurrency_group(self):
        for path in self.WORKFLOWS:
            with self.subTest(path=path):
                content = Path(path).read_text(encoding="utf-8")
                if path.endswith("/sky-chat-bridge.yml"):
                    self.assertIn("format('sky-alert-readonly-{0}', github.event.comment.id)", content)
                    self.assertIn("|| 'sky-fugle-paid-global-research-v1-live-wholemarket'", content)
                else:
                    self.assertIn("group: sky-fugle-paid-global-research-v1-live-wholemarket", content)
                self.assertIn("cancel-in-progress: false", content)

    def test_paid_workflows_require_verified_claim_before_paid_execution(self):
        for path in self.WORKFLOWS:
            with self.subTest(path=path):
                content = Path(path).read_text(encoding="utf-8")
                self.assertIn("python -m research.sky_paid_fugle_api_guard --scope", content)
                self.assertIn("--verify", content)
                self.assertIn("steps.verify_claim.outcome == 'success'", content)
                self.assertIn("steps.guard.outputs.allowed == 'true'", content)
                self.assertIn("path: output/fugle_api_guard/claim.json", content)
                self.assertLess(content.index("id: guard"), content.index("id: verify_claim"))

    def test_monthly_core_workflows_retain_claim_readback_and_concurrency(self):
        for path in (".github/workflows/scan.yml",
                     ".github/workflows/sky-chat-bridge.yml",
                     ".github/workflows/swing-live-scan.yml"):
            content = Path(path).read_text(encoding="utf-8")
            self.assertIn("--monthly-rate-limited", content)
            self.assertIn("SKY_FUGLE_MONTHLY_RATE_CONTROL", content)
            self.assertNotIn("SKY_PAID_ATOMIC_ENFORCE:", content)
            self.assertIn("cancel-in-progress: false", content)
            self.assertIn("--verify", content)

    def test_scan_formal_cron_is_retired_but_manual_path_remains(self):
        # W0 #363 user decision on 2026-11-26: no formal timed scans.
        # Guard against accidental cron reactivation while preserving
        # manual dispatch, paid Claim verification and fail-closed safety.
        content = Path(self.WORKFLOWS[0]).read_text(encoding="utf-8")
        header = content.split("\npermissions:\n", 1)[0]
        self.assertNotIn("\n  schedule:\n", header)
        self.assertNotIn("- cron:", header)
        self.assertIn("\n  workflow_dispatch:", header)
        self.assertIn("\n  push:", header)


if __name__ == "__main__":
    unittest.main()
