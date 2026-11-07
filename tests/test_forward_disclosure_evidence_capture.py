import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from research.forward_disclosure_evidence_capture import run, SOURCES


class TestForwardEvidence(unittest.TestCase):
    def test_four_sources_and_no_pit_promotion(self):
        def mock(label, url, directory):
            directory.mkdir(parents=True, exist_ok=True)
            payload = ('[{"source":"%s"}]' % label).encode()
            (directory / (label + ".raw.json")).write_bytes(payload)
            return {"fetch_status":"CAPTURED", "sha256":hashlib.sha256(payload).hexdigest(),
                    "row_count":1,"observed_at_utc":"2026-11-08T01:00:00+00:00",
                    "qualified_issuer_published_at":False}
        with tempfile.TemporaryDirectory() as temp:
            output=run(Path(temp), fetcher=mock)
            self.assertEqual(len(output["source_results"]),len(SOURCES))
            self.assertEqual(output["historical_pit_event_count"],0)
            self.assertFalse(output["production_signal"])
            self.assertFalse(output["historical_issuer_publication_timestamp_qualified"])
            self.assertEqual(output["long_term_storage"],"NOT_VERIFIED")
            self.assertTrue((Path(temp)/"manifest.json").exists())

    def test_one_failure_blocks_complete(self):
        def mock(label, url, directory):
            return {"fetch_status":"ERROR"} if label=="tpex_revenue_latest" else {"fetch_status":"CAPTURED"}
        with tempfile.TemporaryDirectory() as temp:
            out=run(Path(temp),fetcher=mock)
            self.assertEqual(out["status"],"INCOMPLETE_DATA")
            self.assertFalse(out["production_signal"])

    def test_source_urls_are_official(self):
        self.assertEqual(len(SOURCES),4)
        self.assertTrue(all(v.startswith("https://") for v in SOURCES.values()))


if __name__=="__main__":
    unittest.main()
