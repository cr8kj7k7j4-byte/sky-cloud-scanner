"""Normalize validated raw reports as descriptive evidence, never signals."""
import argparse
import hashlib
import json
from pathlib import Path

TW_FIELDS = ['代號', '名稱', '買進', '賣出', '現金償還', '前日餘額', '今日餘額']
OTC_FIELDS = ['代號', '名稱', '前資餘額(張)', '資買', '資賣', '現償', '資餘額']

def integer(value):
    s = str(value).replace(',', '').strip()
    if not s.isdecimal():
        raise ValueError('invalid non-negative integer: ' + repr(value))
    return int(s)

def normalize(path):
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('collection_status') != 'PASS' or set(manifest.get('sources', {})) != {'TWSE', 'TPEx'}:
        raise ValueError('both sources must pass collection')
    records = []
    seen = set()
    for market in ('TWSE', 'TPEx'):
        source = manifest['sources'][market]
        filename = source.get('file', '')
        if source.get('status') != 'PASS' or not filename or Path(filename).name != filename:
            raise ValueError('invalid source path or status')
        raw = (path / filename).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source.get('sha256'):
            raise ValueError('source hash mismatch')
        obj = json.loads(raw.decode('utf-8-sig'))
        tables = obj.get('tables', [])
        prefix = TW_FIELDS if market == 'TWSE' else OTC_FIELDS
        matches = [t for t in tables if t.get('fields', [])[:len(prefix)] == prefix]
        if len(matches) != 1:
            raise ValueError('missing or ambiguous report schema')
        for row in matches[0].get('data', []):
            if len(row) < len(prefix):
                raise ValueError('short source row')
            code, name = str(row[0]).strip(), str(row[1]).strip()
            if not code or not name or (market, code) in seen:
                raise ValueError('missing or duplicate security')
            seen.add((market, code))
            if market == 'TWSE':
                buy, sell, repay, prev, curr = map(integer, row[2:7])
            else:
                prev, buy, sell, repay, curr = map(integer, row[2:7])
            records.append({'market': market, 'code': code, 'name': name,
                'previous_balance_units': prev, 'buy_units': buy,
                'sell_units': sell, 'cash_repayment_units': repay,
                'current_balance_units': curr, 'change_units': curr-prev})
    result = {'schema_version': 'MARGIN_RAW_NORMALIZED_V1',
        'requested_date': manifest['requested_date'],
        'retrieved_at': {k: v['retrieved_at'] for k,v in manifest['sources'].items()},
        'sources': {k: {'sha256': v['sha256'], 'url': v['url']} for k,v in manifest['sources'].items()},
        'status': 'DESCRIPTIVE_ONLY', 'historical_pit_verified': False,
        'force_liquidation_identified': False, 'trade_signal': False,
        'coverage_verified': False, 'scope': 'all securities in source reports; ordinary-stock eligibility not checked',
        'units_note': 'source report trading units; no inference of forced sales',
        'records': records}
    (path / 'normalized.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='output/margin_evidence')
    args = parser.parse_args()
    result = normalize(args.input)
    print(json.dumps({'status': result['status'], 'record_count': len(result['records']), 'trade_signal': False}))
