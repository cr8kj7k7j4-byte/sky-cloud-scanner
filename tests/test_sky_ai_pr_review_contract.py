import contextlib
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sky_ai_pr_review", ROOT / "scripts" / "sky_ai_pr_review.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
SHA = "a" * 40
REPO = "cr8kj7k7j4-byte/sky-cloud-scanner"


class AIReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.oldcwd = pathlib.Path.cwd()
        os.chdir(self.temp.name)
        event = {"workflow_run": {
            "id": 17, "event": "pull_request", "conclusion": "success",
            "name": "Sky Single Owner Security Evidence",
            "head_sha": SHA, "head_repository": {"full_name": REPO},
        }}
        pathlib.Path("event.json").write_text(json.dumps(event))
        self.env = mock.patch.dict(os.environ, {
            "GITHUB_REPOSITORY": REPO, "GITHUB_EVENT_PATH": str(pathlib.Path("event.json").resolve()),
            "GITHUB_RUN_ID": "18", "GH_READ_TOKEN": "fake-read-only",
            "OPENAI_API_KEY": ""
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        os.chdir(self.oldcwd)
        self.temp.cleanup()

    def report(self):
        return json.loads(pathlib.Path(module.OUT).read_text())

    def test_no_secret_fails_closed_without_external_inference(self):
        pr = {"number": 523, "head": {"sha": SHA, "repo": {"full_name": REPO}},
              "base": {"repo": {"full_name": REPO}}}
        file = {"filename": "src/safe.py", "patch": "@@ -1 +1 @@\n+print('safe')"}
        with mock.patch.object(module, "fetch", side_effect=[[pr], [file]]):
            self.assertEqual(module.main(), 1)
        self.assertEqual(self.report()["reason"], "OPENAI_API_KEY_NOT_CONFIGURED")
        self.assertEqual(self.report()["ai_status"], "HOLD")

    def test_changed_sha_fails_closed(self):
        with mock.patch.object(module, "fetch", return_value=[]):
            self.assertEqual(module.main(), 1)
        self.assertEqual(self.report()["reason"], "LATEST_SHA_PR_NOT_UNIQUE")

    def test_detected_secret_never_sent_to_model(self):
        pr = {"number": 523, "head": {"sha": SHA, "repo": {"full_name": REPO}},
              "base": {"repo": {"full_name": REPO}}}
        file = {"filename": "src/secrets.py",
                "patch": "+token = 'sk-" + "x" * 40 + "'"}
        with mock.patch.object(module, "fetch", side_effect=[[pr], [file]]):
            self.assertEqual(module.main(), 1)
        self.assertEqual(self.report()["reason"], "POSSIBLE_SECRET_IN_DIFF_NO_EXTERNAL_TRANSFER")

    def test_non_pr_event_fails_closed(self):
        data = json.loads(pathlib.Path("event.json").read_text())
        data["workflow_run"]["event"] = "workflow_dispatch"
        pathlib.Path("event.json").write_text(json.dumps(data))
        with mock.patch.object(module, "fetch") as call:
            self.assertEqual(module.main(), 1)
            call.assert_not_called()
        self.assertEqual(self.report()["reason"], "SOURCE_EVENT_NOT_SUCCESSFUL_PR")


if __name__ == "__main__":
    unittest.main()
