from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SCHEMA_VERSION="EFFECTIVE_SECTOR_MAPPING_V1_0"


def _d(value):
    if value is None or pd.isna(value) or not str(value).strip():
        return None
    return date.fromisoformat(str(value)[:10])


def reconstruct_effective_mapping(
    current: pd.DataFrame,
    changes: pd.DataFrame,
    *,
    window_start: str="2023-01-01",
) -> tuple[pd.DataFrame,dict]:
    """
    Reconstruct historical sector intervals by walking official change events
    backward from a verified current snapshot.

    current columns:
      symbol, exchange, sector, source, source_as_of

    changes columns:
      symbol, exchange, effective_date, old_sector, new_sector,
      source_url, published_at

    Every change event must explicitly state old_sector and new_sector.
    Missing history is never guessed.
    """
    req_current={"symbol","exchange","sector"}
    req_changes={"symbol","exchange","effective_date","old_sector","new_sector"}
    if not req_current.issubset(current.columns):
        raise ValueError(f"current snapshot missing {sorted(req_current-set(current.columns))}")
    if not changes.empty and not req_changes.issubset(changes.columns):
        raise ValueError(f"change ledger missing {sorted(req_changes-set(changes.columns))}")

    start=_d(window_start)
    rows=[]; unresolved=[]

    current=current.copy()
    current["symbol"]=current["symbol"].astype(str)
    if not changes.empty:
        changes=changes.copy()
        changes["symbol"]=changes["symbol"].astype(str)

    keys=set(zip(current["exchange"].astype(str),current["symbol"]))
    if not changes.empty:
        keys |= set(zip(changes["exchange"].astype(str),changes["symbol"]))

    for exchange,symbol in sorted(keys):
        cur=current[
            (current["exchange"].astype(str)==exchange)
            & (current["symbol"]==symbol)
        ]
        ev=(
            changes[
                (changes["exchange"].astype(str)==exchange)
                & (changes["symbol"]==symbol)
            ].sort_values("effective_date")
            if not changes.empty else pd.DataFrame()
        )
        if cur.empty:
            unresolved.append({
                "exchange":exchange,"symbol":symbol,
                "reason":"NO_CURRENT_SECTOR_ANCHOR",
                "change_events":int(len(ev)),
            })
            continue
        if len(cur)>1:
            unresolved.append({
                "exchange":exchange,"symbol":symbol,
                "reason":"DUPLICATE_CURRENT_SECTOR_ANCHOR",
            })
            continue

        sector=str(cur.iloc[0]["sector"])
        cursor_end=None
        valid=True
        for _,e in ev.sort_values("effective_date",ascending=False).iterrows():
            eff=_d(e["effective_date"])
            new=str(e["new_sector"])
            old=str(e["old_sector"])
            if sector!=new:
                unresolved.append({
                    "exchange":exchange,"symbol":symbol,
                    "reason":"CHANGE_CHAIN_MISMATCH",
                    "effective_date":str(eff),
                    "expected_new_sector":sector,
                    "ledger_new_sector":new,
                })
                valid=False
                break

            interval_start=max(eff,start)
            if cursor_end is None or interval_start<=cursor_end:
                rows.append({
                    "symbol":symbol,"exchange":exchange,"sector":sector,
                    "effective_from":interval_start.isoformat(),
                    "effective_to":cursor_end.isoformat() if cursor_end else None,
                    "source_type":"CURRENT_ANCHOR_PLUS_OFFICIAL_CHANGE_LEDGER",
                    "source_url":e.get("source_url"),
                    "published_at":e.get("published_at"),
                })
            sector=old
            cursor_end=eff-timedelta(days=1)
            if cursor_end<start:
                break

        if not valid:
            continue
        if cursor_end is None or cursor_end>=start:
            rows.append({
                "symbol":symbol,"exchange":exchange,"sector":sector,
                "effective_from":start.isoformat(),
                "effective_to":cursor_end.isoformat() if cursor_end else None,
                "source_type":"BACKCAST_FROM_VERIFIED_CURRENT_ANCHOR",
                "source_url":cur.iloc[0].get("source"),
                "published_at":cur.iloc[0].get("source_as_of"),
            })

    out=pd.DataFrame(rows)
    if not out.empty:
        out=out.sort_values(["exchange","symbol","effective_from"]).reset_index(drop=True)

    report={
        "schema_version":SCHEMA_VERSION,
        "window_start":window_start,
        "current_anchors":int(len(current)),
        "change_events":int(len(changes)),
        "intervals":int(len(out)),
        "symbols_with_intervals":int(out["symbol"].nunique()) if not out.empty else 0,
        "unresolved_count":len(unresolved),
        "unresolved":unresolved[:500],
        "status":"PASS" if not unresolved else "WARN",
        "governance":{
            "current_only_backfill_without_change_ledger":False,
            "old_new_sector_required_for_each_change":True,
            "unknown_history_is_unresolved":True,
        },
    }
    return out,report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--current",required=True)
    ap.add_argument("--changes",required=True)
    ap.add_argument("--window-start",default="2023-01-01")
    ap.add_argument("--out-dir",default="research_output/effective_sector_mapping")
    args=ap.parse_args()

    current=pd.read_csv(args.current)
    changes=pd.read_csv(args.changes)
    mapping,report=reconstruct_effective_mapping(
        current,changes,window_start=args.window_start
    )
    out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
    mapping.to_csv(out/"effective_sector_mapping.csv",index=False)
    (out/"effective_sector_mapping_audit.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
