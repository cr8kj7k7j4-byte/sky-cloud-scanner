"""No-paid regression: historical and provider probes cannot bypass opted-in atomic gate."""
import os
import unittest
from datetime import date
from unittest.mock import Mock, patch


class DirectFugleAtomicGateTests(unittest.TestCase):
    def test_pit_history_duplicate_never_calls_http(self):
        from research.download_pit_universe_intraday import _request_chunk
        mock_http = Mock()
        with patch("research.download_pit_universe_intraday.guard_fugle_request",
                   side_effect=RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")) as gate:
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_PAID"):
                _request_chunk("2330", date(2026, 11, 2), date(2026, 11, 3),
                               request_get=mock_http)
        mock_http.assert_not_called()
        self.assertEqual(gate.call_count, 1)

    def test_stage2_duplicate_never_calls_http(self):
        from src.sky_fugle_stage2_probe import run
        mock_http = Mock()
        with patch.dict(os.environ, {"FUGLE_API_KEY": "TEST_ONLY"}):
            with patch("src.sky_fugle_stage2_probe.guard_fugle_request",
                       side_effect=RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")):
                with self.assertRaisesRegex(RuntimeError, "DUPLICATE_PAID"):
                    run(request=mock_http, sleeper=lambda _: None)
        mock_http.assert_not_called()

    def test_market_quality_official_non_fugle_request_unchanged(self):
        from research.fugle_market_quality_audit import request
        fake = Mock()
        fake.read.return_value = b"official"
        fake.headers.get_content_charset.return_value = "utf-8"
        opened = Mock()
        opened.__enter__ = Mock(return_value=fake)
        opened.__exit__ = Mock(return_value=None)
        with patch("research.fugle_market_quality_audit.guard_fugle_request") as gate:
            with patch("research.fugle_market_quality_audit.urllib.request.urlopen",
                       return_value=opened):
                data, charset = request("https://isin.twse.com.tw/isin/e_C_public.jsp?strMode=2")
        self.assertEqual(data, b"official")
        gate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
