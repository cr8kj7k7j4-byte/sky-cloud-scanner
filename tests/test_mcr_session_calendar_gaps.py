import unittest
from research.mcr_session_calendar import build_calendar
from research.mcr_forward_markouts import research_markouts
from research.mcr_evidence_gaps import build_gap_report

def snapshot(day,*,symbols=("1101",),tpex=("8088",)):
    rows=[]
    for market,source,codes in (("TWSE","TWSE_OFFICIAL_DAILY",symbols),("TPEx","TPEX_OFFICIAL_DAILY",tpex)):
        for code in codes:
            rows.append({"exchange":market,"symbol":code,"session":day,
               "source":source,"close":10.0,"captured_at":day+"T19:00:00+08:00",
               "adjusted":False})
    return {"schema":"MCR_OFFICIAL_EOD_PRICES_V1","session":day,
       "recorded_at":day+"T19:00:00+08:00","total":len(rows),
       "rows":rows,"market_counts":{"TWSE":len(symbols),"TPEx":len(tpex)},
       "execution_authorized":False,"historical_backfill":False,
       "mode":"RESEARCH_REFERENCE_ONLY"}
def episode():
    return {"episode_id":"e1","market":"TWSE","symbol":"1101",
        "first_session":"2026-11-06","candidate_signal_only":True,"trade_eligible":False}
def run_markouts(docs,*,asof=None):
    c=build_calendar(docs)
    p=[r for d in docs for r in d["rows"]]
    a=asof or docs[-1]["session"]
    return research_markouts([episode()],p,asof_session=a,session_calendar=c),c

class CalendarTests(unittest.TestCase):
    def test_complete_fri_monday_tuesday(self):
        docs=[snapshot("2026-11-06"),snapshot("2026-11-09"),snapshot("2026-11-10")]
        m,c=run_markouts(docs)
        self.assertEqual(c["unverified_weekday_gaps"],[])
        self.assertEqual(m["reference_horizons_complete"],1)
        self.assertEqual(m["results"][0]["horizons"]["1"]["followup_session"],"2026-11-10")
        self.assertEqual(m["trade_count"],0)
        self.assertIsNone(m["cost_adjusted_expectancy_pct"])
    def test_missing_tuesday_never_count_wednesday_as_second_day(self):
        docs=[snapshot("2026-11-06"),snapshot("2026-11-09"),snapshot("2026-11-11")]
        m,c=run_markouts(docs)
        self.assertEqual(c["unverified_weekday_gaps"],["2026-11-10"])
        self.assertEqual(m["reference_horizons_complete"],0)
        self.assertEqual(m["results"][0]["horizon_gaps"]["1"],"UNVERIFIED_SESSION_GAP")
    def test_symbol_suspended_on_required_day_never_shift(self):
        docs=[snapshot("2026-11-06"),snapshot("2026-11-09"),
            snapshot("2026-11-10",symbols=("1102",)),snapshot("2026-11-11")]
        m,c=run_markouts(docs)
        self.assertEqual(c["unverified_weekday_gaps"],[])
        self.assertEqual(m["reference_horizons_complete"],0)
        self.assertEqual(m["results"][0]["horizon_gaps"]["1"],"MISSING_PRICE_ON_REQUIRED_SESSION")
    def test_missing_reference_never_shifts(self):
        docs=[snapshot("2026-11-06"),snapshot("2026-11-09",symbols=("1102",)),
            snapshot("2026-11-10")]
        m,_=run_markouts(docs)
        self.assertEqual(m["results"][0]["status"],"MISSING_REFERENCE_PRICE")
    def test_missing_market_rejected(self):
        d=snapshot("2026-11-09");d["rows"]=[r for r in d["rows"] if r["exchange"]=="TWSE"]
        d["total"]=len(d["rows"]);d["market_counts"]={"TWSE":1}
        with self.assertRaisesRegex(ValueError,"MISSING_EXCHANGE_SOURCE"):
            build_calendar([d])
    def test_duplicate_day_and_mixed_date_rejected(self):
        d=snapshot("2026-11-09")
        with self.assertRaisesRegex(ValueError,"DUPLICATE_MARKET_SESSION"):
            build_calendar([d,d])
        d["rows"][0]["session"]="2026-11-10"
        with self.assertRaisesRegex(ValueError,"MIXED_OFFICIAL_SESSION"):
            build_calendar([d])
    def test_no_verified_calendar_cannot_create_result(self):
        docs=[snapshot("2026-11-06"),snapshot("2026-11-09"),snapshot("2026-11-10")]
        p=[r for d in docs for r in d["rows"]]
        out=research_markouts([episode()],p,asof_session="2026-11-10")
        self.assertEqual(out["results"][0]["status"],"PENDING_SESSION_CALENDAR")
        self.assertEqual(out["reference_horizons_complete"],0)

class GapReportTests(unittest.TestCase):
    def test_gap_categorization_not_pnl(self):
        docs=[snapshot("2026-11-06"),snapshot("2026-11-09"),snapshot("2026-11-11")]
        m,c=run_markouts(docs)
        e={"schema":"MCR_EPISODE_AUDIT_V1","last_session":"2026-11-11",
            "episodes":[episode()],"episode_count":1,"sessions":1,
            "observation_rows":1,"production_promotion_eligible":False,
            "cost_adjusted_expectancy_pct":None}
        report=build_gap_report(e,m,c,latest_price_session="2026-11-11")
        self.assertEqual(report["engineering_data_status"],"DATA_GAP")
        self.assertFalse(report["production_promotion_eligible"])
        self.assertIn("2026-11-10",report["unverified_calendar_gap_dates"])
        self.assertIsNone(report["cost_adjusted_expectancy_pct"])
        self.assertTrue(any(x["key"]=="UNVERIFIED_MARKET_SESSION_GAPS" for x in report["blockers"]))
    def test_mismatched_current_price_date_reported(self):
        docs=[snapshot("2026-11-06")]
        m,c=run_markouts(docs)
        e={"schema":"MCR_EPISODE_AUDIT_V1","last_session":"2026-11-06",
            "episodes":[episode()],"episode_count":1,"sessions":1,
            "observation_rows":1,"production_promotion_eligible":False,
            "cost_adjusted_expectancy_pct":None}
        report=build_gap_report(e,m,c,latest_price_session="2026-11-05")
        self.assertEqual(report["blockers"][0]["key"],"FINANCING_PRICE_SESSION_MISMATCH")

if __name__=="__main__":unittest.main()
