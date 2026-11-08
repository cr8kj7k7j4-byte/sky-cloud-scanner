"""Strict official market session ledger for MCR markout causality.

Missing weekdays are *unknown* until independently verified as closures, never
assumed holidays or normal trading days. A stock missing on an observed exchange
session is not shifted to its next available quoted date.
"""
from __future__ import annotations
from datetime import date,datetime,timedelta
from collections import Counter

MARKETS={"TWSE":"TWSE_OFFICIAL_DAILY","TPEx":"TPEX_OFFICIAL_DAILY"}

def _session(s):
    return date.fromisoformat(s)

def build_calendar(snapshots, *, confirmed_closed_dates=()):
    if not isinstance(snapshots,list):raise ValueError("INVALID_SNAPSHOT_LIST")
    closed=set()
    for d in confirmed_closed_dates:
        closed.add(_session(d))
    calendars={m:[] for m in MARKETS}
    seen=set()
    for snapshot in snapshots:
        if (snapshot.get("schema")!="MCR_OFFICIAL_EOD_PRICES_V1" or
            snapshot.get("execution_authorized") is not False or
            snapshot.get("historical_backfill") is not False or
            snapshot.get("mode")!="RESEARCH_REFERENCE_ONLY"):
            raise ValueError("INVALID_OFFICIAL_SNAPSHOT")
        day=_session(snapshot["session"])
        if day in seen:raise ValueError("DUPLICATE_MARKET_SESSION")
        seen.add(day)
        stamp=datetime.fromisoformat(snapshot["recorded_at"])
        if stamp.tzinfo is None or stamp.date()<day:
            raise ValueError("INVALID_CAPTURE_TIME")
        rows=snapshot.get("rows")
        if not isinstance(rows,list) or snapshot.get("total")!=len(rows):
            raise ValueError("TRUNCATED_OFFICIAL_SNAPSHOT")
        counts=Counter()
        codes=set()
        for row in rows:
            m=row.get("exchange")
            if m not in MARKETS or row.get("source")!=MARKETS[m] or row.get("session")!=snapshot["session"]:
                raise ValueError("MIXED_OFFICIAL_SESSION")
            if row.get("adjusted") is not False:raise ValueError("UNSUPPORTED_ADJUSTED_PRICE")
            captured=datetime.fromisoformat(row["captured_at"])
            if captured.tzinfo is None or captured.date()<day:
                raise ValueError("INVALID_ROW_CAPTURE_TIME")
            close=row.get("close")
            if type(close) not in (float,int) or not 0<float(close)<100000:
                raise ValueError("BAD_OFFICIAL_CLOSE")
            key=(m,row["symbol"])
            if key in codes:raise ValueError("DUPLICATE_MARKET_SYMBOL")
            codes.add(key)
            counts[m]+=1
        if set(counts)!=set(MARKETS) or dict(counts)!=snapshot.get("market_counts"):
            raise ValueError("MISSING_EXCHANGE_SOURCE")
        for m in MARKETS:calendars[m].append(day.isoformat())
    missing_weekdays=[]
    days=sorted(seen)
    for a,b in zip(days,days[1:]):
        x=a+timedelta(days=1)
        while x<b:
            if x.weekday()<5 and x not in closed:
                missing_weekdays.append(x.isoformat())
            x+=timedelta(days=1)
    return {
        "schema":"MCR_SESSION_CALENDAR_V1",
        "source":"VERIFIED_DUAL_MARKET_EOD_SNAPSHOTS",
        "exchange_sessions":{m:sorted(v) for m,v in calendars.items()},
        "unverified_weekday_gaps":sorted(set(missing_weekdays)),
        "verified_nontrading_days":sorted(d.isoformat() for d in closed),
        "coverage_days":len(days),
        "complete_for_forward_markouts":len(missing_weekdays)==0,
        "note":"Weekdays missing between snapshots are unknown, NOT automatically holidays."
    }
