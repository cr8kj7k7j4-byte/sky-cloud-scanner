"""Offline mocked end-to-end checks; never needs a real API key or network."""
import datetime as dt
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from research import fugle_market_quality_audit as audit


def fixture(now, broken_market=None):
    codes=[str(1100+i) for i in range(105)]
    html="<table>"+''.join(
        f"<tr><td>{code}　Sample</td><td>TW0000000000</td><td>2026/01/01</td><td>LISTED</td><td>Industry</td><td>ESVUFR</td></tr>"
        for code in codes
    )+"</table>"
    def fake_request(url,key=None):
        if "isin.twse.com.tw" in url:
            if broken_market and url.endswith("strMode=4"):
                return b"<html>invalid universe</html>","utf-8"
            return html.encode(),"utf-8"
        market="TSE" if "/TSE?" in url else "OTC"
        payload={
            "date":now.date().isoformat(), "time":now.strftime("%H%M%S"),"market":market,
            "data":[{"type":"EQUITY","symbol":code,"closePrice":30.0,
                     "tradeVolume":1000,"lastUpdated":int(now.timestamp()*1000000)}
                    for code in codes]
        }
        return json.dumps(payload).encode(),"utf-8"
    return fake_request


class FullMarketQualityIntegrationTests(unittest.TestCase):
    def execute(self,failed=False):
        now=dt.datetime.now(audit.TZ)
        with tempfile.TemporaryDirectory() as directory:
            previous=os.getcwd()
            try:
                os.chdir(directory)
                with patch.dict(os.environ,{"FUGLE_API_KEY":"test-only-placeholder"}),patch.object(audit,"request",side_effect=fixture(now,failed)):
                    if failed:
                        with self.assertRaises(SystemExit) as error:
                            audit.run()
                        self.assertEqual(error.exception.code,1)
                    else:
                        audit.run()
                with open("fugle_market_quality_audit.json",encoding="utf-8") as fh:
                    return json.load(fh)
            finally:
                os.chdir(previous)

    def test_complete_mocked_market_pass(self):
        evidence=self.execute()
        self.assertEqual(evidence["coverage_status"],"PASS")
        for market in ("TSE","OTC"):
            self.assertEqual(evidence["markets"][market]["official_count"],105)
            self.assertEqual(evidence["markets"][market]["snapshot_count"],105)
            self.assertEqual(evidence["markets"][market]["coverage_ratio"],1.0)
        self.assertIn(evidence["status"],("PASS_LIVE","COVERAGE_PASS_LIVE_PENDING"))

    def test_unverifiable_official_universe_fails_closed(self):
        evidence=self.execute(failed=True)
        self.assertEqual(evidence["status"],"INSUFFICIENT_DATA_OR_REVIEW")
        self.assertEqual(evidence["markets"]["OTC"]["status"],"INSUFFICIENT_DATA")
        self.assertTrue(evidence["markets"]["OTC"]["issues"])


if __name__=="__main__":
    unittest.main()
