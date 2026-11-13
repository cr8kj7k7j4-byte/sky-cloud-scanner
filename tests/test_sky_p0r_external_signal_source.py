"""GitHub artifact provenance tests: fixtures are NEVER live trade evidence."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from research.sky_p0r_external_signal_source import _receipt_from_github


RUN="12345"
SHA="a"*40
ARTIFACT_ID="67890"
RECEIPT={
    "schema":"SKY_PRECOMMITTED_PAPER_SIGNAL_V1",
    "signal_run_id":RUN,
    "signal_sha":SHA,
    "signal_artifact_id":ARTIFACT_ID,
    "signal_scan_id":"independent-scan",
    "published_at":"2026-11-11T09:05:00+08:00",
    "production_eligible":False,
    "automatic_order":False,
    "signal":{"signal_id":"synthetic-fixture-only",
              "signal_time":"2026-11-11T09:05:00+08:00",
              "market_scan_id":"independent-scan","symbol":"2409"},
}
META={
    "id":12345,"status":"completed","conclusion":"success",
    "head_sha":SHA,"workflow_id":77,"repository":{"full_name":"owner/repo"}
}
LISTING={"artifacts":[{
    "id":67890,"name":"sky-precommitted-paper-signal-12345",
    "expired":False,"created_at":"2026-11-11T09:06:00+08:00",
    "workflow_run":{"id":12345}
}]}


def fake_download(directory):
    (directory/"precommitted_signal.json").write_text(
        json.dumps(RECEIPT), encoding="utf-8")


class ExternalSignalVerificationTests(unittest.TestCase):
    def setUp(self):
        self._approved_workflow = patch.dict(
            "os.environ", {"SKY_P0R_APPROVED_SIGNAL_WORKFLOW_ID": "77"})
        self._approved_workflow.start()
        self.addCleanup(self._approved_workflow.stop)

    def test_unapproved_or_unconfigured_workflow_never_issues_signal_receipt(self):
        def fetch(endpoint):
            return META if endpoint.endswith("/runs/12345") else LISTING
        with patch.dict("os.environ",
                        {"SKY_P0R_APPROVED_SIGNAL_WORKFLOW_ID": ""}):
            with self.assertRaisesRegex(
                    ValueError, "SIGNAL_WORKFLOW_NOT_GOVERNANCE_APPROVED"):
                _receipt_from_github(
                    "owner/repo", RUN, fetch=fetch, downloader=fake_download)
        def different_workflow(endpoint):
            if endpoint.endswith("/runs/12345"):
                return {**META, "workflow_id": 78}
            return LISTING
        with self.assertRaisesRegex(
                ValueError, "SIGNAL_WORKFLOW_NOT_GOVERNANCE_APPROVED"):
            _receipt_from_github(
                "owner/repo", RUN, fetch=different_workflow,
                downloader=fake_download)
    def test_server_upload_time_not_claimed_signal_time_controls(self):
        def fetch(endpoint):
            return META if endpoint.endswith("/runs/12345") else LISTING
        receipt,proof=_receipt_from_github(
            "owner/repo",RUN,fetch=fetch,downloader=fake_download)
        self.assertEqual(receipt["published_at"],"2026-11-11T01:06:00+00:00")
        self.assertTrue(proof["github_metadata_verified"])
        self.assertEqual(proof["signal_sha"],SHA)
        self.assertEqual(proof["signal_artifact_id"],ARTIFACT_ID)

    def test_github_assigned_artifact_id_is_bound_after_upload(self):
        # A signal producer cannot know GitHub's Artifact ID before upload.
        def downloader(folder):
            receipt = {k: v for k, v in RECEIPT.items()
                       if k != "signal_artifact_id"}
            (folder / "precommitted_signal.json").write_text(
                json.dumps(receipt), encoding="utf-8")
        def fetch(endpoint):
            return META if endpoint.endswith("/runs/12345") else LISTING
        receipt, proof = _receipt_from_github(
            "owner/repo", RUN, fetch=fetch, downloader=downloader)
        self.assertEqual(receipt["signal_artifact_id"], ARTIFACT_ID)
        self.assertEqual(proof["signal_artifact_id"], ARTIFACT_ID)
        self.assertTrue(proof["github_metadata_verified"])

    def test_non_success_run_rejected(self):
        def fetch(endpoint):
            return {**META,"conclusion":"failure"} if endpoint.endswith("/runs/12345") else LISTING
        with self.assertRaisesRegex(ValueError,"UNTRUSTED_SIGNAL_WORKFLOW_RUN"):
            _receipt_from_github("owner/repo",RUN,fetch=fetch,downloader=fake_download)

    def test_missing_or_other_artifact_rejected(self):
        def fetch(endpoint):
            return META if endpoint.endswith("/runs/12345") else {"artifacts":[]}
        with self.assertRaisesRegex(ValueError,"PRECOMMITTED_SIGNAL_ARTIFACT_NOT_FOUND"):
            _receipt_from_github("owner/repo",RUN,fetch=fetch,downloader=fake_download)

    def test_mismatched_artifact_id_rejected(self):
        def downloader(folder):
            receipt={**RECEIPT,"signal_artifact_id":"wrong"}
            (folder/"precommitted_signal.json").write_text(
                json.dumps(receipt),encoding="utf-8")
        def fetch(endpoint):
            return META if endpoint.endswith("/runs/12345") else LISTING
        with self.assertRaisesRegex(ValueError,"SIGNAL_RECEIPT_GITHUB_METADATA_MISMATCH"):
            _receipt_from_github("owner/repo",RUN,fetch=fetch,downloader=downloader)


    def test_failed_external_readback_writes_fail_closed_status(self):
        from research.sky_p0r_external_signal_source import main
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            from os import chdir, getcwd
            original = getcwd()
            try:
                chdir(tmp)
                folder = Path("output/sky_p0r_paper_ledger_readback")
                folder.mkdir(parents=True)
                (folder / "verified_512_completed_bars.json").write_text(
                    json.dumps({"source_run_id": "upstream-run"}), encoding="utf-8")
                with patch.dict("os.environ", {
                    "SKY_P0R_SIGNAL_RUN_ID": "12345",
                    "GITHUB_REPOSITORY": "owner/repo",
                }), patch(
                    "research.sky_p0r_external_signal_source._receipt_from_github",
                    side_effect=ValueError("UNTRUSTED_SIGNAL_WORKFLOW_RUN"),
                ):
                    self.assertEqual(main(), 0)
                status = json.loads(
                    (folder / "external_signal_source_status.json").read_text(
                        encoding="utf-8"))
                self.assertEqual(status["verdict"], "INSUFFICIENT_DATA")
                self.assertEqual(
                    status["reason"], "EXTERNAL_SIGNAL_READBACK_OR_PROVENANCE_FAILED")
                self.assertEqual(status["paper_fill_count"], 0)
                self.assertFalse(status["reconciled"])
                self.assertFalse(status["production_eligible"])
                self.assertFalse(status["automatic_order"])
                self.assertEqual(status["error_type"], "ValueError")
            finally:
                chdir(original)



if __name__=="__main__":
    unittest.main()
