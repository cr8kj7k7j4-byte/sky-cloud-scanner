from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from research.download_expanded import get_hist

DEFAULT_BENCHMARK="IX0001"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--symbol',default=DEFAULT_BENCHMARK)
    ap.add_argument('--from-date',required=True)
    ap.add_argument('--to-date',required=True)
    ap.add_argument('--out',default='research_data/market_benchmark_5m.json')
    args=ap.parse_args()
    start=date.fromisoformat(args.from_date)
    end=date.fromisoformat(args.to_date)
    data=get_hist(args.symbol,start,end)
    payload={
        'schema_version':'MARKET_BENCHMARK_5M_V1_0',
        'symbol':args.symbol,
        'benchmark_name':'TAIEX' if args.symbol=='IX0001' else None,
        'from':args.from_date,'to':args.to_date,'timeframe':'5',
        'data':data,'source':'FUGLE_HISTORICAL_CANDLES','research_only':True,
    }
    p=Path(args.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'symbol':args.symbol,'bars':len(data),'from':args.from_date,'to':args.to_date},ensure_ascii=False))

if __name__=='__main__':
    main()