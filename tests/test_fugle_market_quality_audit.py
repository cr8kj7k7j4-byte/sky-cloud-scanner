"""Offline contract tests for read-only paid market quality audit."""
import unittest
from research.fugle_market_quality_audit import official_codes, Rows

class MarketQualityAuditTests(unittest.TestCase):
    def test_official_common_equity_filter(self):
        rows = ["<tr><td>Security</td><td>CFICode</td></tr>"]
        rows += [f"<tr><td>{1000+i}　Company {i}</td><td>TW0000000000</td><td>ESVUFR</td></tr>" for i in range(101)]
        rows += ["<tr><td>700019　Warrant</td><td>RWSCCA</td></tr>"]
        rows += ["<tr><td>0050　ETF</td><td>CEOGEU</td></tr>"]
        result=official_codes(("<table>"+"".join(rows)+"</table>").encode("utf-8"),"utf-8")
        self.assertEqual(len(result),101)
        self.assertNotIn("0050",result)
        self.assertNotIn("700019",result)

    def test_malformed_universe_fails_closed(self):
        with self.assertRaises(ValueError):
            official_codes(b"<html><table><tr><td>1101 TCC</td><td>ESVUFR</td></tr></table></html>","utf-8")

    def test_html_parser_does_not_merge_cells(self):
        p=Rows()
        p.feed("<table><tr><td>1101 TCC</td><td>ESVUFR</td></tr></table>")
        self.assertEqual(p.rows,[["1101 TCC","ESVUFR"]])

if __name__=="__main__":
    unittest.main()
