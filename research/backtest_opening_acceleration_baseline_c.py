from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

PRIMARY_COST = 0.0045
STRESS_COST = 0.0065
PRICE_CAP = 100.0
DAY_RETURN_CAP = 0.095
MINUTES = [f"09:{m:02d}" for m in range(0, 16)]
TRADE_MINUTES = [f"09:{m:02d}" for m in range(1, 16)]
SCHEMA_VERSION = "OPENING_ACCELERATION_BASELINE_C_V1_0"


def n(v):
    try:
        return float(v)
    except Exception:
        return None


def split_label(day: str) -> str:
    if day <= "2024-12-31":
        return "DEVELOPMENT"
    if day <= "2025-12-31":
        return "VALIDATION"
    return "RESEARCH_TEST"


def half_label(day: str) -> str:
    y,m,_=day.split("-")
    return f"{y}-H{1 if int(m)<=6 else 2}"


def minute_index(hhmm: str) -> int:
    h,m=map(int,hhmm.split(":"))
    return h*60+m


def percentile_map(rows: list[dict], key: str) -> dict[str,float]:
    vals=[(float(r[key]),str(r["symbol"])) for r in rows if r.get(key) is not None]
    vals.sort()
    if not vals:
        return {}
    if len(vals)==1:
        return {vals[0][1]:1.0}
    out={}
    i=0
    while i<len(vals):
        j=i+1
        while j<len(vals) and vals[j][0]==vals[i][0]:
            j+=1
        pct=((i+j-1)/2)/(len(vals)-1)
        for k in range(i,j):
            out[vals[k][1]]=pct
        i=j
    return out


