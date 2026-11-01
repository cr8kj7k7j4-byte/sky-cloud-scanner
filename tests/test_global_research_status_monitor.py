import unittest
from research.global_research_status_monitor import changed, status


class TestGlobalResearchStatus(unittest.TestCase):
    def setUp(self):
        self.issue = {"number": 190, "state": "open", "updated_at": "2026-11-01T00:00:00Z",
                      "body": "research hold", "comments": 0, "html_url": "https://github.com/x/y/issues/190"}

    def test_initial_and_unchanged(self):
        current = status(self.issue)
        self.assertTrue(changed(current, {}))
        self.assertFalse(changed(current, current.copy()))

    def test_change_detected(self):
        old = status(self.issue)
        self.issue["body"] = "new evidence"
        self.assertTrue(changed(status(self.issue), old))

    def test_wrong_issue_rejected(self):
        self.issue["number"] = 191
        with self.assertRaises(ValueError): status(self.issue)

    def test_missing_timestamp_rejected(self):
        self.issue["updated_at"] = None
        with self.assertRaises(ValueError): status(self.issue)


if __name__ == "__main__":
    unittest.main()
