import io
import json
import unittest
from research.intraday_scan_failure_alert import send_failure


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class TestIntradayFailureAlert(unittest.TestCase):
    def test_success_and_message(self):
        def fake(req, timeout):
            body = json.loads(req.data)
            self.assertEqual(body["chat_id"], "123")
            self.assertIn("未完成", body["text"])
            self.assertIn("https://github.com/x/y/actions/runs/1", body["text"])
            self.assertEqual(timeout, 20)
            return Response(b'{"ok": true}')
        send_failure("secret", "123", "https://github.com/x/y/actions/runs/1", fake)

    def test_missing_config_fails_closed(self):
        with self.assertRaises(ValueError):
            send_failure("", "123", "url")

    def test_rejection_is_failure(self):
        with self.assertRaises(RuntimeError):
            send_failure("secret", "123", "url", lambda *a, **k: Response(b'{"ok": false}'))


if __name__ == "__main__":
    unittest.main()
