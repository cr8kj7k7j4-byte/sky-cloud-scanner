"""Fail-closed tests for W0 run discovery; no network or Fugle calls."""
import unittest
from scripts.sky_w0_run_discovery import discover, parse_time

START = parse_time("2026-11-23T05:20:00Z")
END = parse_time("2026-11-23T05:30:00Z")
COMMENT = {"id": 7092354527, "created_at": "2026-11-23T05:22:23Z"}
RUN = {"id": 45119990000, "created_at": "2026-11-23T05:24:00Z",
       "event": "issue_comment", "name": "Sky Bridge", "workflow_id": 11,
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
            return {"workflow_runs": [{**RUN, "id": 9000000000 + n, "event": "workflow_dispatch"} for n in range(100)], "total_count": 300}
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
        self.assertIn("github.event.comment.id || inputs.w0_comment_id", workflow)
        self.assertIn("github.event.comment.created_at", workflow)
        self.assertIn('if [ -n "$COMMENT_EVENT_TIME" ]; then', workflow)
        # End must include possible post-comment Actions runs, never future timestamps.
        self.assertIn('datetime.datetime.now(datetime.timezone.utc)', workflow)
        self.assertNotIn('WINDOW_END="$COMMENT_EVENT_TIME"', workflow)
        self.assertIn('datetime.timedelta(minutes=10)', workflow)

    def test_naive_time_and_bad_window_block(self):
        with self.assertRaises(ValueError):
            parse_time("2026-11-23T13:24:00")
        with self.assertRaises(ValueError):
            discover("owner/repo", "token", 7092354527, END, START, lambda *a: None)


if __name__ == "__main__":
    unittest.main()
