import unittest
from datetime import datetime,timezone
from research.mcr_episode_audit import build_episode_audit
from research.mcr_forward_markouts import research_markouts

def event(s,market="TWSE",day="2026-11-06"):
    return {"symbol":s,"market":market,"source_session":day,"execution_authorized":False,
            "outcome_evidence":None}
def ledger(day,ids):
    return {"schema":"MCR_PROXY_OBSERVATION_V1","research_only":True,
            "cannot_assume_pnl":True,"source_coverage":"TWSE_TPEX_VERIFIED",
            "session":day,"total":len(ids),"events":[event(s,day=day) for s in ids]}
def price(day,val,source="TWSE_OFFICIAL_DAILY",captured=None):
    return {"exchange":"TWSE","symbol":"1101","session":day,"close":val,
      "source":source,"captured_at":captured or day+"T19:00:00+08:00","adjusted":False}
class AuditTests(unittest.TestCase):
    def test_one_day_520_not_trades(self):
        doc=ledger("2026-11-06",["1101","1102","1103"])
        out=build_episode_audit([doc])
        self.assertEqual(out["sessions"],1)
        self.assertEqual(out["episode_count"],3)
        self.assertEqual(out["independent_trade_sample_count"],0)
        self.assertIsNone(out["cost_adjusted_expectancy_pct"])
        self.assertEqual(out["research_status"],"INSUFFICIENT_DATA")
    def test_duplicate_continuation_one_episode(self):
        out=build_episode_audit([ledger("2026-11-06",["1101","1102"]),
                                 ledger("2026-11-09",["1101"])])
        self.assertEqual(out["episode_count"],2)
        self.assertEqual(out["observation_rows"],3)
        self.assertEqual(out["repeated_daily_observations"],1)
        self.assertEqual(out["episodes"][0]["observation_days"],2)
    def test_new_episode_after_gap(self):
        out=build_episode_audit([ledger("2026-11-06",["1101"]),
                                 ledger("2026-11-16",["1101"])])
        self.assertEqual(out["episode_count"],2)
    def test_duplicate_session_or_symbol_rejected(self):
        a=ledger("2026-11-06",["1101"])
        with self.assertRaisesRegex(ValueError,"DUPLICATE_SESSION"):
            build_episode_audit([a,a])
        b=ledger("2026-11-06",["1101","1101"])
        with self.assertRaisesRegex(ValueError,"DUPLICATE_DAILY_SYMBOL"):
            build_episode_audit([b])
    def test_bias_counts_are_descriptive(self):
        source={"margin_data_date":"2026-11-06","total":2,
                "rows":[{"exchange":"TWSE","two_session_reduction_pct":25,
                         "margin_balance_current_units":250,"daily_volume_shares":50000},
                        {"exchange":"TPEx","two_session_reduction_pct":5,
                         "margin_balance_current_units":2000,"daily_volume_shares":None}]}
        out=build_episode_audit([ledger("2026-11-06",["1101","1102"])],source_merged=source)
        self.assertEqual(out["bias_diagnostics"]["post_financing_balance_under_500_units"],1)
        self.assertEqual(out["bias_diagnostics"]["volume_evidence_missing"],1)
        self.assertEqual(out["bias_diagnostics"]["reduction_at_least_20_pct"],1)

class MarkoutTests(unittest.TestCase):
    def episodes(self):
        return build_episode_audit([ledger("2026-11-06",["1101"])])["episodes"]
    def test_no_future_data_is_pending_not_loss(self):
        r=research_markouts(self.episodes(),[],asof_session="2026-11-08")
        self.assertEqual(r["results"][0]["status"],"PENDING_FORWARD_SESSIONS")
        self.assertEqual(r["trade_count"],0)
        self.assertIsNone(r["cost_adjusted_expectancy_pct"])
    def test_reference_markouts_cannot_be_claimed_as_real_fills(self):
        prices=[price("2026-11-09",10),price("2026-11-10",11),
                price("2026-11-11",12),price("2026-11-12",13)]
        r=research_markouts(self.episodes(),prices,asof_session="2026-11-12")
        h=r["results"][0]["horizons"]
        self.assertEqual(h["1"]["long_reference_change_pct"],10.0)
        self.assertFalse(h["1"]["execution_validated"])
        self.assertIsNone(h["1"]["cost_adjusted_pnl_pct"])
    def test_future_leak_and_missing_provider_rejected(self):
        with self.assertRaisesRegex(ValueError,"FUTURE_DATA_LEAK"):
            research_markouts(self.episodes(),[price("2026-11-09",10)],asof_session="2026-11-08")
        with self.assertRaisesRegex(ValueError,"UNVERIFIED_PRICE_SOURCE"):
            research_markouts(self.episodes(),[price("2026-11-09",10,source="FAKE")],asof_session="2026-11-09")
    def test_duplicate_price_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_PRICE"):
            research_markouts(self.episodes(),[price("2026-11-09",10),price("2026-11-09",11)],asof_session="2026-11-09")

if __name__=="__main__":unittest.main()
