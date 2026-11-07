import unittest
from research.disclosure_source_discovery import analyze_html

class SourceDiscoveryTests(unittest.TestCase):
    def test_heading_without_issuer_rows_is_not_qualified(self):
        x=analyze_html("<html><h3>財務報告書</h3><div>公告日期時間</div></html>")
        self.assertTrue(x["has_announcement_datetime_heading"])
        self.assertEqual(x["candidate_datetime_strings_in_rendered_html"],0)
        self.assertFalse(x["source_timestamps_qualified"])

    def test_apparent_time_is_not_proof_of_filing(self):
        x=analyze_html("<div>公告日期時間</div><p>115/08/07 09:09</p>")
        self.assertEqual(x["candidate_datetime_strings_in_rendered_html"],1)
        self.assertFalse(x["source_timestamps_qualified"])
        self.assertFalse(x["historical_issuer_filing_coverage_certified"])

    def test_js_only_still_no_history_proof(self):
        x=analyze_html('<script src="/static/info.js"></script><table><th>公告日期時間</th></table>')
        self.assertEqual(x["script_asset_count"],1)
        self.assertFalse(x["historical_issuer_filing_coverage_certified"])

if __name__=="__main__":
    unittest.main()
