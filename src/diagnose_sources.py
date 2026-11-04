from datetime import datetime
from zoneinfo import ZoneInfo
import json

from .official import load_official_universe, fetch_mis_quotes
from .fugle import get_tickers, get_quote, snapshot_quotes
from .realtime_quote_evidence import fugle_executed_trade

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

def _probe_executed_quote(symbol):
    """Account entitlement alone is not proof of a fresh executed trade."""
    try:
        payload = get_quote(symbol)
        quote = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(quote, dict):
            return {"ok": False, "status": "INVALID_QUOTE_PAYLOAD",
                    "fresh_executed_trade": False}
        _, trade_time, status = fugle_executed_trade(quote)
        return {
            "ok": status == "FRESH_EXECUTED_TRADE",
            "status": status,
            "api_accessible": True,
            "fresh_executed_trade": status == "FRESH_EXECUTED_TRADE",
            "last_trade_time": trade_time.isoformat() if trade_time else None,
        }
    except PermissionError:
        return {"ok": False, "status": "PLAN_RESTRICTED",
                "api_accessible": False, "fresh_executed_trade": False}
    except Exception as e:
        return {"ok": False, "status": "SOURCE_ERROR",
                "error_type": type(e).__name__, "fresh_executed_trade": False}


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
    out["fugle_quote_2330"] = _probe_executed_quote("2330")
    out["fugle_quote_8089_otc"] = _probe_executed_quote("8089")

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