def build_snapshot_db(data_root: str, db_path: str) -> dict:
    conn=sqlite3.connect(db_path)
    conn.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    PRAGMA temp_store=FILE;
    CREATE TABLE snapshots(
      symbol TEXT,
      exchange TEXT,
      session_date TEXT,
      obs TEXT,
      price REAL,
      session_open REAL,
      prior_close REAL,
      day_return REAL,
      volume REAL,
      ret_1m REAL,
      ret_3m REAL,
      ret_5m REAL,
      ret_10m REAL,
      entry REAL,
      raw_entry_open REAL,
      max_entry_4tick REAL,
      entry_status TEXT,
      exit_30m REAL,
      exit_60m REAL,
      stop_aware_exit_30m REAL,
      stop_aware_exit_60m REAL,
      open_stop_fill REAL,
      open_stop_time TEXT,
      open_stop_triggered INTEGER,
      session_close REAL,
      high_30m REAL,
      low_30m REAL,
      high_60m REAL,
      low_60m REAL,
      high_to_close REAL,
      low_to_close REAL,
      split TEXT,
      half TEXT
    );
    """)
    files=sorted(Path(data_root).rglob("*_opening_1m.json"))
    rows=0
    symbols=set()
    parse_errors=[]

    for i,p in enumerate(files,1):
        try:
            x=json.loads(p.read_text(encoding="utf-8"))
            symbol=str(x.get("symbol") or "")
            exchange=str(x.get("exchange") or "")
            if x.get("schema_version") != "OPENING_ACCELERATION_1M_COMPACT_V1_1_4TICK_STOP":
                raise ValueError(f"ineligible compact schema: {x.get('schema_version')}")
            days=sorted(x.get("days") or [], key=lambda d:str(d.get("date") or ""))
            prior_close=None
            batch=[]
            for d in days:
                day=str(d.get("date") or "")
                session_open=n(d.get("session_open"))
                session_close=n(d.get("session_close"))
                bars=d.get("bars") or {}
                outcomes=d.get("outcomes") or {}
                if not day or prior_close is None or prior_close<=0:
                    if session_close and session_close>0:
                        prior_close=session_close
                    continue

                prices={}
                vols={}
                last_price=prior_close
                for obs in MINUTES:
                    b=bars.get(obs)
                    if b and n(b.get("close")) is not None:
                        last_price=n(b.get("close"))
                    prices[obs]=last_price
                    vols[obs]=n((b or {}).get("volume")) or 0.0

                for obs in TRADE_MINUTES:
                    decision_idx=MINUTES.index(obs)
                    feature_idx=decision_idx-1
                    if feature_idx<0:
                        continue
                    feature_label=MINUTES[feature_idx]
                    price=prices.get(feature_label)
                    if price is None or price<=0:
                        continue
                    dr=price/prior_close-1.0
                    if price>PRICE_CAP or dr>=DAY_RETURN_CAP:
                        continue
                    def ret(h):
                        if feature_idx-h<0:
                            return None
                        p0=prices.get(MINUTES[feature_idx-h])
                        return price/p0-1.0 if p0 and p0>0 else None
                    o=outcomes.get(obs) or {}
                    batch.append((
                        symbol,exchange,day,obs,price,session_open,prior_close,dr,vols.get(feature_label),
                        ret(1),ret(3),ret(5),ret(10),
                        n(o.get("entry")),n(o.get("raw_entry_open")),n(o.get("max_entry_4tick")),o.get("entry_status"),
                        n(o.get("exit_30m")),n(o.get("exit_60m")),
                        n(o.get("stop_aware_exit_30m")),n(o.get("stop_aware_exit_60m")),
                        n(o.get("open_stop_fill")),o.get("open_stop_time"),
                        1 if o.get("open_stop_triggered") else 0,
                        n(o.get("session_close")),
                        n(o.get("high_30m")),n(o.get("low_30m")),n(o.get("high_60m")),n(o.get("low_60m")),
                        n(o.get("high_to_close")),n(o.get("low_to_close")),
                        split_label(day),half_label(day)
                    ))
                if session_close and session_close>0:
                    prior_close=session_close
            if batch:
                conn.executemany("INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",batch)
                rows+=len(batch)
                symbols.add(symbol)
            if i%100==0:
                conn.commit()
                print(f"loaded {i}/{len(files)} files rows={rows}",flush=True)
        except Exception as exc:
            parse_errors.append({"file":str(p),"error":f"{type(exc).__name__}: {exc}"})
    conn.commit()
    conn.execute("CREATE INDEX idx_snap_day_obs ON snapshots(session_date,obs)")
    conn.execute("CREATE INDEX idx_snap_symbol_day_obs ON snapshots(symbol,session_date,obs)")
    conn.execute("""
    CREATE TABLE ranked AS
    SELECT *,
      ROW_NUMBER() OVER(
        PARTITION BY session_date,obs
        ORDER BY day_return DESC,symbol ASC
      ) AS gain_rank,
      COUNT(*) OVER(PARTITION BY session_date,obs) AS eligible_n
    FROM snapshots
    """)
    conn.execute("CREATE INDEX idx_rank_day_obs ON ranked(session_date,obs,gain_rank)")
    conn.execute("CREATE INDEX idx_rank_symbol_day_obs ON ranked(symbol,session_date,obs)")
    conn.commit()

    # Add causal rank lags and first Top100 entry minute.
    conn.execute("""
    CREATE TABLE features AS
    SELECT c.*,
      r1.gain_rank AS rank_1m_ago,
      r3.gain_rank AS rank_3m_ago,
      r5.gain_rank AS rank_5m_ago,
      r10.gain_rank AS rank_10m_ago,
      v1.volume AS vol_1m_ago,
      v2.volume AS vol_2m_ago,
      v3.volume AS vol_3m_ago
    FROM ranked c
    LEFT JOIN ranked r1 ON r1.symbol=c.symbol AND r1.session_date=c.session_date
      AND (CAST(substr(r1.obs,1,2) AS INT)*60+CAST(substr(r1.obs,4,2) AS INT))
        =(CAST(substr(c.obs,1,2) AS INT)*60+CAST(substr(c.obs,4,2) AS INT))-1
    LEFT JOIN ranked r3 ON r3.symbol=c.symbol AND r3.session_date=c.session_date
      AND (CAST(substr(r3.obs,1,2) AS INT)*60+CAST(substr(r3.obs,4,2) AS INT))
        =(CAST(substr(c.obs,1,2) AS INT)*60+CAST(substr(c.obs,4,2) AS INT))-3
    LEFT JOIN ranked r5 ON r5.symbol=c.symbol AND r5.session_date=c.session_date
      AND (CAST(substr(r5.obs,1,2) AS INT)*60+CAST(substr(r5.obs,4,2) AS INT))
        =(CAST(substr(c.obs,1,2) AS INT)*60+CAST(substr(c.obs,4,2) AS INT))-5
    LEFT JOIN ranked r10 ON r10.symbol=c.symbol AND r10.session_date=c.session_date
      AND (CAST(substr(r10.obs,1,2) AS INT)*60+CAST(substr(r10.obs,4,2) AS INT))
        =(CAST(substr(c.obs,1,2) AS INT)*60+CAST(substr(c.obs,4,2) AS INT))-10
    LEFT JOIN ranked v1 ON v1.symbol=c.symbol AND v1.session_date=c.session_date
      AND (CAST(substr(v1.obs,1,2) AS INT)*60+CAST(substr(v1.obs,4,2) AS INT))
        =(CAST(substr(c.obs,1,2) AS INT)*60+CAST(substr(c.obs,4,2) AS INT))-1
    LEFT JOIN ranked v2 ON v2.symbol=c.symbol AND v2.session_date=c.session_date
      AND (CAST(substr(v2.obs,1,2) AS INT)*60+CAST(substr(v2.obs,4,2) AS INT))
        =(CAST(substr(c.obs,1,2) AS INT)*60+CAST(substr(c.obs,4,2) AS INT))-2
    LEFT JOIN ranked v3 ON v3.symbol=c.symbol AND v3.session_date=c.session_date
      AND (CAST(substr(v3.obs,1,2) AS INT)*60+CAST(substr(v3.obs,4,2) AS INT))
        =(CAST(substr(c.obs,1,2) AS INT)*60+CAST(substr(c.obs,4,2) AS INT))-3
    """)
    conn.execute("CREATE INDEX idx_feat_day_obs_rank ON features(session_date,obs,gain_rank)")
    conn.execute("CREATE INDEX idx_feat_symbol_day_obs ON features(symbol,session_date,obs)")
    conn.commit()
    conn.close()
    return {"files":len(files),"symbols":len(symbols),"rows":rows,"parse_errors":parse_errors[:100]}


def enrich_rows(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory=sqlite3.Row
    cur=conn.execute("SELECT * FROM features ORDER BY session_date,obs,gain_rank,symbol")
    grouped=defaultdict(list)
    for row in cur:
        d=dict(row)
        grouped[(d["session_date"],d["symbol"])].append(d)

    out=[]
    for (_day,_symbol), arr in grouped.items():
        first_top=None
        for d in sorted(arr,key=lambda x:x["obs"]):
            if d["gain_rank"]<=100 and first_top is None:
                first_top=d["obs"]
            d["first_top100_obs"]=first_top
            d["minutes_since_top100_entry"]=(
                minute_index(d["obs"])-minute_index(first_top)
                if first_top is not None else None
            )
            d["rank_velocity_1m"]=(d["rank_1m_ago"]-d["gain_rank"]) if d.get("rank_1m_ago") is not None else None
            d["rank_velocity_3m"]=(d["rank_3m_ago"]-d["gain_rank"])/3.0 if d.get("rank_3m_ago") is not None else None
            d["rank_velocity_5m"]=(d["rank_5m_ago"]-d["gain_rank"])/5.0 if d.get("rank_5m_ago") is not None else None
            d["rank_velocity_10m"]=(d["rank_10m_ago"]-d["gain_rank"])/10.0 if d.get("rank_10m_ago") is not None else None
            prev3=[d.get("vol_1m_ago"),d.get("vol_2m_ago"),d.get("vol_3m_ago")]
            if all(v is not None for v in prev3) and sum(prev3)>0:
                d["volume_acceleration_1v3"]=d["volume"]/(sum(prev3)/3.0)-1.0
            else:
                d["volume_acceleration_1v3"]=None
            out.append(d)
    return out


def select_variant(rows: list[dict], *, remove_open=False, remove_fresh=False,
                   remove_rank=False, remove_return=False, remove_volume=False) -> list[dict]:
    by_group=defaultdict(list)
    for d0 in rows:
        d=dict(d0)
        if d["gain_rank"]>100:
            continue
        if d.get("entry_status") != "ENTRY_4TICK_ZONE" or not d.get("entry"):
            continue
        if not remove_open:
            if d.get("session_open") is None or d["price"]<=d["session_open"]:
                continue
        if not remove_fresh:
            m=d.get("minutes_since_top100_entry")
            if m is None or m<0 or m>3:
                continue
        if not remove_rank:
            if d.get("rank_velocity_1m") is None or d["rank_velocity_1m"]<=0:
                continue
        if not remove_return:
            if d.get("ret_1m") is None or d["ret_1m"]<=0:
                continue
        if not remove_volume:
            if d.get("volume_acceleration_1v3") is None or d["volume_acceleration_1v3"]<=0:
                continue
        by_group[(d["session_date"],d["obs"])].append(d)

    picked=[]
    seen_by_day=defaultdict(set)
    for key in sorted(by_group):
        cands=by_group[key]
        score_keys=[]
        if not remove_rank:
            score_keys += ["rank_velocity_1m","rank_velocity_3m"]
        if not remove_return:
            score_keys += ["ret_1m","ret_3m"]
        if not remove_volume:
            score_keys += ["volume_acceleration_1v3"]
        pct={k:percentile_map(cands,k) for k in score_keys}
        for d in cands:
            vals=[pct[k][d["symbol"]] for k in score_keys if d.get(k) is not None and d["symbol"] in pct[k]]
            d["opening_acceleration_score"]=sum(vals)/len(vals) if vals else 0.0
        cands.sort(key=lambda x:(-x["opening_acceleration_score"],x["gain_rank"],x["symbol"]))
        for d in cands:
            if len([x for x in picked if x["session_date"]==key[0] and x["obs"]==key[1]])>=3:
                break
            if d["symbol"] in seen_by_day[d["session_date"]]:
                continue
            seen_by_day[d["session_date"]].add(d["symbol"])
            exit60=d.get("stop_aware_exit_60m") or d.get("exit_60m")
            exit30=d.get("stop_aware_exit_30m") or d.get("exit_30m")
            gross60=(exit60/d["entry"]-1.0) if d.get("entry") and exit60 else None
            gross30=(exit30/d["entry"]-1.0) if d.get("entry") and exit30 else None
            close_ret=(d["session_close"]/d["entry"]-1.0) if d.get("entry") and d.get("session_close") else None
            d["gross_30m"]=gross30
            d["gross_60m"]=gross60
            d["gross_close"]=close_ret
            d["net_60m_045"]=gross60-PRIMARY_COST if gross60 is not None else None
            d["net_60m_065"]=gross60-STRESS_COST if gross60 is not None else None
            d["mfe_60m"]=(d["high_60m"]/d["entry"]-1.0) if d.get("entry") and d.get("high_60m") else None
            d["mae_60m"]=(d["low_60m"]/d["entry"]-1.0) if d.get("entry") and d.get("low_60m") else None
            d["mfe_to_close"]=(d["high_to_close"]/d["entry"]-1.0) if d.get("entry") and d.get("high_to_close") else None
            d["mae_to_close"]=(d["low_to_close"]/d["entry"]-1.0) if d.get("entry") and d.get("low_to_close") else None
            d["hit_plus5"]=(d["mfe_to_close"] is not None and d["mfe_to_close"]>=0.05)
            d["open_stop_hit"]=bool(d.get("open_stop_triggered"))
            d["near_limit_proxy"]=(
                d.get("high_to_close") is not None and d.get("prior_close") and
                d["high_to_close"]/d["prior_close"]-1.0>=0.095
            )
            picked.append(d)
    return picked


def max_drawdown(trades: list[dict], field: str):
    by_day=defaultdict(list)
    for t in trades:
        if t.get(field) is not None:
            by_day[t["session_date"]].append(float(t[field]))
    if not by_day:
        return None
    eq=peak=1.0
    mdd=0.0
    for day in sorted(by_day):
        r=sum(by_day[day])/len(by_day[day])
        eq*=1+r
        peak=max(peak,eq)
        mdd=min(mdd,eq/peak-1)
    return mdd


def metrics(trades: list[dict], field: str) -> dict:
    vals=[float(t[field]) for t in trades if t.get(field) is not None]
    if not vals:
        return {"n":0}
    wins=[x for x in vals if x>0]
    losses=[x for x in vals if x<0]
    return {
        "n":len(vals),
        "expectancy":sum(vals)/len(vals),
        "pf":sum(wins)/abs(sum(losses)) if losses else None,
        "win_rate":len(wins)/len(vals),
        "avg_win":sum(wins)/len(wins) if wins else None,
        "avg_loss":sum(losses)/len(losses) if losses else None,
        "max_drawdown":max_drawdown(trades,field),
        "avg_mfe_60m":sum(t["mfe_60m"] for t in trades if t.get("mfe_60m") is not None)/max(1,sum(t.get("mfe_60m") is not None for t in trades)),
        "avg_mae_60m":sum(t["mae_60m"] for t in trades if t.get("mae_60m") is not None)/max(1,sum(t.get("mae_60m") is not None for t in trades)),
        "hit_plus5_rate":sum(bool(t.get("hit_plus5")) for t in trades)/len(trades),
        "near_limit_proxy_rate":sum(bool(t.get("near_limit_proxy")) for t in trades)/len(trades),
        "open_stop_rate":sum(bool(t.get("open_stop_hit")) for t in trades)/len(trades),
    }


def subgroup(trades,key,field):
    g=defaultdict(list)
    for t in trades:
        g[str(t.get(key))].append(t)
    return {k:metrics(v,field) for k,v in sorted(g.items())}


def concentration(trades):
    c=defaultdict(int)
    for t in trades:
        c[t["symbol"]]+=1
    total=len(trades)
    return {
        "unique_symbols":len(c),
        "max_symbol_share":max(c.values())/total if total else None,
        "top_symbols":sorted(
            ({"symbol":k,"n":v,"share":v/total} for k,v in c.items()),
            key=lambda x:(-x["n"],x["symbol"])
        )[:20] if total else []
    }


def adjudicate(primary,split,conc):
    if primary.get("n",0)<200:
        return "HOLD_INSUFFICIENT_SAMPLE"
    if primary.get("expectancy") is None or primary["expectancy"]<=0:
        return "REJECT_AFTER_COST_EXPECTANCY"
    if primary.get("pf") is None or primary["pf"]<=1:
        return "REJECT_AFTER_COST_PF"
    if (conc.get("max_symbol_share") or 0)>0.20:
        return "HOLD_CONCENTRATION_FAIL"
    for required in ("VALIDATION","RESEARCH_TEST"):
        m=split.get(required,{})
        if m.get("n",0)<50:
            return "HOLD_SPLIT_SAMPLE"
        if m.get("expectancy") is None or m["expectancy"]<=0 or (m.get("pf") or 0)<=1:
            return "HOLD_SPLIT_INSTABILITY"
    return "PROMOTE_CANDIDATE_TO_W4"


def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8");return
    keys=sorted({k for r in rows for k in r})
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=keys);w.writeheader();w.writerows(rows)


def run(data_root: str, out_dir: str, source_run_id: str|None=None):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    db=out/"opening_acceleration.sqlite"
    if db.exists(): db.unlink()
    build=build_snapshot_db(data_root,str(db))
    conn=sqlite3.connect(db)
    rows=enrich_rows(conn)
    conn.close()

    baseline=select_variant(rows)
    write_csv(out/"opening_acceleration_baseline_c_trades.csv",baseline)
    p045=metrics(baseline,"net_60m_045")
    p065=metrics(baseline,"net_60m_065")
    split=subgroup(baseline,"split","net_60m_045")
    half=subgroup(baseline,"half","net_60m_045")
    minute=subgroup(baseline,"obs","net_60m_045")
    exchange=subgroup(baseline,"exchange","net_60m_045")
    conc=concentration(baseline)

    ab_specs={
      "REMOVE_OPEN_GATE":{"remove_open":True},
      "REMOVE_FRESH_ENTRY":{"remove_fresh":True},
      "REMOVE_RANK_VELOCITY":{"remove_rank":True},
      "REMOVE_RETURN_ACCELERATION":{"remove_return":True},
      "REMOVE_VOLUME_ACCELERATION":{"remove_volume":True},
    }
    ablations={}
    for name,kw in ab_specs.items():
        ts=select_variant(rows,**kw)
        ablations[name]={
            "cost_045":metrics(ts,"net_60m_045"),
            "selected":len(ts),
        }

    decision=adjudicate(p045,split,conc)
    report={
        "schema_version":SCHEMA_VERSION,
        "preregistered_spec":"research/w5/OPENING_ACCELERATION_BASELINE_C_PREREGISTRATION_20261026.md",
        "source":{"opening_1m_workflow_run_id":source_run_id},
        "build":build,
        "baseline":{
            "selected":len(baseline),
            "gross_30m":metrics(baseline,"gross_30m"),
            "gross_60m":metrics(baseline,"gross_60m"),
            "gross_close":metrics(baseline,"gross_close"),
            "cost_045":p045,
            "cost_065":p065,
            "split_045":split,
            "half_045":half,
            "minute_045":minute,
            "exchange_045":exchange,
            "concentration":conc,
        },
        "ablations":ablations,
        "decision":decision,
        "governance":{
            "production_change":False,
            "baseline_a_b_retuned":False,
            "next_if_survives":"W4_SHADOW_PAPER_ONLY",
        }
    }
    (out/"opening_acceleration_baseline_c_report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    md=[
      "# Opening Acceleration Scanner — Baseline C Result","",
      f"- Decision: **{decision}**",
      f"- Selected: {len(baseline):,}",
      f"- 0.45% expectancy: {p045.get('expectancy')}",
      f"- 0.45% PF: {p045.get('pf')}",
      f"- 0.65% expectancy: {p065.get('expectancy')}",
      f"- 0.65% PF: {p065.get('pf')}","",
      "## 0.45% split","",json.dumps(split,ensure_ascii=False,indent=2),"",
      "## Ablations","",json.dumps(ablations,ensure_ascii=False,indent=2),"",
      "No Production change."
    ]
    (out/"opening_acceleration_baseline_c_report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",required=True)
    ap.add_argument("--out-dir",default="research_output/opening_acceleration_baseline_c")
    ap.add_argument("--source-run-id",default=None)
    args=ap.parse_args()
    result=run(args.data_root,args.out_dir,args.source_run_id)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
