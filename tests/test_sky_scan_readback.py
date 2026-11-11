import unittest
from datetime import datetime, timedelta, timezone
from src.sky_scan_readback import COMMANDS, canonical_command, validate_scan_readback

NOW = datetime(2026, 11, 11, 1, 10, tzinfo=timezone.utc)
RUN_ID = "123456"
REQUEST_ID = "readback-20261111-001"

def good():
    return {
        "schema": "SKY_CHAT_SCAN_STATUS_V1",
        "scan_id": RUN_ID,
        "request_id": REQUEST_ID,
        "run_url": "https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/" + RUN_ID,
        "completed_at_utc": (NOW - timedelta(seconds=40)).isoformat(),
        "status": "REPORT_READY_RESEARCH_ONLY",
        "data_timestamp": (NOW - timedelta(minutes=2)).isoformat(),
        "source": "FUGLE_PAID_SNAPSHOT",
        "row_count": 1986, "universe_count": 1986,
        "observed_price_count": 1957, "stage2_verified_executed_count": 12,
        "production_eligible": False, "automatic_order": False,
    }

def check(x):
    return validate_scan_readback(x, expected_run_id=RUN_ID,
                                  expected_request_id=REQUEST_ID, now=NOW)

class ReadbackContracts(unittest.TestCase):
    def test_all_five_commands_use_one_route(self):
        self.assertEqual(len(COMMANDS), 5)
        for command in COMMANDS:
            self.assertEqual(canonical_command(command), "Sky 快掃")

    def test_unknown_command_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED"):
            canonical_command("Sky 下單")

    def test_fresh_snapshot_is_not_trade_certification(self):
        x = check(good())
        self.assertFalse(x["snapshot_is_executed_trade_time"])
        self.assertFalse(x["production_eligible"])
        self.assertEqual(x["trade_action"], "禁止交易")

    def test_old_receipt_is_rejected(self):
        x = good()
        x["completed_at_utc"] = (NOW - timedelta(minutes=30)).isoformat()
        with self.assertRaisesRegex(ValueError, "STALE_RECEIPT"):
            check(x)

    def test_old_snapshot_capture_is_never_trade_verified(self):
        x = good()
        x["data_timestamp"] = (NOW - timedelta(days=1)).isoformat()
        self.assertFalse(check(x)["snapshot_is_executed_trade_time"])

    def test_fail_closed_for_wrong_provenance(self):
        for key, value in (("scan_id", "older"), ("request_id", "other"),
                           ("run_url", "https://example.com/123456"),
                           ("source", "TWSE_MIS"),
                           ("production_eligible", True),
                           ("automatic_order", True),
                           ("row_count", 2), ("observed_price_count", 9999),
                           ("status", "DATA_BLOCKED_SOURCE_FAILURE")):
            with self.subTest(key=key):
                x = good()
                x[key] = value
                with self.assertRaises(ValueError):
                    check(x)

    def test_invalid_timestamps_are_rejected(self):
        for key in ("completed_at_utc", "data_timestamp"):
            for val in (None, "bad", "2026-11-11T09:10:00"):
                with self.subTest(key=key, val=val):
                    x = good()
                    x[key] = val
                    with self.assertRaises(ValueError):
                        check(x)

    def test_future_receipt_rejected(self):
        x = good()
        x["completed_at_utc"] = (NOW + timedelta(minutes=10)).isoformat()
        with self.assertRaisesRegex(ValueError, "RECEIPT_FROM_FUTURE"):
            check(x)

if __name__ == "__main__":
    unittest.main()
