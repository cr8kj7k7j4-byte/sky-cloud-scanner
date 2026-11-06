import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('collect', Path(__file__).with_name('collect.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.day = dt.date(2026, 10, 30)
        self.twse = {'stat': 'OK', 'date': '20261030', 'tables': [{'fields':['代號','名稱'], 'data': [['2330','台積電']]*100}]}
        self.tpex = {'reportDate': '115/10/30', 'aaData': [['1234']]*100}
    def test_both_sources_and_hash(self):
        def fake(url):
            return json.dumps(self.twse if 'twse.com.tw' in url else self.tpex).encode()
        with tempfile.TemporaryDirectory() as d:
            result = m.run(self.day, Path(d), fake)
            self.assertEqual(result['collection_status'], 'PASS')
            self.assertFalse(result['trade_signal'])
            self.assertEqual(len(result['sources']['TWSE']['sha256']), 64)
    def test_stale_date_and_missing_data_fail_closed(self):
        self.twse['date'] = '20261029'
        self.tpex['aaData'] = []
        with tempfile.TemporaryDirectory() as d:
            result = m.run(self.day, Path(d), lambda url: json.dumps(self.twse if 'twse.com.tw' in url else self.tpex).encode())
            self.assertEqual(result['collection_status'], 'FAIL')
            self.assertEqual(result['research_status'], 'HOLD')
    def test_scheduled_run_delayed_past_taiwan_midnight(self):
        # 15:30 UTC = 23:30 Asia/Taipei; delayed start at 16:33 UTC
        # is already November 6 local time but still requests Nov 5.
        delayed = dt.datetime(2026, 11, 5, 16, 33, tzinfo=dt.timezone.utc)
        self.assertEqual(delayed.astimezone(m.TZ).date(), dt.date(2026, 11, 6))
        self.assertEqual(m.scheduled_utc_report_date(delayed), dt.date(2026, 11, 5))
        with self.assertRaises(ValueError):
            m.scheduled_utc_report_date(dt.datetime(2026, 11, 5, 16, 33))

    def test_transport_failure_is_reported(self):
        def failed(url):
            raise TimeoutError('network')
        with tempfile.TemporaryDirectory() as d:
            result = m.run(self.day, Path(d), failed)
            self.assertEqual(result['sources']['TWSE']['status'], 'FAIL')
            self.assertTrue((Path(d) / 'manifest.json').exists())

if __name__ == '__main__':
    unittest.main()
