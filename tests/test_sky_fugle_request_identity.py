import unittest
from research.sky_fugle_request_identity import canonical_fugle_request as key


class CanonicalFugleRequestTests(unittest.TestCase):
    def test_same_endpoint_from_different_workflows_is_identical(self):
        one = key("GET", "https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/2330")
        two = key("get", "/intraday/quote/2330")
        self.assertEqual(one, two)
        self.assertTrue(one.startswith("sky:fugle:endpoint:v1:"))

    def test_equivalent_parameter_order(self):
        one = key("GET", "/historical/candles/2330?to=2026-11-10&from=2026-11-01&timeframe=5")
        two = key("GET", "/historical/candles/2330?timeframe=5&from=2026-11-01&to=2026-11-10")
        self.assertEqual(one, two)

    def test_distinct_stock_timeframe_and_interval_are_distinct(self):
        base = key("GET", "/historical/candles/2330?from=2026-11-01&to=2026-11-10&timeframe=5")
        for url in (
            "/historical/candles/2317?from=2026-11-01&to=2026-11-10&timeframe=5",
            "/historical/candles/2330?from=2026-11-01&to=2026-11-10&timeframe=1",
            "/historical/candles/2330?from=2026-11-01&to=2026-11-09&timeframe=5",
        ):
            with self.subTest(url=url):
                self.assertNotEqual(base, key("GET", url))

    def test_tse_otc_snapshot_scope_differs(self):
        self.assertNotEqual(key("GET", "/snapshot/quotes/TSE?type=COMMONSTOCK"),
                            key("GET", "/snapshot/quotes/OTC?type=COMMONSTOCK"))

    def test_unsupported_or_untrusted_fail_closed(self):
        for url in (
            "http://api.fugle.tw/intraday/quote/2330",
            "https://evil.example/intraday/quote/2330",
            "https://api.fugle.tw:8443/intraday/quote/2330",
            "https://api.fugle.tw:bad/intraday/quote/2330",
            "//evil.example/intraday/quote/2330",
            "intraday/quote/2330",
            "/unknown",
            "/intraday/quote/2330?secret=token",
            "/intraday/quote/2330?limit=1&limit=2",
            "/historical/candles/2330?from=2026-11-10&to=2026-11-01",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    key("GET", url)
        with self.assertRaises(ValueError):
            key("POST", "/intraday/quote/2330")


if __name__ == "__main__":
    unittest.main()
