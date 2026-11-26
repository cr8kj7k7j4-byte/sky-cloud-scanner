"""W0 #363 swing off-hours fail-closed routing contract (offline only)."""
import unittest
from datetime import datetime, timedelta, timezone

from src.sky_swing_session_policy import swing_session_policy
from src.sky_command_router import route_command

TPE = timezone(timedelta(hours=8))


class SwingSessionPolicyTests(unittest.TestCase):
    def at(self, hour, minute=0):
        return datetime(2026, 11, 27, hour, minute, tzinfo=TPE)

    def test_premarket_does_not_launch_live_scan_or_authorize_entry(self):
        report = swing_session_policy(self.at(4, 46), trading_day_verified=True)
        self.assertEqual(report["session_mode"], "PREMARKET_RESEARCH")
        self.assertFalse(report["allow_live_scan"])
        self.assertTrue(report["allow_historical_readback"])
        self.assertFalse(report["historical_artifact_verified"])
        self.assertFalse(report["new_entry_authorized"])

    def test_live_window_requires_verified_calendar_and_still_denies_entry(self):
        report = swing_session_policy(self.at(9, 15), trading_day_verified=True)
        self.assertTrue(report["allow_live_scan"])
        self.assertFalse(report["new_entry_authorized"])
        self.assertEqual(report["exact_v1_rule_status"], "BLOCKED_EXACT_RULE_SPEC")

    def test_unverified_calendar_denies_live(self):
        report = swing_session_policy(self.at(9, 15))
        self.assertFalse(report["allow_live_scan"])

    def test_nontrading_session_is_historical_only(self):
        report = swing_session_policy(self.at(10), trading_day_verified=False)
        self.assertEqual(report["session_mode"], "NON_TRADING_DAY_RESEARCH")
        self.assertFalse(report["allow_live_scan"])

    def test_latest_session_label_does_not_validate_artifact(self):
        report = swing_session_policy(self.at(18), trading_day_verified=True,
                                      latest_complete_session_date="2026-11-26")
        self.assertFalse(report["historical_artifact_verified"])
        self.assertEqual(report["status"], "HOLD_EVIDENCE")

    def test_swing_quick_scan_retains_existing_scanner_without_dispatch(self):
        route = route_command("Sky 波段快掃")
        self.assertEqual(route.data_mode, "SESSION_ADAPTIVE_SWING_RESEARCH")
        self.assertIn("src.swing_live_scanner --mode swing", route.execution_target)
        self.assertIn("sky_swing_session_policy", route.execution_target)
        self.assertIn("No dispatch", route.notes)


if __name__ == "__main__":
    unittest.main()
