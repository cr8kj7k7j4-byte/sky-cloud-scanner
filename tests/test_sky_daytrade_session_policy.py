"""W0 #363: session-selector regressions, no quote/API/network access."""
import unittest
from datetime import datetime, timedelta, timezone

from src.sky_daytrade_session_policy import daytrade_session_policy
from src.sky_command_router import route_command


TPE = timezone(timedelta(hours=8))


class SessionPolicyTests(unittest.TestCase):
    def at(self, hour, minute=0):
        return datetime(2026, 11, 27, hour, minute, tzinfo=TPE)

    def test_all_sessions_allow_research_without_sample_count_or_live_claim(self):
        for hour in (4, 9, 13, 18, 23):
            for verified in (True, False, None):
                result = daytrade_session_policy(self.at(hour), trading_day_verified=verified)
                access = result["research_access"]
                self.assertTrue(access["research_processing_allowed"])
                self.assertFalse(access["requires_market_open_for_research"])
                self.assertFalse(access["requires_sample_minimum_for_research"])
                self.assertFalse(result["new_entry_authorized"])
                self.assertFalse(access["production_eligible"])

    def test_premarket_research(self):
        p = daytrade_session_policy(self.at(4, 38), trading_day_verified=True)
        self.assertEqual(p["session_mode"], "PREMARKET_RESEARCH")
        self.assertFalse(p["allow_live_quote_claim"])
        self.assertFalse(p["new_entry_authorized"])

    def test_verified_session_selection_not_authorization(self):
        p = daytrade_session_policy(self.at(9, 15), trading_day_verified=True)
        self.assertEqual(p["session_mode"], "INTRADAY_A1_A2")
        self.assertTrue(p["allow_live_quote_claim"])
        self.assertFalse(p["new_entry_authorized"])
        self.assertTrue(p["requires_a1_a2_for_new_entry"])

    def test_unknown_calendar_does_not_claim_live(self):
        p = daytrade_session_policy(self.at(9, 15))
        self.assertEqual(p["session_mode"], "INTRADAY_CALENDAR_UNVERIFIED_RESEARCH")
        self.assertFalse(p["allow_live_quote_claim"])

    def test_postmarket_research(self):
        p = daytrade_session_policy(self.at(14), trading_day_verified=True)
        self.assertEqual(p["session_mode"], "POSTMARKET_RESEARCH")
        self.assertFalse(p["new_entry_authorized"])

    def test_exchange_verified_nontrading_day_wins(self):
        p = daytrade_session_policy(self.at(10), trading_day_verified=False)
        self.assertEqual(p["session_mode"], "NON_TRADING_DAY_RESEARCH")
        self.assertFalse(p["allow_live_quote_claim"])

    def test_time_boundary(self):
        self.assertEqual(daytrade_session_policy(self.at(9), trading_day_verified=True)["session_mode"], "INTRADAY_A1_A2")
        self.assertEqual(daytrade_session_policy(self.at(13, 30), trading_day_verified=True)["session_mode"], "INTRADAY_A1_A2")
        self.assertEqual(daytrade_session_policy(self.at(13, 31), trading_day_verified=True)["session_mode"], "POSTMARKET_RESEARCH")

    def test_input_must_be_timezone_aware(self):
        with self.assertRaises(ValueError):
            daytrade_session_policy(datetime(2026, 11, 27, 10))
        with self.assertRaises(ValueError):
            daytrade_session_policy(self.at(10), trading_day_verified="yes")

    def test_utc_translated_to_tpe(self):
        utc = self.at(14).astimezone(timezone.utc)
        self.assertEqual(daytrade_session_policy(utc, trading_day_verified=True)["session_mode"], "POSTMARKET_RESEARCH")

    def test_historical_label_not_proof(self):
        p = daytrade_session_policy(self.at(4), latest_complete_session_date="2026-11-26")
        self.assertEqual(p["latest_complete_session_date"], "2026-11-26")
        self.assertFalse(p["historical_artifact_verified"])
        self.assertEqual(p["status"], "HOLD_EVIDENCE")

    def test_shortcut_route_keeps_single_scanner_and_live_safety(self):
        r = route_command("Sky 當沖快掃")
        self.assertEqual(r.command_family, "SKY_DAYTRADE_SCAN")
        self.assertEqual(r.data_mode, "SESSION_ADAPTIVE_DAYTRADE_RESEARCH")
        self.assertTrue(r.realtime_required)
        self.assertTrue(r.whole_market_required)
        self.assertIn("src.main", r.execution_target)


if __name__ == "__main__":
    unittest.main()
