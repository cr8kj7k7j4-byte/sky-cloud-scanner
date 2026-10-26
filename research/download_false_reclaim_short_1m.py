from __future__ import annotations

import argparse, json, time
from collections import defaultdict
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path

from research.download_pit_universe_intraday import MIN_INTERVAL, _request_chunk, chunks, load_pit_union

TAIPEI=timezone(timedelta(hours=8))
DECISION_TIMES=[f"09:{m:02d}" for m in range(1,16)]
KEEP_END=dtime(9,14)

def num(v):
    try:return float(v)
    except Exception:return None

def parse_ts(v):
    dt=datetime.fromisoformat(str(v).replace("Z","+00:00"))
    if dt.tzinfo is None:dt=dt.replace(tzinfo=TAIPEI)
    return dt.astimezone(TAIPEI)

def tick_size(price):
    if price < 10:return 0.01
    if price < 50:return 0.05
    if price < 100:return 0.10
    if price < 500:return 0.50
    if price < 1000:return 1.00
    return 5.00

def prev_tick(price):
    eps=1e-12
    p=float(price)
    # step is determined just below current boundary
    step=tick_size(max(p-eps,0))
    return round(p-step,2)

def fourth_tick_below(price):
    x=float(price)
    for _ in range(4):x=prev_tick(x)
    return x

def compact_chunk(data):
    by_day=defaultdict(list)
    for raw in data:
        try:ts=parse_ts(raw.get("date"))
        except Exception:continue
        by_day[ts.date().isoformat()].append((ts,raw))
    out=[]
    for day,items in sorted(by_day.items()):
        items.sort(key=lambda x:x[0])
        if not items:continue
        session_open=num(items[0][1].get("open"));session_close=num(items[-1][1].get("close"))
        if session_open is None or session_close is None:continue
        bm={ts.strftime("%H:%M"):(ts,b) for ts,b in items}
        bars={}
        for ts,b in items:
            if ts.time()<=KEEP_END:
                bars[ts.strftime("%H:%M")]={"open":num(b.get("open")),"high":num(b.get("high")),"low":num(b.get("low")),"close":num(b.get("close")),"volume":num(b.get("volume")) or 0.0}
        outcomes={}
        min_entry=fourth_tick_below(session_open)
        for hhmm in DECISION_TIMES:
            entry_row=bm.get(hhmm)
            if entry_row is None:continue
            entry=num(entry_row[1].get("open"))
            if entry is None or entry<=0:continue
            entry_ok=bool(min_entry<=entry<session_open)
            row={"raw_entry_open":entry,"entry":entry if entry_ok else None,"min_entry_4tick":min_entry,
                 "entry_status":"SHORT_ENTRY_4TICK_ZONE" if entry_ok else ("NO_SHORT_BELOW_OPEN" if entry>=session_open else "MISSED_4TICK_SHORT_NO_CHASE")}
            if not entry_ok:
                outcomes[hhmm]=row;continue
            entry_dt=entry_row[0]
            future=[(ts,b) for ts,b in items if ts>=entry_dt]
            stop_ts=None;stop_fill=None
            for ts,b in future:
                hi=num(b.get("high"));op=num(b.get("open"))
                if hi is not None and hi>session_open:
                    stop_ts=ts;stop_fill=max(session_open,op) if op is not None else session_open;break
            row["open_stop_triggered"]=stop_ts is not None
            row["open_stop_time"]=stop_ts.strftime("%H:%M") if stop_ts else None
            row["open_stop_fill"]=stop_fill
            for horizon in (30,60):
                exit_dt=entry_dt+timedelta(minutes=horizon-1)
                exit_row=bm.get(exit_dt.strftime("%H:%M"))
                window=[(ts,b) for ts,b in future if ts<=exit_dt]
                if exit_row is not None and window:
                    highs=[num(b.get("high")) for _,b in window];highs=[x for x in highs if x is not None]
                    lows=[num(b.get("low")) for _,b in window];lows=[x for x in lows if x is not None]
                    row[f"exit_{horizon}m"]=num(exit_row[1].get("close"))
                    row[f"high_{horizon}m"]=max(highs) if highs else None
                    row[f"low_{horizon}m"]=min(lows) if lows else None
                    row[f"stop_aware_exit_{horizon}m"]=stop_fill if stop_ts is not None and stop_ts<=exit_dt else row[f"exit_{horizon}m"]
            highs=[num(b.get("high")) for _,b in future];highs=[x for x in highs if x is not None]
            lows=[num(b.get("low")) for _,b in future];lows=[x for x in lows if x is not None]
            row["session_close"]=session_close
            row["high_to_close"]=max(highs) if highs else None
            row["low_to_close"]=min(lows) if lows else None
            outcomes[hhmm]=row
        out.append({"date":day,"session_open":session_open,"session_close":session_close,"bars":bars,"short_outcomes":outcomes})
    return out

def download_symbol(item,start,end,out_dir):
    all_days={};raw=0
    for a,b in chunks(start,end):
        t0=time.time();data=_request_chunk(item["symbol"],a,b,timeframe="1");raw+=len(data)
        for d in compact_chunk(data):all_days[d["date"]]=d
        elapsed=time.time()-t0
        if elapsed<MIN_INTERVAL:time.sleep(MIN_INTERVAL-elapsed)
    d=out_dir/item["exchange"];d.mkdir(parents=True,exist_ok=True)
    payload={**item,"schema_version":"FALSE_RECLAIM_SHORT_1M_COMPACT_V1_0","timeframe":"1","from":start.isoformat(),"to":end.isoformat(),"days":[all_days[k] for k in sorted(all_days)]}
    (d/f'{item["symbol"]}_false_reclaim_short_1m.json').write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
    return {"symbol":item["symbol"],"exchange":item["exchange"],"ok":True,"raw_bars":raw,"days":len(all_days)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pit-intervals",required=True);ap.add_argument("--from-date",required=True);ap.add_argument("--to-date",required=True)
    ap.add_argument("--out",required=True);ap.add_argument("--shard-count",type=int,default=1);ap.add_argument("--shard-index",type=int,default=0)
    a=ap.parse_args();start=date.fromisoformat(a.from_date);end=date.fromisoformat(a.to_date)
    items=load_pit_union(a.pit_intervals,a.from_date,a.to_date)
    items=[x for i,x in enumerate(items) if i%a.shard_count==a.shard_index]
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);summary=[]
    for i,item in enumerate(items,1):
        try:
            lo=max(start,date.fromisoformat(item.get("history_required_from",start.isoformat())))
            hi=min(end,date.fromisoformat(item.get("history_required_to",end.isoformat())))
            r=download_symbol(item,lo,hi,out);summary.append(r);print(f"[{i}/{len(items)}] {item['symbol']} {r['days']} days",flush=True)
        except Exception as e:
            summary.append({"symbol":item.get("symbol"),"exchange":item.get("exchange"),"ok":False,"error":f"{type(e).__name__}: {e}"})
    rep={"schema_version":"FALSE_RECLAIM_SHORT_DOWNLOAD_SUMMARY_V1_0","from_date":a.from_date,"to_date":a.to_date,"shard_count":a.shard_count,"shard_index":a.shard_index,"expected_symbols":len(items),"successful_symbols":sum(bool(x.get("ok")) for x in summary),"raw_bars":sum(int(x.get("raw_bars") or 0) for x in summary),"summary":summary}
    (out/"download_summary.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in rep.items() if k!="summary"},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
