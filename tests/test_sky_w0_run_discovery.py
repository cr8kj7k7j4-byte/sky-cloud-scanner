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
                return {"workflow_runs": [RUN]}
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
            return {"workflow_runs": [{**RUN, "event": "workflow_dispatch"}]}
        result = discover("owner/repo", "token", 7092354527, START, END, getter)
        self.assertEqual(result["status"], "HOLD_NO_MATCHING_RUN")

    def test_incomplete_pages_fail_closed(self):
        def getter(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            return {"workflow_runs": [{**RUN, "event": "workflow_dispatch"}] * 100}
        result = discover("owner/repo", "token", 7092354527, START, END, getter, max_pages=2)
        self.assertEqual(result["status"], "HOLD_LISTING_INCOMPLETE")

    def test_invalid_run_sha_and_incomplete_artifact_list_block(self):
        def getter(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            if endpoint.startswith("/actions/runs?"):
                return {"workflow_runs": [RUN]}
            return {"artifacts": [], "total_count": 2}
        with self.assertRaises(ValueError):
            discover("owner/repo", "token", 7092354527, START, END, getter)
        def getter2(repo, token, endpoint):
            if endpoint.startswith("/issues/comments/"):
                return COMMENT
            return {"workflow_runs": [{**RUN, "head_sha": None}]}
        with self.assertRaises(ValueError):
            discover("owner/repo", "token", 7092354527, START, END, getter2)

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
