"""Fail-closed tests for W0 run discovery; no network or Fugle calls."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.sky_w0_run_discovery import attest_current_trigger, discover, parse_time

START = parse_time("2026-11-23T05:20:00Z")
END = parse_time("2026-11-23T05:30:00Z")
COMMENT = {"id": 7092354527, "created_at": "2026-11-23T05:22:23Z",
           "issue_url": "https://api.github.com/repos/owner/repo/issues/363",
           "user": {"login": "owner"}, "author_association": "OWNER"}
RUN = {"id": 45119990000, "created_at": "2026-11-23T05:24:00Z",
       "event": "issue_comment", "path": ".github/workflows/sky-chat-bridge.yml",
       "name": "Sky Bridge", "workflow_id": 11,
       "status": "completed", "conclusion": "success",
       "run_attempt": 1, "head_sha": "a" * 40}


class TestW0RunDiscovery(unittest.TestCase):
    def test_candidate_not_attested_as_causal_or_market_capture(self):
        def getter(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            if endpoint.startswith("/actions/runs?"):
                return {"workflow_runs": [RUN], "total_count": 1}
            return {"artifacts": [{"id": 55, "name": "receipt", "digest": "sha256:abc"}],
                    "total_count": 1}
        result = discover("owner/repo", "token", 7092354527, START, END, getter)
        self.assertEqual(result["status"], "HOLD_CANDIDATE_RUN_UNCORRELATED")
        self.assertEqual(result["comment_to_run_status"], "HOLD_UNCORRELATED")
        self.assertEqual(result["market_capture_status"], "HOLD_UNVERIFIED")
        self.assertEqual(result["candidate_runs"][0]["artifacts"][0]["id"], 55)
        self.assertIs(result["automatic_order"], False)

    def test_dispatch_comment_must_be_owner_on_canonical_issue(self):
        invalid_sources = (
            {"issue_url": "https://api.github.com/repos/owner/repo/issues/364"},
            {"issue_url": "https://api.github.com/repos/other/repo/issues/363"},
            {"user": {"login": "someone-else"}},
            {"user": None},
            {"author_association": "CONTRIBUTOR"},
            {"author_association": None},
        )
        for invalid in invalid_sources:
            with self.subTest(invalid=invalid):
                def getter(repo, token, endpoint):
                    if endpoint.startswith("/issues/comments/"):
                        return {**COMMENT, **invalid}
                    return {"workflow_runs": [], "total_count": 0}
                with self.assertRaisesRegex(ValueError, "COMMENT_SOURCE_NOT_OWNER_363"):
                    discover("owner/repo", "token", 7092354527, START, END, getter)

    def test_other_workflow_and_pre_comment_runs_are_not_candidates(self):
        for invalid in (
            {"path": ".github/workflows/other.yml"},
            {"path": None},
            {"created_at": "2026-11-23T05:21:00Z"},
        ):
            with self.subTest(invalid=invalid):
                def getter(repo, token, endpoint):
                    if endpoint.startswith("/issues/comments/"):
                        return COMMENT
                    return {"workflow_runs": [{**RUN, **invalid}], "total_count": 1}
                result = discover("owner/repo", "token", 7092354527, START, END, getter)
                self.assertEqual(result["status"], "HOLD_NO_MATCHING_RUN")
                self.assertEqual(result["candidate_runs"], [])

    def test_no_matching_issue_comment(self):
        def getter(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            return {"workflow_runs": [{**RUN, "event": "workflow_dispatch"}], "total_count": 1}
        result = discover("owner/repo", "token", 7092354527, START, END, getter)
        self.assertEqual(result["status"], "HOLD_NO_MATCHING_RUN")

    def test_incomplete_pages_fail_closed(self):
        def getter(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            return {"workflow_runs": [
                {**RUN, "id": 9000000000 + n + (100 if "&page=2&" in endpoint else 0),
                 "event": "workflow_dispatch"} for n in range(100)],
                "total_count": 300}
        result = discover("owner/repo", "token", 7092354527, START, END, getter, max_pages=2)
        self.assertEqual(result["status"], "HOLD_LISTING_INCOMPLETE")

    def test_invalid_run_sha_and_incomplete_artifact_list_block(self):
        def getter(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            if endpoint.startswith("/actions/runs?"):
                return {"workflow_runs": [RUN], "total_count": 1}
            return {"artifacts": [], "total_count": 2}
        with self.assertRaises(ValueError):
            discover("owner/repo", "token", 7092354527, START, END, getter)
        def getter2(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            return {"workflow_runs": [{**RUN, "head_sha": None}], "total_count": 1}
        with self.assertRaises(ValueError):
            discover("owner/repo", "token", 7092354527, START, END, getter2)

    def test_incomplete_workflow_run_metadata_fails_closed(self):
        for invalid in (
            {"run_attempt": None}, {"run_attempt": 0},
            {"run_attempt": True}, {"run_attempt": "1"},
            {"workflow_id": None}, {"workflow_id": 0},
            {"workflow_id": True}, {"workflow_id": "11"},
            {"name": None}, {"name": ""}, {"name": "  "},
        ):
            with self.subTest(invalid=invalid):
                def getter(repo, token, endpoint):
                    if endpoint.startswith("/issues/comments/"):
                        return COMMENT
                    if endpoint.startswith("/actions/runs?"):
                        return {"workflow_runs": [{**RUN, **invalid}], "total_count": 1}
                    return {"artifacts": [], "total_count": 0}
                with self.assertRaisesRegex(ValueError, "INVALID_WORKFLOW_RUN_METADATA"):
                    discover("owner/repo", "token", 7092354527, START, END, getter)

    def test_missing_or_inconsistent_artifact_count_fails_closed(self):
        # A partial or malformed GitHub response is never complete evidence.
        for artifact_response in (
            {"artifacts": [{"id": 55, "name": "receipt"}]},
            {"artifacts": [{"id": 55, "name": "receipt"}], "total_count": 2},
            {"artifacts": [{"id": 55, "name": "receipt"}], "total_count": True},
            {"artifacts": [], "total_count": -1},
        ):
            with self.subTest(artifact_response=artifact_response):
                def getter(repo, token, endpoint):
                    if endpoint.startswith("/issues/comments/"):
                        return COMMENT
                    if endpoint.startswith("/actions/runs?"):
                        return {"workflow_runs": [RUN], "total_count": 1}
                    return artifact_response
                with self.assertRaisesRegex(ValueError, "INCOMPLETE_ARTIFACT_LIST"):
                    discover("owner/repo", "token", 7092354527, START, END, getter)

    def test_malformed_and_duplicate_artifact_identity_fail_closed(self):
        bad_lists = (
            [None],
            ["invalid"],
            [{"id": 12, "name": "valid"}, None],
            [{"id": None, "name": "receipt"}],
            [{"id": True, "name": "receipt"}],
            [{"id": 0, "name": "receipt"}],
            [{"id": 12, "name": ""}],
            [{"id": 12}],
            [{"id": 12, "name": "first"}, {"id": 12, "name": "second"}],
        )
        for artifacts in bad_lists:
            with self.subTest(artifacts=artifacts):
                def getter(repo, token, endpoint):
                    if endpoint.startswith("/issues/comments/"):
                        return COMMENT
                    if endpoint.startswith("/actions/runs?"):
                        return {"workflow_runs": [RUN], "total_count": 1}
                    return {"artifacts": artifacts, "total_count": len(artifacts)}
                with self.assertRaisesRegex(
                    ValueError, "INVALID_ARTIFACT_IDENTITY|DUPLICATE_ARTIFACT_ID"
                ):
                    discover("owner/repo", "token", 7092354527, START, END, getter)

    def test_run_list_total_contract_fail_closed(self):
        for payload in (
            {"workflow_runs": []},
            {"workflow_runs": [], "total_count": True},
            {"workflow_runs": [], "total_count": -1},
            {"workflow_runs": [RUN], "total_count": 0},
        ):
            with self.subTest(payload=payload):
                def getter(repo, token, endpoint):
                    if endpoint.startswith("/issues/comments/"):
                        return COMMENT
                    return payload
                with self.assertRaisesRegex(
                    ValueError, "INVALID_RUN_LIST_TOTAL|RUN_LIST_TOTAL_MISMATCH"
                ):
                    discover("owner/repo", "token", 7092354527, START, END, getter)

    def test_short_run_page_cannot_claim_complete_listing(self):
        def getter(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            return {"workflow_runs": [], "total_count": 2}
        result = discover("owner/repo", "token", 7092354527, START, END, getter)
        self.assertEqual(result["status"], "HOLD_LISTING_INCOMPLETE")
        self.assertIs(result["listing_complete"], False)

    def test_run_list_total_change_between_pages_fails_closed(self):
        def getter(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            if "&page=1&" in endpoint:
                return {"workflow_runs": [{**RUN, "id": 9000000000 + n, "event": "workflow_dispatch"} for n in range(100)],
                        "total_count": 150}
            return {"workflow_runs": [], "total_count": 151}
        with self.assertRaisesRegex(ValueError, "RUN_LIST_TOTAL_CHANGED"):
            discover("owner/repo", "token", 7092354527, START, END, getter)

    def test_duplicate_run_ids_fail_closed(self):
        for records in (
            [RUN, RUN],
            [RUN, {**RUN, "event": "workflow_dispatch"}],
        ):
            with self.subTest(records=records):
                def getter(repo, token, endpoint):
                    if endpoint.startswith("/issues/comments/"):
                        return COMMENT
                    if endpoint.startswith("/actions/runs?"):
                        return {"workflow_runs": records, "total_count": len(records)}
                    return {"artifacts": [], "total_count": 0}
                with self.assertRaisesRegex(ValueError, "DUPLICATE_RUN_ID"):
                    discover("owner/repo", "token", 7092354527, START, END, getter)

    def test_duplicate_run_id_across_pages_fails_closed(self):
        def getter(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            if "&page=1&" in endpoint:
                return {"workflow_runs": [{**RUN, "event": "workflow_dispatch"}] +
                        [{**RUN, "id": 9000000000 + n, "event": "workflow_dispatch"}
                         for n in range(99)], "total_count": 101}
            return {"workflow_runs": [{**RUN, "event": "workflow_dispatch"}],
                    "total_count": 101}
        with self.assertRaisesRegex(ValueError, "DUPLICATE_RUN_ID"):
            discover("owner/repo", "token", 7092354527, START, END, getter)

    def test_issue_comment_workflow_uses_current_event_identity(self):
        # Contract: a new issue comment must not silently audit an old comment.
        from pathlib import Path
        workflow = Path(".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        self.assertIn("github.event.comment.id || inputs.w0_comment_id || ''", workflow)
        self.assertNotIn("inputs.w0_comment_id || '7092354527'", workflow)
        self.assertIn('test -n "$TARGET_COMMENT_ID" || { echo "W0_COMMENT_ID_REQUIRED" >&2; exit 1; }', workflow)
        self.assertIn("github.event.comment.created_at", workflow)
        self.assertIn('if [ -n "$COMMENT_EVENT_TIME" ]; then', workflow)
        # End must include possible post-comment Actions runs, never future timestamps.
        self.assertIn('datetime.datetime.now(datetime.timezone.utc)', workflow)
        self.assertNotIn('WINDOW_END="$COMMENT_EVENT_TIME"', workflow)
        self.assertIn('datetime.timedelta(minutes=10)', workflow)

    def test_discovery_failure_has_explicit_no_trade_artifact_fallback(self):
        from pathlib import Path
        workflow = Path(".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        self.assertIn("Preserve failed discovery as no-trade evidence", workflow)
        self.assertIn("DISCOVERY_STEP_", workflow)
        self.assertIn('"status": "HOLD_DISCOVERY_FAILED"', workflow)
        self.assertIn('"comment_to_run_status": "HOLD_UNCORRELATED"', workflow)
        self.assertIn('"market_capture_status": "HOLD_UNVERIFIED"', workflow)
        self.assertIn('"trade_action": "禁止交易"', workflow)
        upload = workflow.split("      - name: Upload discovery artifact", 1)[1].split(
            "      - name: Independent same-run identity", 1)[0]
        self.assertIn("if-no-files-found: error", upload)

    def test_current_issue_event_attestation_is_distinct_from_historical_candidates(self):
        event = {"action": "created", "repository": {"full_name": "owner/repo"},
                 "issue": {"number": 363},
                 "comment": {"id": 7092354527, "body": "Sky #363 保全查核",
                             "author_association": "OWNER", "user": {"login": "owner"}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.json"
            path.write_text(json.dumps(event), encoding="utf-8")
            result = attest_current_trigger(
                "owner/repo", 7092354527, "issue_comment", str(path),
                "45192350089", "a" * 40)
            self.assertEqual(result["status"], "PASS_THIS_RUN_TRIGGER_EVENT_ATTESTED_RESEARCH_ONLY")
            self.assertEqual(result["trigger_run_id"], 45192350089)
            self.assertEqual(result["trigger_comment_id"], 7092354527)
            for altered in (
                {"action": "edited"},
                {"issue": {"number": 364}},
                {"repository": {"full_name": "other/repo"}},
                {"comment": {**event["comment"], "id": 7092354528}},
                {"comment": {**event["comment"], "body": "Sky 快掃"}},
                {"comment": {**event["comment"], "user": {"login": "someone"}}},
                {"comment": {**event["comment"], "author_association": "CONTRIBUTOR"}},
            ):
                with self.subTest(altered=altered):
                    path.write_text(json.dumps({**event, **altered}), encoding="utf-8")
                    blocked = attest_current_trigger(
                        "owner/repo", 7092354527, "issue_comment", str(path),
                        "45192350089", "a" * 40)
                    self.assertEqual(blocked["status"], "HOLD_TRIGGER_EVENT_UNATTESTED")
            path.write_text(json.dumps(event), encoding="utf-8")
            for inputs in (
                ("workflow_dispatch", str(path), "45192350089", "a" * 40),
                ("issue_comment", "", "45192350089", "a" * 40),
                ("issue_comment", str(path), "0", "a" * 40),
                ("issue_comment", str(path), "45192350089", "bad_sha"),
            ):
                with self.subTest(inputs=inputs):
                    self.assertEqual(attest_current_trigger(
                        "owner/repo", 7092354527, *inputs)["status"],
                        "HOLD_TRIGGER_EVENT_UNATTESTED")

    def test_independent_readback_requires_exact_same_run_event_attestation(self):
        # Preserve distinct provenance: historical candidate Runs still remain HOLD.
        workflow = Path(".github/workflows/sky-chat-bridge.yml").read_text(encoding="utf-8")
        readback = workflow.split("      - name: Independent same-run identity and SHA256 readback", 1)[1]
        readback = readback.split("      - name: Upload independent readback receipt", 1)[0]
        self.assertIn('W0_DISCOVERY_TRIGGER_ATTESTATION_MISSING', readback)
        self.assertIn('W0_DISCOVERY_TRIGGER_ATTESTATION_MISMATCH', readback)
        self.assertIn('W0_DISCOVERY_TRIGGER_EVENT_UNEXPECTED_PASS', readback)
        self.assertIn('attestation.get("trigger_comment_id")!=obj.get("target_comment_id")', readback)
        self.assertIn('attestation.get("trigger_run_id")!=int(os.environ["GITHUB_RUN_ID"])', readback)
        self.assertIn('attestation.get("trigger_head_sha")!=os.environ["GITHUB_SHA"]', readback)
        self.assertIn('"trigger_event_attestation_status":attestation.get("status")', readback)

    def test_naive_time_and_bad_window_block(self):
        with self.assertRaises(ValueError):
            parse_time("2026-11-23T13:24:00")
        with self.assertRaises(ValueError):
            discover("owner/repo", "token", 7092354527, END, START, lambda *a: None)


if __name__ == "__main__":
    unittest.main()
