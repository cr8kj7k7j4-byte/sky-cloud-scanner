"""W0 #363 swing off-hours fail-closed routing contract (offline only)."""
import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

from src.sky_swing_session_policy import swing_session_policy, read_swing_complete_session_observations
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

    def test_command_is_always_accepted_without_claiming_data_available(self):
        for hour in (4, 9, 12, 14, 23):
            for trading_day in (True, False, None):
                report = swing_session_policy(self.at(hour), trading_day_verified=trading_day)
                self.assertTrue(report["command_accepted"])
                self.assertEqual(report["command_availability"], "ALL_SESSIONS")
                self.assertFalse(report["report_available"])
                self.assertEqual(report["status"], "HOLD_EVIDENCE")
                self.assertFalse(report["new_entry_authorized"])

    def test_offhours_verified_artifact_renders_swing_observation_only(self):
        from tests.test_sky_historical_research_readback import fixture, SHA, DATE
        with tempfile.TemporaryDirectory() as folder:
            fixture(Path(folder))
            result = read_swing_complete_session_observations(
                self.at(18), folder, trading_day_verified=True,
                expected_run_id="123", expected_attempt="2",
                expected_head_sha=SHA, artifact_id=456,
                verified_complete_session_date=DATE,
                calendar_session_certified=True,
            )
            self.assertTrue(result["historical_artifact_verified"])
            self.assertEqual(result["run_id"], "123")
            self.assertFalse(result["strategy_signal_verified"])
            self.assertFalse(result["source_certified"])
            self.assertFalse(result["new_entry_authorized"])
            self.assertEqual(result["trade_action"], "禁止交易")
            self.assertIn("台泥", result["historical_evidence"]["research_markdown"])

    def test_intraday_never_uses_stale_historical_report_as_live_quote(self):
        with self.assertRaisesRegex(ValueError, "LIVE_SESSION_REQUIRES_AUTHORIZED_A1_A2"):
            read_swing_complete_session_observations(
                self.at(11), "/missing", trading_day_verified=True,
                expected_run_id="123", expected_attempt="2",
                expected_head_sha="a" * 40, artifact_id=456,
                verified_complete_session_date="2026-11-26",
                calendar_session_certified=True,
            )

    def test_offhours_unverified_session_and_tampered_artifact_fail_closed(self):
        from tests.test_sky_historical_research_readback import fixture, SHA, DATE
        with tempfile.TemporaryDirectory() as folder:
            source, _, _, _ = fixture(Path(folder))
            opts = dict(trading_day_verified=True,
                        expected_run_id="123", expected_attempt="2",
                        expected_head_sha=SHA, artifact_id=456,
                        verified_complete_session_date=DATE)
            with self.assertRaisesRegex(ValueError, "SWING_OFFICIAL_COMPLETE_SESSION_REQUIRED"):
                read_swing_complete_session_observations(
                    self.at(18), folder, calendar_session_certified=False, **opts)
            source.write_bytes(source.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "SOURCE_DIGEST_MISMATCH"):
                read_swing_complete_session_observations(
                    self.at(18), folder, calendar_session_certified=True, **opts)

    def test_swing_quick_scan_retains_existing_scanner_without_dispatch(self):
        route = route_command("Sky 波段快掃")
        self.assertEqual(route.data_mode, "SESSION_ADAPTIVE_SWING_RESEARCH")
        self.assertIn("src.swing_live_scanner --mode swing", route.execution_target)
        self.assertIn("sky_swing_session_policy", route.execution_target)
        self.assertIn("No dispatch", route.notes)


if __name__ == "__main__":
    unittest.main()
