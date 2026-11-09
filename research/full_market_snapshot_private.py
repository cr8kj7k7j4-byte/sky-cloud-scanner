"""Private, research-only Fugle bulk snapshot ledger.

Snapshot lastUpdated is not a per-symbol executed trade timestamp. Raw paid
market data is written ONLY to private GCS, never GitHub Actions artifacts.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")


def build_snapshot(universe, payloads, *, now):
    known = {str(row["symbol"]): row for row in universe}
    result = {symbol: {
        "symbol": symbol, "name": info.get("name"),
        "exchange": info.get("exchange"), "price": None,
        "change_pct": None, "volume": None,
        "price_kind": "NOT_AVAILABLE", "snapshot_time": None,
        "direction": None, "bull_score": None, "bear_score": None,
        "trigger": None, "stop": None, "target": None,
        "model_inference_verified": False, "trade_eligible": False,
        "action": "觀察",
    } for symbol, info in known.items()}
    audits = {}
    for market, exchange in (("TSE", "TWSE"), ("OTC", "TPEx")):
        payload = payloads.get(market)
        if not isinstance(payload, dict):
            raise ValueError("missing_market_payload_" + market)
        if payload.get("date") != now.date().isoformat():
            raise ValueError("stale_market_date_" + market)
        hhmmss = str(payload.get("time") or "")
        if len(hhmmss) != 6 or not hhmmss.isdigit():
            raise ValueError("invalid_snapshot_time_" + market)
        parsed = datetime.combine(now.date(), time(
            int(hhmmss[:2]), int(hhmmss[2:4]), int(hhmmss[4:6])), TPE)
        age = (now - parsed).total_seconds()
        if age < -30 or age > 300:
            raise ValueError("stale_snapshot_" + market)
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise ValueError("invalid_snapshot_rows_" + market)
        seen = set()
        usable = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "")
            if symbol in seen or symbol not in known:
                continue
            if known[symbol].get("exchange") != exchange:
                continue
            seen.add(symbol)
            item = result[symbol]
            item["snapshot_time"] = parsed.isoformat()
            item["quote_source"] = "Fugle paid bulk snapshot " + market
            if row.get("isTrial") is True:
                item["price_kind"] = "TRIAL_EXCLUDED"
                continue
            try:
                p = float(row.get("lastPrice"))
                vol = float(row.get("tradeVolume"))
                if not 0 < p < 10000000 or vol <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            item["price"] = p
            item["volume"] = vol
            try:
                item["change_pct"] = float(row.get("changePercent"))
            except (TypeError, ValueError):
                pass
            item["price_kind"] = "SNAPSHOT_REFERENCE_NOT_VERIFIED_EXECUTION"
            usable += 1
        audits[exchange] = {
            "universe": sum(x.get("exchange") == exchange for x in universe),
            "returned": len(rows), "matched": len(seen),
            "reference_price_present": usable,
            "snapshot_time": parsed.isoformat(),
            "source": "Fugle paid snapshot " + market,
        }
    return {
        "schema": "SKY_PRIVATE_FULL_MARKET_SNAPSHOT_RESEARCH_V1",
        "observation_time": now.isoformat(),
        "universe_count": len(result),
        "by_exchange": audits,
        "observation_count": sum(x["price"] is not None for x in result.values()),
        "evidence_class": "UNVERIFIED_PER_SYMBOL_EXECUTION_TIME",
        "snapshot_price_is_executable": False,
        "six_models_inferred": False,
        "production_signal": False, "orders_authorized": False,
        "trading_decision": "禁止新進場、未驗證通過",
        "observations": sorted(result.values(), key=lambda x: x["symbol"]),
    }


def main():
    from src.official import load_official_universe
    from src.fugle import snapshot_quotes
    from google.cloud import storage

    now = datetime.now(TPE)
    if now.weekday() >= 5 or not time(9, 0) <= now.time() <= time(13, 30):
        raise RuntimeError("not_regular_taiwan_market_session")
    bucket_name = os.environ.get("SKY_RESEARCH_GCS_BUCKET")
    if not bucket_name or not os.environ.get("FUGLE_API_KEY"):
        raise RuntimeError("missing_private_bucket_or_paid_fugle_key")
    universe, counts = load_official_universe()
    if counts["twse"] < 500 or counts["tpex"] < 400:
        raise RuntimeError("official_universe_incomplete")
    payloads = {market: snapshot_quotes(market) for market in ("TSE", "OTC")}
    result = build_snapshot(universe, payloads, now=datetime.now(TPE))
    data = json.dumps(result, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode()
    digest = hashlib.sha256(data).hexdigest()
    run_id = os.environ.get("GITHUB_RUN_ID") or now.strftime("%Y%m%d%H%M%S")
    path = f"full-market-research/v1/{now:%Y/%m/%d}/{run_id}.json"
    blob = storage.Client().bucket(bucket_name).blob(path)
    blob.upload_from_string(data, content_type="application/json",
                            if_generation_match=0)
    if hashlib.sha256(blob.download_as_bytes()).hexdigest() != digest:
        raise RuntimeError("private_gcs_readback_hash_mismatch")
    summary = {
        "status": "PRIVATE_GCS_READBACK_VERIFIED",
        "time": result["observation_time"],
        "universe_count": result["universe_count"],
        "by_exchange": result["by_exchange"],
        "reference_price_present": result["observation_count"],
        "raw_paid_quotes_publicly_uploaded": False,
        "gcs_object": path, "sha256": digest,
        "six_models_inferred": False,
        "production_signal": False, "trade_eligible": False,
    }
    out = Path("output/full_market_private/sanitized_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
