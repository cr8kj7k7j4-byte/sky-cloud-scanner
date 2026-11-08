import unittest
from datetime import date, datetime, timedelta, timezone, time

from research.ai_direction_labels import build_audit, build_rows


TPE = timezone(timedelta(hours=8))


def bar(stamp, base=40):
    price = float(base)
    return {"timestamp":stamp.isoformat(),"open":price,"high":price+1,
            "low":price-1,"close":price+0.25,"volume":1000}


def payload(kind, *, bar_end=True):
    day = date(2026, 1, 5)
    bars=[]
    if kind=="next_day":
        for i in range(27):
            d = day + timedelta(days=i)
            bars.append(bar(datetime.combine(d,time(13,30),TPE),40+i*.1))
    else:
        for day_offset in range(2):
            d = day + timedelta(days=day_offset)
            clock=datetime.combine(d,time(9,0),TPE)
            for j in range(54):
                bars.append(bar(clock+timedelta(minutes=5*j),40+day_offset))
    return {"source":"FUGLE","as_of":datetime(2026,2,15,tzinfo=TPE).isoformat(),
            "bar_timestamp_semantics":"BAR_END" if bar_end else "UNKNOWN",
            "symbols":{"2330": {"bars_daily":bars} if kind=="next_day" else {"bars_5m":bars}}}


class HorizonLabelsTests(unittest.TestCase):
    def test_next_day_label_uses_next_session_open_and_close(self):
        p=payload("next_day")
        r=build_rows(p,horizon="next_day")
        self.assertGreater(len(r),0)
        first=r[0]
        self.assertLess(first["date"], first["label_start_at"])
        self.assertLess(first["label_start_at"],first["label_end_at"])
        self.assertAlmostEqual(first["target_return_pct"], (42.35/42.1-1)*100)
        self.assertEqual(first["feature_available_at"],first["date"])
        self.assertFalse(build_audit(p,"next_day")["production_eligible"])

    def test_intraday_uses_completed_0930_then_0935_open_to_1320_close(self):
        rows=build_rows(payload("intraday"),horizon="intraday")
        self.assertTrue(rows)
        self.assertTrue(all(x["date"].endswith("09:30:00+08:00") for x in rows))
        self.assertTrue(all(x["label_start_at"].endswith("09:35:00+08:00") for x in rows))
        self.assertTrue(all(x["label_end_at"].endswith("13:20:00+08:00") for x in rows))

    def test_unverified_bar_semantics_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"semantics"):
            build_rows(payload("intraday",bar_end=False),horizon="intraday")

    def test_missing_middle_bar_is_not_accepted(self):
        p = payload("intraday")
        bars = p["symbols"]["2330"]["bars_5m"]
        # Remove a completed bar from the second day's 10:00 path.
        p["symbols"]["2330"]["bars_5m"] = [
            b for b in bars if not b["timestamp"].startswith("2026-01-06T10:00:00")
        ]
        self.assertEqual(build_rows(p, horizon="intraday"), [])

    def test_bad_source_rejected(self):
        p=payload("next_day");p["source"]="SIMULATED"
        with self.assertRaises(ValueError):
            build_rows(p,horizon="next_day")

    def test_partial_intraday_session_produces_no_fabricated_labels(self):
        p=payload("intraday")
        p["symbols"]["2330"]["bars_5m"] = p["symbols"]["2330"]["bars_5m"][:25]
        self.assertEqual(build_rows(p,horizon="intraday"),[])


if __name__=="__main__":
    unittest.main()
