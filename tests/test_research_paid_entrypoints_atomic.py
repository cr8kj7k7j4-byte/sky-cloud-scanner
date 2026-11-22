"""#363: zero-provider-call research paid entrypoint safety tests."""
import os
import unittest
from unittest.mock import Mock, patch

from research import download_intraday as intraday
from research import probe_fugle_pit_intraday_coverage as pit
from research import download_taiex_benchmark as taiex


def response(status, data=None):
    r = Mock()
    r.status_code = status
    r.json.return_value = {"data": data or []}
    return r


class PaidLegacyGuardContract(unittest.TestCase):
    def test_intraday_without_guard_blocks_before_get(self):
        with patch.dict(os.environ, {"FUGLE_API_KEY": "offline"}, clear=True), \
             patch.object(intraday.requests, "get") as get, \
             patch.object(intraday, "guard_fugle_request") as guard:
            with self.assertRaisesRegex(RuntimeError, "HISTORICAL_PAID_GUARD_REQUIRED"):
                intraday.get_hist("2330", "2026-11-16", "2026-11-20")
            get.assert_not_called()
            guard.assert_not_called()

    def test_intraday_429_never_retries(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1", "FUGLE_API_KEY": "offline"}), \
             patch.object(intraday, "guard_fugle_request") as guard, \
             patch.object(intraday.requests, "get", return_value=response(429)) as get:
            with self.assertRaisesRegex(RuntimeError, "FUGLE_RATE_LIMITED_NO_RETRY"):
                intraday.get_hist("2330", "2026-11-16", "2026-11-20")
            get.assert_called_once()
            guard.assert_called_once()

    def test_intraday_duplicate_claim_blocks_http(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1", "FUGLE_API_KEY": "offline"}), \
             patch.object(intraday, "guard_fugle_request", side_effect=RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")), \
             patch.object(intraday.requests, "get") as get:
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED"):
                intraday.get_hist("2330", "2026-11-16", "2026-11-20")
            get.assert_not_called()

    def test_pit_requires_enforcement(self):
        with patch.dict(os.environ, {"FUGLE_API_KEY": "offline"}, clear=True), \
             patch.object(pit.requests, "get") as get:
            with self.assertRaisesRegex(RuntimeError, "HISTORICAL_PAID_GUARD_REQUIRED"):
                pit.request_one("2330", "2026-11-16", "2026-11-20")
            get.assert_not_called()

    def test_pit_429_is_terminal(self):
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1", "FUGLE_API_KEY": "offline"}), \
             patch.object(pit, "guard_fugle_request") as guard, \
             patch.object(pit.requests, "get", return_value=response(429)) as get:
            result = pit.request_one("2330", "2026-11-16", "2026-11-20")
            self.assertEqual(result["status"], "RATE_LIMIT_429_EXHAUSTED")
            self.assertEqual(result["attempts"], 1)
            get.assert_called_once()
            guard.assert_called_once()

    def test_taiex_requires_enforcement(self):
        get = Mock()
        with patch.dict(os.environ, {"FUGLE_API_KEY": "offline"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "HISTORICAL_PAID_GUARD_REQUIRED"):
                taiex.download_taiex("2026-11-16", "2026-11-20", request_get=get)
            get.assert_not_called()

    def test_taiex_valid_claim_allows_once(self):
        get = Mock(return_value=response(200, [{"date": "2026-11-16T09:00:00+08:00"}]))
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1", "FUGLE_API_KEY": "offline"}), \
             patch.object(taiex, "guard_fugle_request") as guard:
            data = taiex.download_taiex("2026-11-16", "2026-11-20",
                                        request_get=get, sleep_fn=lambda _: None)
            self.assertEqual(len(data), 1)
            get.assert_called_once()
            guard.assert_called_once()

    def test_taiex_duplicate_claim_blocks_http(self):
        get = Mock()
        with patch.dict(os.environ, {"SKY_PAID_ATOMIC_ENFORCE": "1", "FUGLE_API_KEY": "offline"}), \
             patch.object(taiex, "guard_fugle_request", side_effect=RuntimeError("DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED")):
            with self.assertRaisesRegex(RuntimeError, "DUPLICATE_PAID_FUGLE_ENDPOINT_BLOCKED"):
                taiex.download_taiex("2026-11-16", "2026-11-20", request_get=get)
            get.assert_not_called()
