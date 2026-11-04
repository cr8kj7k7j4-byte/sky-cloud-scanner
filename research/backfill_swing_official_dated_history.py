"""Official dated whole-market daily OHLCV backfill with PIT alignment.

TWSE MI_INDEX and TPEx otc_quotes_no1430 accept date requests. The seemingly
similar TPEx daily_close_quotes endpoint returned the *latest* session when
queried for an old date and is intentionally excluded.

This produces unadjusted historical backfill only; it cannot by itself
establish corporate-action completeness or promote a Swing trade signal.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.http_utils import get_json
from src.trading_calendar import fetch_calendar, classify_date
from research.collect_swing_official_daily_delta import join_pit, value, SYMBOL

TWSE_URL="https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
TPEX_URL="https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php"


def _validated_market_table(payload: dict, *, market: str, session: date) -> list[dict]:
    if not isinstance(payload,dict):
        raise ValueError(f"{market} response is not JSON object")
    stat=str(payload.get("stat") or "").lower()
    if stat != "ok":
        raise ValueError(f"{market} date={session}: official stat={stat}")
    sent_date=str(payload.get("date") or "").strip().replace("/","")
    expected_twse=session.strftime("%Y%m%d")
    expected_tpex=f"{session.year-1911:03d}{session.month:02d}{session.day:02d}"
    expected=expected_twse if market=="TWSE" else expected_tpex
    if sent_date not in ({expected, expected_twse} if market=="TPEx" else {expected}):
        raise ValueError(f"{market} stale/wrong day: payload date={sent_date}, requested={expected}")

    required=("證券代號","開盤價","最高價","最低價","收盤價","成交股數") if market=="TWSE" else ("代號","開盤 ","最高 ","最低","收盤 ","成交股數  ")
    rows=[]
    candidates=0
    for tbl in payload.get("tables") or []:
        fields=[str(f).strip() for f in (tbl.get("fields") or [])]
        if not fields:
            continue
        normalized_required=[r.strip() for r in required]
        if not set(normalized_required).issubset(fields):
            continue
        idx={field:i for i,field in enumerate(fields)}
        for rec in tbl.get("data") or []:
            if not isinstance(rec,list) or len(rec)<len(fields)-2:
                continue
            sym=str(rec[idx["證券代號" if market=="TWSE" else "代號"]]).strip()
            if not SYMBOL.fullmatch(sym):
                continue
            candidates+=1
            def get(field):
                pos=idx.get(field)
                return value(rec[pos]) if pos is not None and pos<len(rec) else None
            if market=="TWSE":
                op,hi,lo,cl=get("開盤價"),get("最高價"),get("最低價"),get("收盤價")
                volume,turnover=get("成交股數"),get("成交金額")
            else:
                op,hi,lo,cl=get("開盤"),get("最高"),get("最低"),get("收盤")
                volume,turnover=get("成交股數"),get("成交金額(元)")
            if None in (op,hi,lo,cl,volume) or volume<0 or min(op,hi,lo,cl)<=0:
                continue
            if not (lo<=min(op,cl)<=max(op,cl)<=hi):
                continue
            rows.append({
                "symbol":sym,"exchange":market,"date":session.isoformat(),
                "open":op,"high":hi,"low":lo,"close":cl,
                "volume":volume,"turnover":turnover,
                "source":f"{market}_OFFICIAL_DATED_DAILY",
                "retrieved_at":datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
                "adjusted":False,"corporate_action_checked":False,
            })
    if len(rows)<(500 if market=="TWSE" else 400):
        raise ValueError(
            f"{market} {session} valid={len(rows)}, raw_codes={candidates}, "
            f"fields/schema or incomplete official session"
        )
    if len({x["symbol"] for x in rows}) != len(rows):
        raise ValueError(f"{market}: duplicate symbols on {session}")
    return rows


def _fetch_market(market: str, day: date) -> list[dict]:
    if market=="TWSE":
        return _validated_market_table(
            get_json(TWSE_URL,params={
                "date":day.strftime("%Y%m%d"),
                "type":"ALLBUT0999","response":"json",
            },timeout=30,retries=3),
            market=market,session=day
        )
    roc=f"{day.year-1911}/{day.month:02d}/{day.day:02d}"
    return _validated_market_table(
        get_json(TPEX_URL,params={"l":"zh-tw","d":roc,"se":"EW"},
                 timeout=30,retries=3),
        market=market,session=day
    )


def collect(start: date,end: date,pit: dict,out: Path,calendar: list[dict]) -> dict:
    if pit.get("historical_universe_gate_pass") is not True or (pit.get("interval_validation") or {}).get("valid") is not True:
        raise ValueError("canonical PIT authority is not PASS")
    out.mkdir(parents=True,exist_ok=True)
    sessions=[]
    closed=[]
    failed=[]
    day=start
    while day<=end:
        # Extraordinary market-wide typhoon closure. Not part of the annual
        # preannounced TWSE holiday schedule; TWSE and TPEx confirmed a
        # complete closure for 2026-10-23 on 2026-10-22.
        if day.isoformat()=="2026-10-23":
            closed.append({
                "date":day.isoformat(),
                "reason":"CLOSED_EXTRAORDINARY_TYPOON_BOTH_EXCHANGES",
                "evidence":"https://www.cna.com.tw/news/afe/202610220388.aspx",
            })
            day+=timedelta(days=1)
            continue
        cal=classify_date(day,calendar)
        if not cal["market_open"]:
            closed.append({"date":day.isoformat(),"reason":cal["status"]})
            day+=timedelta(days=1)
            continue
        try:
            raw=_fetch_market("TWSE",day)+_fetch_market("TPEx",day)
            matched,quarantine=join_pit(raw,pit["intervals"])
            if len(matched)<1400:
                raise ValueError(f"PIT matched only {len(matched)}")
            doc={
                "schema_version":"SKY_SWING_OFFICIAL_DATED_BACKFILL_1",
                "trading_date":day.isoformat(),
                "status":"RAW_PIT_DAILY_ONLY_CA_AUDIT_PENDING",
                "pit_matched":len(matched),
                "quarantined":quarantine,
                "rows":matched,
            }
            p=out/f"{day.isoformat()}.json"
            p.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
            sessions.append({
                "date":day.isoformat(),"matched":len(matched),
                "raw_source":"TWSE_MI_INDEX + TPEX_OTC_QUOTES_NO1430",
                "sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
            })
        except Exception as exc:
            failed.append({"date":day.isoformat(),"reason":f"{type(exc).__name__}:{str(exc)[:260]}"})
        day+=timedelta(days=1)
    report={
        "schema_version":"SWING_OFFICIAL_DATED_BACKFILL_AUDIT_1",
        "range":[start.isoformat(),end.isoformat()],
        "verified_sessions":sessions,
        "closed_days":closed,
        "failed_open_days":failed,
        "status":"RAW_DATA_FETCHED_CA_PENDING" if sessions and not failed else "BLOCKED_MISSING_OFFICIAL_SESSION",
        "production_eligible":False,
        "corporate_action_ledger_complete":False,
        "note":"Do not feed to V1.1 live signals until all open sessions + PIT corporate actions are validated.",
    }
    (out/"backfill_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start",required=True)
    ap.add_argument("--end",required=True)
    ap.add_argument("--pit-json",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    pit=json.loads(Path(args.pit_json).read_text(encoding="utf-8"))
    calendar=fetch_calendar()
    out=collect(date.fromisoformat(args.start),date.fromisoformat(args.end),pit,Path(args.out),calendar)
    print(json.dumps(out,ensure_ascii=False))
    if out["status"]=="BLOCKED_MISSING_OFFICIAL_SESSION":
        raise SystemExit(2)


if __name__=="__main__":
    main()
