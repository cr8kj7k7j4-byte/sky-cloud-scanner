"""Collect contemporaneous public margin reports, not trading signals."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Taipei')
SOURCES = {
    'TWSE': 'https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN',
    'TPEx': 'https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php',
}

def validate(source, payload, day):
    if not isinstance(payload, dict):
        raise ValueError('response is not an object')
    if source == 'TWSE':
        if payload.get('stat') != 'OK' or str(payload.get('date', '')) != day.strftime('%Y%m%d'):
            raise ValueError('TWSE status or report date mismatch')
        tables = payload.get('tables', [])
        valid = [t for t in tables if isinstance(t, dict) and isinstance(t.get('data'), list) and len(t['data']) >= 100 and t.get('fields', [])[:2] == ['代號', '名稱']]
        if not valid:
            raise ValueError('TWSE individual security table absent or incomplete: ' + repr([(t.get('title'), t.get('fields', [])[:3], len(t.get('data', []))) for t in tables if isinstance(t, dict)])[:700])
        return len(valid[0]['data'])
    dates = {day.strftime('%Y/%m/%d'), f'{day.year - 1911}/{day.month:02d}/{day.day:02d}', day.strftime('%Y%m%d')}
    value = str(payload.get('reportDate', payload.get('date', ''))).strip()
    tables = payload.get('tables') or []
    rows = payload.get('aaData') or payload.get('data') or (tables[0].get('data') if tables and isinstance(tables[0], dict) else None)
    if value not in dates or not isinstance(rows, list) or len(rows) < 100:
        raise ValueError('TPEx report date mismatch or individual table absent')
    return len(rows)

def fetch(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 SkyResearchDataAudit/1.0', 'Accept': 'application/json'})
    with urlopen(req, timeout=35) as response:
        return response.read(15_000_001)

def run(day, out, getter=fetch):
    out.mkdir(parents=True, exist_ok=True)
    result = {'research_status': 'HOLD', 'trade_signal': False, 'requested_date': day.isoformat(), 'generated_at': dt.datetime.now(TZ).isoformat(), 'historical_pit_verified': False, 'sources': {}}
    queries = {
        'TWSE': {'date': day.strftime('%Y%m%d'), 'response': 'json', 'selectType': 'ALL'},
        'TPEx': {'d': f'{day.year-1911}/{day.month:02d}/{day.day:02d}', 'l': 'zh-tw', 'o': 'json'},
    }
    for name, endpoint in SOURCES.items():
        url = endpoint + '?' + urlencode(queries[name])
        record = {'url': url, 'status': 'FAIL', 'retrieved_at': None}
        try:
            raw = getter(url)
            record['retrieved_at'] = dt.datetime.now(TZ).isoformat()
            if len(raw) > 15_000_000:
                raise ValueError('response exceeds size limit')
            obj = json.loads(raw.decode('utf-8-sig'))
            count = validate(name, obj, day)
            filename = f'{name.lower()}-{day.isoformat()}.json'
            (out / filename).write_bytes(raw)
            record.update(status='PASS', rows=count, sha256=hashlib.sha256(raw).hexdigest(), file=filename)
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}: {str(exc)[:300]}'
        result['sources'][name] = record
    result['collection_status'] = 'PASS' if all(x['status'] == 'PASS' for x in result['sources'].values()) else 'FAIL'
    (out / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', help='YYYY-MM-DD; diagnostic only')
    parser.add_argument('--output', default='output/margin_evidence')
    args = parser.parse_args()
    day = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(TZ).date()
    result = run(day, Path(args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write(f"## 融資資料研究蒐集：{result['collection_status']}\n\n資料日：{day}。研究狀態 HOLD；沒有交易訊號。\n\n歷史時點資料、策略效果與實際斷頭均未驗證。原始報表與來源狀態請見 artifact。\n")
    if result['collection_status'] != 'PASS':
        raise SystemExit(1)

if __name__ == '__main__':
    main()
