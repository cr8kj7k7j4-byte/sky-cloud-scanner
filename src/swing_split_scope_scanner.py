"""Research-only split scope swing scanner.

Official TWSE/TPEx daily close cross section (D-close) supplies market breadth.
Only selected symbols receive Fugle intraday quotes. Never treat D-close
coverage as whole-market *live* quote coverage.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .official import COMMON, TWSE_UNIVERSE_URL, TPEX_UNIVERSE_URL, load_official_universe, _f
from .http_utils import get_json
from .fugle import get_quote
from .realtime_quote_evidence import fugle_executed_trade

TZ = ZoneInfo("Asia/Taipei")
TWSE_DAILY = TWSE_UNIVERSE_URL
TPEX_DAILY = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
TPEX_BACKUP = TPEX_UNIVERSE_URL
OUT = Path("output/swing_split_scope")


def _date(v):
    s = str(v or "").strip().replace("-", "").replace("/", "")
    if len(s) == 7 and s.isdigit():
        return f"{int(s[:3])+1911:04d}-{s[3:5]}-{s[5:7]}"
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    raise ValueError("missing or malformed official trading date")


def parse_daily_rows(rows, market):
    """Never infer a missing date or price; fail closed instead."""
    out = {}
    for r in rows if isinstance(rows, list) else []:
        symbol = str(r.get("Code") if market == "TWSE" else r.get("SecuritiesCompanyCode") or "").strip()
        if not COMMON.fullmatch(symbol):
            continue
        try:
            trade_date = _date(r.get("Date"))
        except (TypeError, ValueError):
            continue
        close = _f(r.get("ClosingPrice") if market == "TWSE" else r.get("Close"))
        shares = _f(r.get("TradeVolume") if market == "TWSE" else r.get("TradingShares"))
        turnover = _f(r.get("TradeValue") if market == "TWSE" else r.get("TransactionAmount"))
        change = _f(r.get("Change"))
        if close is None or close <= 0 or shares is None or shares <= 0 or turnover is None or turnover <= 0:
            continue
        if change is None or close-change <= 0:
            continue
        out[symbol] = {
            "symbol": symbol, "date": trade_date, "close": close,
            "previous_close": close-change, "change_pct": 100*change/(close-change),
            "volume_shares": shares, "volume_lots": shares/1000,
            "trade_value": turnover, "market": market,
            "source": "TWSE STOCK_DAY_ALL" if market == "TWSE" else "TPEx daily_close_quotes",
        }
    return out


def evaluate_daily_scope(universe, twse, tpex, now):
    by_symbol = {item["symbol"]: item for item in universe}
    wanted = {"TWSE": sum(x.get("exchange")=="TWSE" for x in universe),
              "TPEx": sum(x.get("exchange")=="TPEx" for x in universe)}
    a = {k:v for k,v in twse.items() if k in by_symbol and by_symbol[k].get("exchange")=="TWSE"}
    b = {k:v for k,v in tpex.items() if k in by_symbol and by_symbol[k].get("exchange")=="TPEx"}
    dates = {v["date"] for v in [*a.values(), *b.values()]}
    # Do not accidentally use a not-yet-finalized current-day close.
    current = now.date()
    date_ok = len(dates)==1
    signal_date = next(iter(dates)) if date_ok else None
    if signal_date:
        d = date.fromisoformat(signal_date)
        age=(current-d).days
        date_ok = 0 <= age <= 4 and not (age == 0 and now.hour < 14)
    coverage = round(100*(len(a)+len(b))/len(universe),2) if universe else 0.
    market_coverage = { "TWSE":round(100*len(a)/wanted["TWSE"],2) if wanted["TWSE"] else 0.,
                        "TPEx":round(100*len(b)/wanted["TPEx"],2) if wanted["TPEx"] else 0.}
    qualified = bool(date_ok and coverage>=80 and all(v>=70 for v in market_coverage.values()))
    return {
        "status":"PASS_DAILY_CROSS_SECTION" if qualified else "BLOCKED_DAILY_CROSS_SECTION",
        "daily_scope_qualified":qualified,
        "daily_cross_section_coverage_pct":coverage,
        "market_coverage_pct":market_coverage,
        "universe_count":len(universe),"daily_count":len(a)+len(b),
        "daily_twse_count":len(a),"daily_tpex_count":len(b),
        "signal_date":signal_date,"source_dates":sorted(dates),
        "records":list(a.values())+list(b.values()),
    }


def quote_time_freshness(q, now, max_age_seconds=900):
    """Return verified quote timestamp, or an explicit reason to withhold recency."""
    raw=q.get("lastUpdated")
    try:
        timestamp=float(raw)
        if timestamp > 10**14:
            timestamp/=1_000_000  # Fugle epoch microseconds
        elif timestamp > 10**11:
            timestamp/=1000  # milliseconds
        updated=datetime.fromtimestamp(timestamp, TZ)
        age=(now-updated).total_seconds()
        if -120<=age<=max_age_seconds:
            return updated.isoformat(), "FRESH"
        return updated.isoformat(), "STALE_OR_FUTURE_TIMESTAMP"
    except (TypeError, ValueError, OverflowError, OSError):
        return None, "MISSING_OR_INVALID_TIMESTAMP"


def run(deep_n=8):
    now=datetime.now(TZ)
    OUT.mkdir(parents=True,exist_ok=True)
    universe, health=load_official_universe()
    errors=[]
    try: tw=parse_daily_rows(get_json(TWSE_DAILY, timeout=12, retries=2), "TWSE")
    except Exception as e:
        tw={}
        errors.append(f"TWSE daily data: {type(e).__name__}")
    tp={}
    for label, url in (("daily_close", TPEX_DAILY), ("mainboard_quotes", TPEX_BACKUP)):
        if tp:
            break
        try:
            tp=parse_daily_rows(get_json(url, timeout=12, retries=2), "TPEx")
            if not tp:
                errors.append(f"TPEx {label}: returned no date-verified valid close rows")
        except Exception as e:
            errors.append(f"TPEx {label}: {type(e).__name__}")
    # TPEx backup is official end-of-day quotes, never a substitute for
    # intraday executed-price coverage. Missing dates remain missing.

    assessment=evaluate_daily_scope(universe,tw,tp,now)
    # Market-wide is historical D-close; a quote for one candidate does not
    # change daily coverage or certify a live whole-market scanner.
    eligible=[]
    if assessment["daily_scope_qualified"]:
        eligible=[r for r in assessment["records"]
                  if 0 < r["close"] < 100 and r["volume_lots"]>=500
                  and r["trade_value"]>=10_000_000 and -5<=r["change_pct"]<9]
    eligible.sort(key=lambda r:(r["change_pct"],r["trade_value"]),reverse=True)
    candidates=[]
    for row in eligible[:max(1,deep_n)]:
        candidate=dict(row)
        candidate.update({"live_quote_status":"UNVERIFIED",
            "current_price":None,"current_price_date":None,"current_price_source":None,
            "strategy_signal":False,"production_eligible":False,"action":"等待"})
        try:
            q=get_quote(row["symbol"])
            qdate=str(q.get("date") or "")
            # closePrice is not guaranteed to be the most recent executed trade.
            # Never promote it to a live last price if lastPrice is missing.
            last, trade_dt, evidence_status = fugle_executed_trade(
                q, now, max_age_seconds=900
            )
            # During market hours accept only a quote explicitly dated today.
            updated_at = trade_dt.isoformat() if trade_dt else None
            candidate["current_price_updated_at"]=updated_at
            if evidence_status == "FRESH_EXECUTED_TRADE" and last is not None:
                candidate.update({"current_price":last,"current_price_date":qdate,
                    "current_price_source":"Fugle single-symbol intraday",
                    "live_quote_status":"FRESH_DATE_AND_TIMESTAMP_VERIFIED"})
            else:
                candidate["live_quote_status"]=evidence_status
        except Exception as e:
            candidate["live_quote_status"]=f"UNAVAILABLE_{type(e).__name__}"
        candidates.append(candidate)

    report={
        "generated_at":now.isoformat(),
        "mode":"SWING_SPLIT_SCOPE_RESEARCH",
        "strategy_status":"RESEARCH_ONLY_NOT_PRODUCTION",
        "daily_scope_status":assessment["status"],
        "official_universe_health":health,
        "official_daily_coverage_pct":assessment["daily_cross_section_coverage_pct"],
        "official_daily_market_coverage_pct":assessment["market_coverage_pct"],
        "official_daily_count":assessment["daily_count"],
        "universe_count":assessment["universe_count"],
        "official_daily_signal_date":assessment["signal_date"],
        "official_source_dates":assessment["source_dates"],
        "live_quote_scope":"CANDIDATES_ONLY",
        "live_quote_requested":len(candidates),
        "live_quote_available":sum(x["current_price"] is not None for x in candidates),
        "live_quote_timestamp_verified":sum(x["live_quote_status"]=="FRESH_DATE_AND_TIMESTAMP_VERIFIED" for x in candidates),
        "live_whole_market_coverage_pct":None,
        "live_whole_market_certified":False,
        "strict_official_full_market_certified":False,
        "market_data_errors":errors,
        "candidates":candidates,
        "note":"官方每日收盤橫斷面 + 富果少數個股當日報價。非全市場盤中即時行情；非正式交易訊號。",
    }
    p=OUT/"latest.json"
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="candidates"},ensure_ascii=False,indent=2))
    if not assessment["daily_scope_qualified"]:
        raise SystemExit("BLOCKED: official daily cross section is stale, inconsistent, or incomplete")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--deep-n",type=int,default=8)
    run(parser.parse_args().deep_n)
