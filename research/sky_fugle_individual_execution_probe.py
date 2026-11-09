"""Bounded, Fugle-paid individual lastTrade verification after broad bulk snapshots.

This is a RESEARCH-ONLY parallel evidence rail, NEVER a replacement for the
P0-R market-wide executed coverage gate. Snapshot lastUpdated is not trade time.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.fugle import get_quote
from src.realtime_quote_evidence import fugle_executed_trade

TPE = ZoneInfo("Asia/Taipei")
OUT = Path("output/sky_quickscan_information/fugle_execution_samples.json")
MAX_SAMPLES = 8


def select_symbols(observations, limit=MAX_SAMPLES):
    """Bounded multi-market sample from the Fugle-ranked full-market snapshot."""
    if not isinstance(observations, dict) or not isinstance(observations.get("ranked_observations"), list):
        return []
    if not 1 <= limit <= MAX_SAMPLES:
        raise ValueError("INVALID_SAMPLE_LIMIT")
    ranked = observations["ranked_observations"]
    by_market = {"TWSE": [], "TPEx": []}
    for row in ranked:
        if not isinstance(row, dict) or row.get("source") != "Fugle paid bulk snapshot":
            continue
        if row.get("data_status") not in ("FRESH_EXECUTED_TRADE", "UNVERIFIED_EXECUTION_TIME",
                                          "STALE_EXECUTION_TIME"):
            continue
        symbol = str(row.get("symbol") or "")
        try:
            price = float(row.get("last_price"))
        except (ValueError, TypeError):
            continue
        if not symbol.isdigit() or not 4 <= len(symbol) <= 6 or not 0 < price < 100:
            continue
        exchange = row.get("exchange")
        if exchange in by_market and symbol not in by_market[exchange]:
            by_market[exchange].append(symbol)
    # Alternate markets to avoid the top-gainer side dominating the probe.
    out = []
    while len(out) < limit and any(by_market.values()):
        for exchange in ("TWSE", "TPEx"):
            if by_market[exchange] and len(out) < limit:
                out.append((exchange, by_market[exchange].pop(0)))
    return out


def verify_samples(observations, now=None, *, quote_fetch=get_quote, limit=MAX_SAMPLES):
    now = now or datetime.now(TPE)
    selected = select_symbols(observations, limit)
    items = []
    for exchange, symbol in selected:
        result = {"symbol": symbol, "exchange": exchange,
                  "source": "Fugle paid individual /intraday/quote",
                  "latest_executed_price": None, "last_trade_time": None,
                  "status": "NOT_CHECKED", "research_only": True,
                  "production_eligible": False}
        try:
            quote = quote_fetch(symbol)
            raw = quote.get("data", quote) if isinstance(quote, dict) else None
            if not isinstance(raw, dict):
                result["status"] = "INVALID_PROVIDER_RESPONSE"
            elif str(raw.get("symbol") or "") != symbol:
                result["status"] = "SYMBOL_MISMATCH"
            elif str(raw.get("market") or "").upper() not in (
                    ("TSE", "TWSE") if exchange == "TWSE" else ("OTC", "TPEX")):
                result["status"] = "EXCHANGE_MISMATCH"
            else:
                trade = raw.get("lastTrade")
                # closeTime/lastUpdated are not substitutes for lastTrade.time.
                if not isinstance(trade, dict) or trade.get("time") is None or trade.get("price") is None:
                    price, executed, status = None, None, "MISSING_LAST_TRADE_EVIDENCE"
                else:
                    price, executed, status = fugle_executed_trade(raw, now=now)
                if not (9 <= now.hour < 13 or (now.hour == 13 and now.minute < 30)):
                    status = "OUTSIDE_REGULAR_SESSION"
                    price = None
                result["status"] = status
                result["last_trade_time"] = executed.isoformat() if executed else None
                # Keep only verified executions as executable evidence; other
                # values remain in raw paid research source, never promoted.
                if status == "FRESH_EXECUTED_TRADE":
                    result["latest_executed_price"] = price
        except PermissionError:
            result["status"] = "FUGLE_PERMISSION_DENIED"
        except Exception as exc:
            # Avoid raw provider errors/headers: never disclose credentials.
            result["status"] = "FUGLE_REQUEST_ERROR"
            result["error_type"] = type(exc).__name__
        items.append(result)
    return {"schema": "SKY_FUGLE_INDIVIDUAL_EXECUTION_PROBE_V1",
            "checked_at_tpe": now.isoformat(),
            "snapshot_checked_at_tpe": observations.get("checked_at_tpe"),
            "source": "Fugle paid /intraday/quote only",
            "requested_count": len(selected),
            "verified_fresh_executed_count": sum(
                x["status"] == "FRESH_EXECUTED_TRADE" for x in items),
            "rows": items, "research_only": True,
            "production_eligible": False,
            "full_market_executed_certified": False,
            "note": "Bounded sample; cannot certify full-market freshness or bypass P0-R."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path,
                        default=Path("output/sky_quickscan_information/full_universe.json"))
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--limit", type=int, default=MAX_SAMPLES)
    args = parser.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    report = verify_samples(source, limit=args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("FUGLE_PAID_INDIVIDUAL_PROBE",
          report["requested_count"], report["verified_fresh_executed_count"],
          "RESEARCH_ONLY")


if __name__ == "__main__":
    main()
