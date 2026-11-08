"""Synthetic tests for declared-interval portfolio risk reservation."""
import unittest
from portfolio_reservations import reserve_intervals
from test_comparison import trade


def candidate(i, symbol, start="2026-11-09T09:15:00+08:00",
              end="2026-11-10T13:30:00+08:00"):
    r=trade(id=f"res-{i}")
    r["symbol"]=symbol
    r["decision_at"]=start
    r["exit_at"]=end
    return r


class ReservationTests(unittest.TestCase):
    def test_three_names_accepted(self):
        rs=[candidate(1,"1101"),candidate(2,"1102"),candidate(3,"1103")]
        out=reserve_intervals(rs)
        self.assertEqual(len(out["accepted_ids"]),3)
        self.assertEqual(out["peak_reserved_names"],3)
        self.assertFalse(out["portfolio_validated"])

    def test_fourth_name_rejected(self):
        rs=[candidate(i,str(i+1100)) for i in range(1,5)]
        out=reserve_intervals(rs)
        self.assertEqual(len(out["accepted_ids"]),3)
        self.assertEqual(out["rejected"][0]["reason"],"MAX_THREE_NAMES")

    def test_same_symbol_cannot_overlap(self):
        out=reserve_intervals([candidate(1,"1101"),candidate(2,"1101")])
        self.assertEqual(out["rejected"][0]["reason"],"SAME_SYMBOL_OVERLAP")

    def test_exit_at_entry_releases(self):
        earlier=candidate(1,"1101")
        later=candidate(2,"1101",start=earlier["exit_at"],
                        end="2026-11-11T13:30:00+08:00")
        out=reserve_intervals([later,earlier])
        self.assertEqual(len(out["accepted_ids"]),2)
        self.assertEqual(out["peak_reserved_names"],1)

    def test_invalid_exit(self):
        r=candidate(1,"1101");r["exit_at"]=r["decision_at"]
        with self.assertRaisesRegex(ValueError,"noncausal_exit"):
            reserve_intervals([r])

    def test_missing_timestamp_rejected(self):
        r=candidate(1,"1101");r["exit_at"]="2026-11-10T13:30:00"
        with self.assertRaisesRegex(ValueError,"timezone_required"):
            reserve_intervals([r])

    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError,"duplicate"):
            reserve_intervals([candidate(1,"1101"),candidate(1,"1102")])

    def test_declared_execution_only(self):
        r=candidate(1,"1101");r["execution_evidence"]="ACTUAL"
        with self.assertRaisesRegex(ValueError,"simulation_only"):
            reserve_intervals([r])

    def test_reservation_does_not_claim_pnl(self):
        out=reserve_intervals([candidate(1,"1101")])
        self.assertIsNone(out["portfolio_max_drawdown"])
        self.assertFalse(out["daily_loss_kill_switch_validated"])
        self.assertFalse(out["actual_execution_validated"])
        self.assertEqual(out["status"],"INSUFFICIENT_DATA")


if __name__=="__main__":
    unittest.main()
