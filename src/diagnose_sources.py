from datetime import datetime
from zoneinfo import ZoneInfo
import json

from .official import load_official_universe, fetch_mis_quotes
from .fugle import get_tickers, get_quote, snapshot_quotes

def _probe(name, fn):
    try:
        payload = fn()
        data = payload.get("data", []) if isinstance(payload, dict) else []
        return {
            "ok": True,
            "status": "available",
            "count": len(data),
            "date": payload.get("date") if isinstance(payload, dict) else None,
            "time": payload.get("time") if isinstance(payload, dict) else None,
        }
    except PermissionError as e:
        return {
            "ok": False,
            "status": "plan_restricted",
            "error": str(e),
        }
    except Exception as e:
        return {
            "ok": False,
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
        }

def run():
    out = {"time": datetime.now(ZoneInfo("Asia/Taipei")).isoformat()}

    universe, st = load_official_universe()
    out["official_universe"] = st
    out["universe_count"] = len(universe)

    q, w = fetch_mis_quotes(universe[:120])
    out["mis_sample"] = {
        "requested": min(120, len(universe)),
        "returned": len(q),
        "warnings": w,
    }

    # Intraday APIs are the capabilities actually used for deep-dive.
    out["fugle_tickers_TSE"] = _probe(
        "fugle_tickers_TSE", lambda: get_tickers("TSE")
    )
    out["fugle_tickers_OTC"] = _probe(
        "fugle_tickers_OTC", lambda: get_tickers("OTC")
    )
    out["fugle_quote_2330"] = _probe(
        "fugle_quote_2330", lambda: get_quote("2330")
    )

    # Snapshot is diagnostic only. 403 is recorded as plan_restricted and is
    # not considered a scanner failure.
    out["fugle_snapshot_TSE"] = _probe(
        "fugle_snapshot_TSE", lambda: snapshot_quotes("TSE")
    )
    out["fugle_snapshot_OTC"] = _probe(
        "fugle_snapshot_OTC", lambda: snapshot_quotes("OTC")
    )

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run()
