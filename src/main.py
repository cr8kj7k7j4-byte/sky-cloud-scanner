from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import json
from .config import TOP_N,DEEP_DIVE_N,STRICT_OFFICIAL_MODE,ALLOW_MIS_OTC_FALLBACK
from .official import load_official_universe,fetch_mis_quotes
from .fugle import get_ticker,get_quote,get_candles,snapshot_quotes
from .sky_rules import first_gate,score_for_ranking,enrich
from .notifier import send_telegram

TZ=ZoneInfo("Asia/Taipei"); OUT=Path("output")

def _fugle_fallback_rows(universe):
    # Only used if snapshot API is available on the user's Fugle plan.
    allowed={x["symbol"]:x for x in universe}
    rows=[]; warnings=[]
    for market in ("TSE","OTC"):
        try:
            p=snapshot_quotes(market)
            for q in p.get("data",[]):
                code=str(q.get("symbol","")); m=allowed.get(code)
                if not m: continue
                last=q.get("lastPrice",q.get("closePrice")); prev=(last-q.get("change")) if last is not None and q.get("change") is not None else None
                if last is None or not prev: continue
                rows.append({**m,"last":float(last),"previous_close":float(prev),"change_pct":float(q.get("changePercent") or 0),
                             "volume":int(q.get("tradeVolume") or 0),"trade_value":float(q.get("tradeValue") or 0),
                             "high":q.get("highPrice"),"low":q.get("lowPrice"),"open":q.get("openPrice"),
                             "bid":None,"ask":None,"quote_time":str(p.get("time","")),"quote_source":"Fugle snapshot fallback"})
        except Exception as e: warnings.append(f"Fugle snapshot {market} unavailable: {type(e).__name__}: {e}")
    return rows,warnings

def run():
    now=datetime.now(TZ); OUT.mkdir(exist_ok=True)
    st={"run_time":now.isoformat(),"full_market_scan":False,"strict_official_mode":STRICT_OFFICIAL_MODE,"warnings":[],"source_health":{},"top100":[],"deep":[]}
    try:
        universe,ust=load_official_universe(); st["source_health"]["official_universe"]=ust; st["universe_count"]=len(universe)
        rows,miswarn=fetch_mis_quotes(universe); st["warnings"].extend(miswarn); st["mis_quote_count"]=len(rows)
        twse_rows=[x for x in rows if x["exchange"]=="TWSE"]; otc_rows=[x for x in rows if x["exchange"]=="TPEx"]
        official_universe_ok=ust["twse"]>=500 and ust["tpex"]>=400
        # TWSE MIS is official TWSE real-time. For OTC it is fallback only, not TPEx-official intraday.
        twse_intraday_ok=len(twse_rows)>=400
        tpex_official_intraday_ok=False
        st["source_health"]["twse_intraday"]={"ok":twse_intraday_ok,"source":"TWSE MIS","count":len(twse_rows)}
        st["source_health"]["tpex_intraday"]={"ok":False,"source":"TPEx official public intraday full-market feed not verified in this build","count":0}
        if STRICT_OFFICIAL_MODE:
            st["full_market_scan"]=bool(official_universe_ok and twse_intraday_ok and tpex_official_intraday_ok)
            if not st["full_market_scan"]: st["warnings"].append("未完成全市場掃描：TPEx 官方公開免費來源未能驗證完整盤中全市場即時排行/快照。")
        else:
            st["full_market_scan"]=bool(official_universe_ok and len(rows)>=700)
        # Operational fallback: use MIS OTC to avoid an empty report, but cap classification at A.
        working_rows=rows if ALLOW_MIS_OTC_FALLBACK else twse_rows
        if len(working_rows)<300:
            fb,fw=_fugle_fallback_rows(universe); st["warnings"].extend(fw)
            if len(fb)>len(working_rows): working_rows=fb
        passed=[]
        for r in working_rows:
            ok,reasons=first_gate(r); r["gate_reasons"]=reasons
            if ok:
                r["rank_score"]=score_for_ranking(r); passed.append(r)
        passed.sort(key=lambda x:x["rank_score"],reverse=True)
        top=passed[:TOP_N]; st["top100"]=top
        deep=[]
        for row in top[:DEEP_DIVE_N]:
            try:
                item=enrich(row,get_ticker(row["symbol"]),get_quote(row["symbol"]),get_candles(row["symbol"],"5"))
                item["classification_cap"]="A" if not st["full_market_scan"] else "A+ eligible only after all gates"
                deep.append(item)
            except Exception as e:
                item=dict(row); item["flags"]=[f"Fugle深查失敗:{type(e).__name__}"]; item["classification_cap"]="A"; deep.append(item)
        st["deep"]=deep
        lines=[f"Sky Cloud Scanner v0.3｜{now:%Y-%m-%d %H:%M}",f"官方母池 TWSE {ust['twse']}｜TPEx {ust['tpex']}｜MIS有效報價 {len(rows)}｜第一層通過 {len(passed)}"]
        if st["full_market_scan"]: lines.append("✅ 已完成嚴格定義的全市場資料鏈。")
        else: lines.append("⚠ 未完成全市場掃描；任何候選最高只列 A，不得宣告 A+。")
        lines.append("來源：TWSE官方母池＋TPEx官方母池；盤中上市=TWSE MIS；上櫃若使用 MIS 僅為操作備援，非 TPEx 官方盤中全市場驗證。")
        lines += ["","【候選深查】"]
        if not deep: lines.append("目前沒有完成深查的候選；不產生交易建議。")
        for i,x in enumerate(deep[:10],1):
            flags="、".join(x.get("flags",[])) or "待確認"
            lines.append(f'{i}. {x["symbol"]} {x.get("name","")} {x["last"]:.2f} ({x["change_pct"]:+.2f}%) 量{x.get("volume",0):,}｜{flags}｜上限:{x.get("classification_cap") }')
        lines += ["","注意：rank_score 僅用於候選排序，不是勝率、SSS 或 EES。","A+ 必須再通過 Market Gate→Sector/RS→MTF→SSS→Phase→Anti-Chase→Breakout Quality→Setup+Trigger→Devil’s Advocate→EES→RR Gate。"]
        msg="\n".join(lines)
        (OUT/"latest.txt").write_text(msg,encoding="utf-8")
        (OUT/"latest.json").write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
        send_telegram(msg)
    except Exception as e:
        err=f"Sky Cloud Scanner v0.3 執行失敗｜{now:%Y-%m-%d %H:%M}\n{type(e).__name__}: {e}\n不產生交易建議。"
        st["warnings"].append(err); (OUT/"latest.txt").write_text(err,encoding="utf-8"); (OUT/"latest.json").write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding="utf-8")
        print(err); raise
if __name__=="__main__": run()
