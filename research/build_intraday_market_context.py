from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.point_in_time_universe import universe_as_of

SCHEMA_VERSION="INTRADAY_MARKET_CONTEXT_V1_1"

def load_history_dir(path: str) -> pd.DataFrame:
    rows=[]
    for p in sorted(Path(path).glob('*_5.json')):
        obj=json.loads(p.read_text(encoding='utf-8'))
        symbol=str(obj.get('symbol') or p.name.split('_')[0])
        exchange=str(obj.get('exchange') or '')
        for b in obj.get('data') or []:
            rows.append({
                'symbol':symbol,'exchange':exchange,
                'timestamp':b.get('date'),'open':b.get('open'),
                'high':b.get('high'),'low':b.get('low'),
                'close':b.get('close'),'volume':b.get('volume'),
                'average':b.get('average'),
            })
    df=pd.DataFrame(rows)
    if not df.empty:
        df['timestamp']=pd.to_datetime(df['timestamp'],errors='coerce',utc=True)
        for c in ('open','high','low','close','volume','average'):
            df[c]=pd.to_numeric(df[c],errors='coerce')
        df=df[df['timestamp'].notna()].sort_values(['symbol','timestamp'])
    return df


def benchmark_returns_from_fugle_json(path: str) -> pd.DataFrame:
    obj=json.loads(Path(path).read_text(encoding='utf-8'))
    rows=[]
    for b in obj.get('data') or []:
        rows.append({'timestamp':b.get('date'),'open':b.get('open'),'close':b.get('close')})
    x=pd.DataFrame(rows)
    if x.empty:
        return pd.DataFrame(columns=['timestamp','available_at','market_return'])
    x['timestamp']=pd.to_datetime(x['timestamp'],errors='coerce',utc=True)
    x['open']=pd.to_numeric(x['open'],errors='coerce')
    x['close']=pd.to_numeric(x['close'],errors='coerce')
    x=x.dropna(subset=['timestamp','open','close']).sort_values('timestamp')
    x['available_at']=x['timestamp']+pd.Timedelta(minutes=5)
    x['session_date']=x['timestamp'].dt.tz_convert('Asia/Taipei').dt.date.astype(str)
    first=x.groupby('session_date',as_index=False).head(1)[['session_date','open']].rename(columns={'open':'session_open'})
    x=x.merge(first,on='session_date',how='left')
    x['market_return']=x['close']/x['session_open']-1.0
    return x[['timestamp','available_at','market_return']].sort_values('timestamp')
