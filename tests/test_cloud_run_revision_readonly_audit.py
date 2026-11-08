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

    def test_traffic_and_tagged_canary_are_both_attested(self):
        service = sample()
        service["status"]["latestReadyRevisionName"] = "tw-ai-mobile-00157-wiw"
        service["status"]["traffic"] = [
            {"revisionName": "tw-ai-mobile-00154-csh", "percent": 100},
            {"revisionName": "tw-ai-mobile-00157-wiw", "percent": 0, "tag": "ledger-canary"},
        ]
        revisions = {
            name: {"metadata": {"name": name}, "spec": {"containers": [{"image": image}]}}
            for name, image in (
                ("tw-ai-mobile-00154-csh", "example.invalid/prod@sha256:old"),
                ("tw-ai-mobile-00157-wiw", "example.invalid/canary@sha256:new"),
            )
        }
        report = extract(service, revisions["tw-ai-mobile-00157-wiw"], revisions)
        self.assertTrue(report["all_revisions_inspected"])
        self.assertEqual(len(report["revision_images"]), 2)
        self.assertEqual(report["revision_images"]["tw-ai-mobile-00154-csh"]["spec_image"],
                         "example.invalid/prod@sha256:old")
        self.assertEqual(report["traffic"][1]["tag"], "ledger-canary")

    def test_incomplete_revision_attestation_fails_closed(self):
        service = sample()
        service["status"]["traffic"] = [
            {"revisionName": "tw-ai-mobile-001", "percent": 100},
            {"revisionName": "tw-ai-mobile-002", "percent": 0, "tag": "ledger-canary"},
        ]
        only_ready = {"tw-ai-mobile-001":
            {"metadata": {"name": "tw-ai-mobile-001"},
             "spec": {"containers": [{"image": "example.invalid/v1"}]}}}
        with self.assertRaisesRegex(ValueError, "revision_set_incomplete"):
            extract(service, only_ready["tw-ai-mobile-001"], only_ready)

    def test_revision_identity_mismatch_fails_closed(self):
        service = sample()
        revision = {"metadata": {"name": "unexpected-revision"},
                    "spec": {"containers": [{"image": "example.invalid/v1"}]}}
        with self.assertRaisesRegex(ValueError, "revision_identity_mismatch"):
            extract(service, revision, {"tw-ai-mobile-001": revision})

    def test_empty_traffic_revision_rejected(self):
        service = sample()
        service["status"]["traffic"][0]["revisionName"] = None
        with self.assertRaisesRegex(ValueError, "invalid_traffic_revision"):
            extract(service)

    def test_latest_revision_without_revision_name_is_supported(self):
        service = sample()
        service["status"]["latestReadyRevisionName"] = "tw-ai-mobile-002"
        service["status"]["traffic"] = [
            {"revisionName": "tw-ai-mobile-001", "percent": 100},
            {"latestRevision": True, "tag": "ledger-canary", "percent": 0},
        ]
        revisions = {
            name: {"metadata": {"name": name},
                   "spec": {"containers": [{"image": "example.invalid/" + name}]}}
            for name in ("tw-ai-mobile-001", "tw-ai-mobile-002")
        }
        data = extract(service, revisions["tw-ai-mobile-002"], revisions)
        self.assertEqual(data["traffic"][1]["revision"], "tw-ai-mobile-002")
        self.assertTrue(data["all_revisions_inspected"])

    def test_runtime_evidence_never_exposes_environment_or_command_secrets(self):
        service = sample()
        revision = {
            "metadata": {
                "name": "tw-ai-mobile-001",
                "labels": {"commit-sha": "abcdef", "gcb-build-id": "build-123"}
            },
            "spec": {
                "serviceAccountName": "private-service-account@internal.invalid",
                "containers": [{
                    "image": "example.invalid/rev@sha256:abcd",
                    "command": ["python", "--password=COMMAND_PRIVATE"],
                    "args": ["--api-key=ARGS_PRIVATE"],
                    "ports": [{"name": "http1", "containerPort": 8080}],
                    "env": [{"name": "MOBILE_PASSWORD", "value": "ENV_PRIVATE"}],
                }]
            },
            "status": {"imageDigest": "example.invalid/rev@sha256:abcd"}
        }
        data = extract(service, revision, {"tw-ai-mobile-001": revision})
        evidence = data["revision_images"]["tw-ai-mobile-001"]["runtime"]
        self.assertTrue(evidence["command_override_present"])
        self.assertTrue(evidence["args_override_present"])
        self.assertEqual(evidence["first_container_ports"][0]["containerPort"], 8080)
        self.assertEqual(evidence["commit_label"], "abcdef")
        self.assertTrue(evidence["revision_service_account_set"])
        import json
        dump = json.dumps(data)
        for secret in ("COMMAND_PRIVATE", "ARGS_PRIVATE", "ENV_PRIVATE",
                       "private-service-account@internal.invalid"):
            self.assertNotIn(secret, dump)

    def test_traffic_latest_flag_without_revision_name_requires_true(self):
        service = sample()
        service["status"]["traffic"] = [{"latestRevision": False, "percent": 100}]
        with self.assertRaisesRegex(ValueError, "invalid_traffic_revision"):
            extract(service)

    def test_wrong_service_name_cannot_be_attested(self):
        service = sample()
        service["metadata"]["name"] = "unexpected-service"
        with self.assertRaisesRegex(ValueError, "service_identity_mismatch"):
            extract(service)

    def test_bool_percent_must_not_count_as_one_percent(self):
        service = sample()
        service["status"]["traffic"] = [
            {"revisionName": "tw-ai-mobile-001", "percent": 99},
            {"revisionName": "tw-ai-mobile-002", "percent": True},
        ]
        with self.assertRaisesRegex(ValueError, "invalid_traffic_percent"):
            extract(service)

    def test_missing_and_invalid_ready_revision_identity_fails_closed(self):
        service = sample()
        service["status"]["latestReadyRevisionName"] = "other-service-001"
        with self.assertRaisesRegex(ValueError, "missing_ready_revision_or_traffic"):
            extract(service)

    def test_empty_traffic_must_not_attest_ready_revision(self):
        service = sample()
        service["status"]["traffic"] = []
        with self.assertRaisesRegex(ValueError, "missing_ready_revision_or_traffic"):
            extract(service)

    def test_immutable_digest_proof_is_separate_from_image_name(self):
        revision = {
            "metadata": {"name": "tw-ai-mobile-001"},
            "spec": {"containers": [{"image": "example.invalid/app:latest"}]},
            "status": {},
        }
        data = extract(sample(), revision, {"tw-ai-mobile-001": revision})
        proof = data["revision_images"]["tw-ai-mobile-001"]
        self.assertTrue(proof["image_evidence_present"])
        self.assertFalse(proof["immutable_digest_present"])

if __name__=="__main__":
    unittest.main()
