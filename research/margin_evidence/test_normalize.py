import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('normalize', Path(__file__).with_name('normalize.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class NormalizeTests(unittest.TestCase):
    def make(self, folder):
        tw = {'tables':[{'fields':m.TW_FIELDS, 'data':[['2330','台積電','10','20','2','1,000','988']]}]}
        ot = {'tables':[{'fields':m.OTC_FIELDS, 'data':[['6488','環球晶','2,000','8','18','1','1,989']]}]}
        sources={}
        for name, obj in [('TWSE',tw),('TPEx',ot)]:
            raw=json.dumps(obj,ensure_ascii=False).encode()
            file=name+'.json'; (folder/file).write_bytes(raw)
            sources[name]={'status':'PASS','file':file,'sha256':hashlib.sha256(raw).hexdigest(),'url':'official','retrieved_at':'2026-11-01T10:00:00+08:00'}
        (folder/'manifest.json').write_text(json.dumps({'collection_status':'PASS','requested_date':'2026-10-30','sources':sources}),encoding='utf-8')
    def test_normalize_and_no_signal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); self.make(p); out=m.normalize(p)
            self.assertEqual([r['change_units'] for r in out['records']],[-12,-11])
            self.assertFalse(out['trade_signal']); self.assertFalse(out['historical_pit_verified'])
    def test_reject_tampered_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); self.make(p); (p/'TWSE.json').write_text('{}')
            with self.assertRaises(ValueError): m.normalize(p)
    def test_duplicate_symbol_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); self.make(p)
            f=p/'TWSE.json'; obj=json.loads(f.read_text());obj['tables'][0]['data']*=2
            raw=json.dumps(obj).encode(); f.write_bytes(raw)
            mf=p/'manifest.json'; manifest=json.loads(mf.read_text()); manifest['sources']['TWSE']['sha256']=hashlib.sha256(raw).hexdigest(); mf.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError): m.normalize(p)

if __name__ == '__main__': unittest.main()
