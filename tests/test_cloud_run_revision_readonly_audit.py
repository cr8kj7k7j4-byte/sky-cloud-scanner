import unittest
from scripts.cloud_run_revision_readonly_audit import extract

def sample():
    return {
        "metadata": {"name":"tw-ai-mobile"},
        "status": {"latestReadyRevisionName":"tw-ai-mobile-001",
                   "traffic":[{"revisionName":"tw-ai-mobile-001","percent":100}],
                   "conditions":[{"type":"Ready","status":"True"}]},
        "spec":{"template":{"spec":{"containers":[{"image":"example.invalid/image:v1"}]}}}
    }

class ReadOnlyCloudRunAuditTests(unittest.TestCase):
    def test_extract_does_not_claim_http_or_deployment(self):
        x=extract(sample(),{"status":{"imageDigest":"example.invalid/image@sha256:abc"}})
        self.assertEqual(x["ready_revision"],"tw-ai-mobile-001")
        self.assertEqual(x["traffic"][0]["percent"],100)
        self.assertFalse(x["http_health_verified"])
        self.assertFalse(x["trade_authorized"])
        self.assertTrue(x["deployed_commit"].startswith("UNVERIFIED"))

    def test_missing_revision_rejected(self):
        body=sample()
        body["status"].pop("latestReadyRevisionName")
        with self.assertRaises(ValueError):
            extract(body)

    def test_traffic_incomplete_rejected(self):
        body=sample()
        body["status"]["traffic"][0]["percent"]=80
        with self.assertRaises(ValueError):
            extract(body)

    def test_invalid_traffic_rejected(self):
        body=sample()
        body["status"]["traffic"][0]["percent"]=-1
        with self.assertRaises(ValueError):
            extract(body)

if __name__=="__main__":
    unittest.main()
