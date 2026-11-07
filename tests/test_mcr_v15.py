import unittest

from research.mcr_v15 import Financing, Tape, Portfolio, classify, evaluate_payload


def fixture():
    fin = Financing("1101", "2026-11-06", "2026-11-06T22:30:00+08:00",
                    estimated_maintenance_pct=125, margin_balance=800,
                    previous_margin_balance=1000, margin_cost=44)
    tape = Tape("2026-11-09T09:30:00+08:00", price=40, volume=10000,
                aggressive_buy_volume=6000, aggressive_sell_volume=4000,
                bid=39.95, ask=40, vwap=39.5, prior_low=39.2,
                resistance=39.8, previous_sell_impact=.9,
                current_sell_impact=.4, market_gate=True, event_risk_clear=True)
    p = Portfolio(daily_net_pnl=0, open_risk=0, open_positions=0, consecutive_losses=0)
    return fin, tape, p


class TestMCR(unittest.TestCase):
    def test_research_only_even_when_all_conditions_pass(self):
        f,t,p=fixture()
        result=classify(f,t,p,entry=40,stop=39,target=43)
        self.assertEqual(result["classification"], "A_RESEARCH_ONLY")
        self.assertEqual(result["action"], "等待")
        self.assertFalse(result["production_signal"])
        self.assertTrue(result["features"]["research_reversal_pattern"])
        self.assertAlmostEqual(result["features"]["margin_balance_change_pct"], -20)

    def test_future_financing_is_rejected(self):
        f,t,p=fixture()
        f=Financing("1101","2026-11-09","2026-11-09T22:30:00+08:00",125,800,1000,44)
        result=classify(f,t,p,entry=40,stop=39,target=43)
        self.assertIn("LOOK_AHEAD_FINANCING",result["failed"])
        self.assertIn("SAME_DAY_FINANCING_NOT_ELIGIBLE",result["failed"])

    def test_missing_aggessor_and_portfolio_cannot_be_ready(self):
        f,t,_=fixture()
        t=Tape("2026-11-09T09:30:00+08:00",40,10000)
        result=classify(f,t,entry=40,stop=39,target=43)
        self.assertEqual(result["classification"],"WATCH")
        self.assertIn("CURRENT_PORTFOLIO_STATE",result["missing"])
        self.assertIn("AGGRESSOR_CLASSIFIED_TRADES",result["missing"])

    def test_stop_and_cost_gate(self):
        f,t,p=fixture()
        r=classify(f,t,p,entry=40,stop=36,target=42)
        self.assertIn("AFTER_COST_RR_BELOW_1_5",r["failed"])
        self.assertIsNone(classify(f,t,p)["features"]["rr_primary"])

    def test_daily_kill_switch(self):
        f,t,p=fixture()
        p=Portfolio(daily_net_pnl=-10000,open_risk=0,open_positions=0,consecutive_losses=0)
        self.assertIn("DAILY_KILL_SWITCH",classify(f,t,p,entry=40,stop=39,target=43)["failed"])

    def test_short_side_is_not_authorized(self):
        f,t,p=fixture()
        r=classify(f,t,p,side="SHORT",entry=40,stop=41,target=37)
        self.assertEqual(r["classification"],"X")
        self.assertFalse(r["production_signal"])

    def test_bad_timestamp_rejected(self):
        f,t,p=fixture()
        f=Financing("1101","2026-11-06","2026-11-06T22:30:00",125,800,1000,44)
        self.assertIn("INVALID_TIMESTAMP",classify(f,t,p)["failed"])

    def test_payload(self):
        f,t,p=fixture()
        from dataclasses import asdict
        r=evaluate_payload({"financing":asdict(f),"tape":asdict(t),"portfolio":asdict(p),
                            "entry":40,"stop":39,"target":43})
        self.assertFalse(r["production_signal"])


if __name__ == "__main__":
    unittest.main()
