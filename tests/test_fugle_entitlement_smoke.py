import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "research" / "data_sources" / "fugle_entitlement_smoke.py"
SPEC = importlib.util.spec_from_file_location("fugle_entitlement_smoke", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return b'{"symbol":"2330"}'


class SmokeTests(unittest.TestCase):
    @patch.object(mod, "urlopen", return_value=Response())
    def test_safe_success(self, open_mock):
        result = mod.probe("listed_ticker", "/intraday/ticker/2330", "secret-token")
        self.assertTrue(result["verified"])
        self.assertNotIn("secret-token", json.dumps(result))
        self.assertEqual(result["response_kind"], "dict")

    @patch.object(mod, "urlopen")
    def test_http_failure_masks_body(self, open_mock):
        open_mock.side_effect = HTTPError("https://api.fugle.tw/marketdata/v1.0/stock/x", 403, "forbidden", {}, None)
        result = mod.probe("listed_ticker", "/intraday/ticker/2330", "secret-token")
        self.assertFalse(result["verified"])
        self.assertEqual(result["http_status"], 403)
        self.assertNotIn("secret-token", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