def build_market_context(decisions, bars, pit_intervals, benchmark=None, regime_context=None):
    """Build contemporaneous breadth/volatility from synchronized PIT members.
    Raw market data only. market_return requires an explicit benchmark.\n    market_regime is never inferred by W3A; a frozen provider/snapshot is required."""
    d=decisions.copy()
    d['decision_timestamp']=pd.to_datetime(d['decision_timestamp'],errors='coerce',utc=True)
    if 'session_date' not in d.columns:
        d['session_date']=d['decision_timestamp'].dt.tz_convert('Asia/Taipei').dt.date.astype(str)

    b=bars.copy()
    if b.empty:
        return pd.DataFrame(columns=['decision_id','market_regime','market_return','market_breadth','market_volatility']), {'schema_version':SCHEMA_VERSION,'status':'FAIL','reason':'NO_BARS','rows':0}
    b['timestamp']=pd.to_datetime(b['timestamp'],errors='coerce',utc=True)
    b=b[b['timestamp'].notna()].copy()
    b['session_date']=b['timestamp'].dt.tz_convert('Asia/Taipei').dt.date.astype(str)

    benchmark_series=None
    if benchmark is not None and not benchmark.empty:
        benchmark=benchmark.copy()
        benchmark['timestamp']=pd.to_datetime(benchmark['timestamp'],errors='coerce',utc=True)
        benchmark['market_return']=pd.to_numeric(benchmark['market_return'],errors='coerce')
        benchmark_series=benchmark.dropna(subset=['timestamp']).sort_values('timestamp')

    regime_lookup={}
    if regime_context is not None and not regime_context.empty:
        r=regime_context.copy()
        if "decision_id" in r.columns and "market_regime" in r.columns:
            regime_lookup=dict(zip(r["decision_id"].astype(str),r["market_regime"]))

    out=[]; detail=[]
    for ts,part in d.groupby('decision_timestamp',dropna=False):
        if pd.isna(ts):
            for _,row in part.iterrows(): out.append({'decision_id':row['decision_id']})
            continue
        session=str(part.iloc[0]['session_date'])
        members=universe_as_of(pit_intervals,session)
        member_syms={str(x['symbol']) for x in members}
        avail=b[(b['session_date']==session)&(b['symbol'].astype(str).isin(member_syms))&(b['timestamp']<=ts)]
        latest=avail.sort_values('timestamp').groupby('symbol',as_index=False).tail(1)
        first=avail.sort_values('timestamp').groupby('symbol',as_index=False).head(1)[['symbol','open']].rename(columns={'open':'session_open'})
        snap=latest.merge(first,on='symbol',how='left')
        snap['ret']=(snap['close']/snap['session_open']-1.0)
        valid=snap['ret'].dropna()
        breadth=float((valid>0).mean()) if len(valid) else None
        ew=float(valid.mean()) if len(valid) else None
        med=float(valid.median()) if len(valid) else None
        vol=float(valid.std(ddof=0)) if len(valid) else None
        observed=int(snap['symbol'].nunique())
        expected=len(member_syms)
        coverage=observed/expected if expected else 0.0
        market_return=None
        if benchmark_series is not None:
            z=benchmark_series[benchmark_series['timestamp']<=ts]
            if not z.empty: market_return=float(z.iloc[-1]['market_return'])
        record={
            'market_return':market_return,
            'market_breadth':breadth,'market_volatility':vol,
            'market_equal_weight_return':ew,'market_median_return':med,
            'market_member_expected':expected,'market_member_observed':observed,
            'market_member_coverage':coverage,
            'market_context_source':'PIT_SYNCHRONIZED_5M_CROSS_SECTION',
            'market_benchmark_source':'EXPLICIT' if market_return is not None else 'MISSING',
        }
        for _,row in part.iterrows():
            decision_id=str(row["decision_id"])
            item={
                "decision_id":row["decision_id"],
                "market_regime":regime_lookup.get(decision_id),
                "market_regime_source":"FROZEN_PROVIDER" if decision_id in regime_lookup else "MISSING",
                **record,
            }
            out.append(item)
            detail.append({"timestamp":ts.isoformat(),"session_date":session,**item})

    result=pd.DataFrame(out)
    cov=[x['market_member_coverage'] for x in detail]
    benchmark_ok=bool(not result.empty and 'market_return' in result.columns and result['market_return'].notna().all())
    regime_ok=bool(not result.empty and 'market_regime' in result.columns and result['market_regime'].notna().all())
    report={
        'schema_version':SCHEMA_VERSION,'decision_rows':int(len(result)),'timestamps':len(detail),
        'mean_member_coverage':round(sum(cov)/len(cov),6) if cov else 0.0,
        'min_member_coverage':round(min(cov),6) if cov else 0.0,
        'benchmark_available':benchmark_ok,
        'frozen_regime_available':regime_ok,
        'status':'PASS' if cov and min(cov)>=0.95 and benchmark_ok and regime_ok else 'BLOCKED',
        'governance':{
            'equal_weight_return_not_substituted_for_market_return':True,
            'market_regime_not_inferred_by_w3a':True,
            'pit_membership_required':True,'future_bars_allowed':False,
            'only_completed_5m_bars_used':True,
        },
    }
    return result,report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--decisions',required=True)
    ap.add_argument('--history-dir',required=True)
    ap.add_argument('--pit-universe',required=True)
    ap.add_argument('--benchmark')
    ap.add_argument('--regime-context')
    ap.add_argument('--out-dir',default='research_output/intraday_market_context')
    args=ap.parse_args()
    decisions=pd.read_csv(args.decisions)
    bars=load_history_dir(args.history_dir)
    obj=json.loads(Path(args.pit_universe).read_text(encoding='utf-8'))
    intervals=obj if isinstance(obj,list) else obj.get('intervals',[])
    benchmark=(benchmark_returns_from_fugle_json(args.benchmark) if args.benchmark and str(args.benchmark).lower().endswith('.json') else (pd.read_csv(args.benchmark) if args.benchmark else None))
    regime=pd.read_csv(args.regime_context) if args.regime_context else None
    frame,report=build_market_context(decisions,bars,intervals,benchmark,regime)
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    frame.to_csv(out/'market_context.csv',index=False)
    (out/'market_context_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()