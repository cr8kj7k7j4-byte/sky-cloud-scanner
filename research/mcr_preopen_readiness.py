"""Read-only MCR preopen source readiness. Never certifies live trades or trades."""
from __future__ import annotations
import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.fugle import snapshot_quotes

TZ = ZoneInfo("Asia/Taipei")
OUT = Path("output/mcr_preopen_readiness.json")


def run(probe=snapshot_quotes, attempts=3, sleep=time.sleep):
    now = datetime.now(TZ)
    receipt = {
        "schema": "SKY_MCR_PREOPEN_READINESS_V1",
        "checked_at_tpe": now.isoformat(),
        "execution_scope": "READ_ONLY_SOURCE_SMOKE",
        "source": "Fugle paid bulk snapshot TSE + OTC",
        "markets": {},
        "trade_eligible": False,
        "is_live_trade_certified": False,
        "maintenance_below_130_verified": False,
        "action": "禁止交易",
    }
    for market in ("TSE", "OTC"):
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                raw = probe(market)
                rows = raw.get("data") if isinstance(raw, dict) else None
                if not isinstance(rows, list) or not rows:
                    raise ValueError("EMPTY_OR_INVALID_SNAPSHOT")
                receipt["markets"][market] = {
                    "status": "API_RESPONDED",
                    "source_date": str(raw.get("date") or ""),
                    "snapshot_rows": len(rows),
                    "rows_with_last_trade_time": sum(
                        isinstance(r.get("lastTrade"), dict)
                        and bool(r["lastTrade"].get("time"))
                        for r in rows if isinstance(r, dict)
                    ),
                    "attempt": attempt,
                    "notice": "Snapshot is not a confirmed fresh executed trade.",
                }
                break
            except Exception as exc:
                # Do not expose keys, request URLs, or exception messages.
                last_error = type(exc).__name__
                if attempt < attempts:
                    sleep(5 * attempt)
        else:
            receipt["markets"][market] = {
                "status": "API_UNAVAILABLE",
                "error_type": last_error,
                "attempts": attempts,
            }
    receipt["source_reachable"] = all(
        receipt["markets"].get(m, {}).get("status") == "API_RESPONDED"
        for m in ("TSE", "OTC")
    )
    receipt["result"] = (
        "PREOPEN_SOURCE_REACHABLE_NOT_LIVE_VERIFIED"
        if receipt["source_reachable"] else "DATA_BLOCKED"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    report = run()
    print(json.dumps(report, ensure_ascii=False))
    if not report["source_reachable"]:
        raise SystemExit("MCR_PREOPEN_SOURCE_UNAVAILABLE")


if __name__ == "__main__":
    main()
