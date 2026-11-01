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
        self.twse = {'stat': 'OK', 'date': '20261030', 'tables': [{'fields':['證券代號'], 'data': [['2330']]*100}]}
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
    def test_transport_failure_is_reported(self):
        def failed(url):
            raise TimeoutError('network')
        with tempfile.TemporaryDirectory() as d:
            result = m.run(self.day, Path(d), failed)
            self.assertEqual(result['sources']['TWSE']['status'], 'FAIL')
            self.assertTrue((Path(d) / 'manifest.json').exists())

if __name__ == '__main__':
    unittest.main()
