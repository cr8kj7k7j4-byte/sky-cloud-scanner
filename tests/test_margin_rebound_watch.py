import unittest
from collections import deque
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from research.margin_rebound_watch import evaluate

TZ = ZoneInfo("Asia/Taipei")

class MarginWatchTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 9, 9, 2, 30, tzinfo=TZ)
        self.samples = deque(maxlen=10)

    def row(self, age, price, vol, tick=1):
        return {"date": (self.now-timedelta(seconds=age)).strftime("%Y-%m-%d %H:%M:%S"),
                "close": price, "total_volume": vol, "TickType": tick,
                "buy_price": price-.05, "sell_price": price}

    def test_three_distinct_buy_snapshots(self):
        self.assertFalse(evaluate(self.samples,self.row(30,50,100),self.now))
        self.assertFalse(evaluate(self.samples,self.row(20,50.2,110),self.now))
        self.assertTrue(evaluate(self.samples,self.row(10,50.5,120),self.now))

    def test_duplicate_is_not_a_new_trade(self):
        r=self.row(15,50,100)
        evaluate(self.samples,r,self.now)
        self.assertFalse(evaluate(self.samples,r,self.now))
        self.assertEqual(len(self.samples),1)

    def test_stale_rejected(self):
        self.assertFalse(evaluate(self.samples,self.row(90,50,100),self.now))

    def test_sell_in_streak_rejected(self):
        for r in (self.row(30,50,100),self.row(20,50.2,110,2),self.row(10,50.5,120)):
            self.assertFalse(evaluate(self.samples,r,self.now))

    def test_nonmonotonic_price_rejected(self):
        for r in (self.row(30,50,100),self.row(20,49.9,110),self.row(10,50.5,120)):
            self.assertFalse(evaluate(self.samples,r,self.now))

if __name__ == "__main__":
    unittest.main()
