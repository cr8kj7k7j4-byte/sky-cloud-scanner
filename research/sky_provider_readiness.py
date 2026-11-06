"""Read-only provider entitlement preflight. No quote-to-signal promotion.

Separate:
- GitHub secret present
- TSE and OTC market snapshot endpoints authorized and current-session
- snapshot market breadth coverage
- executable trade event confirmation on individual candidates

Snapshot lastPrice can include trial prices, and lastUpdated is not the
last trade's timestamp. Never use them as a source-backed fill.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src import fugle

TZ = ZoneInfo("Asia/Taipei")


def probe_snapshot(market, fetch, today):
    try:
        payload = fetch(market)
    except PermissionError:
        return {"status": "PLAN_RESTRICTED", "http_status": 403,
                "market": market, "snapshot_authorized": False}
    except RuntimeError as exc:
        return {"status": "MISSING_OR_INVALID_CREDENTIAL" if
                "Missing FUGLE_API_KEY" in str(exc) else "PROVIDER_RUNTIME_ERROR",
                "market": market, "snapshot_authorized": False}
    except Exception as exc:
        return {"status": "SOURCE_ERROR", "error_type": type(exc).__name__,
                "market": market, "snapshot_authorized": False}
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return {"market": market, "status": "INVALID_RESPONSE",
                "snapshot_authorized": True}
    records = payload["data"]
    date = str(payload.get("date") or "")
    usable = [x for x in records if isinstance(x, dict)
              and x.get("lastPrice") is not None
              and x.get("isTrial") is not True
              and float_or_zero(x.get("tradeVolume")) > 0]
    status = "AVAILABLE" if date == today and records else "STALE_OR_EMPTY"
    return {"market": market, "status": status, "snapshot_authorized": True,
            "source_date": date, "snapshot_time": payload.get("time"),
            "record_count": len(records), "non_trial_lastprice_with_volume": len(usable),
            "trade_timestamp_per_symbol": False,
            "last_updated_is_trade_time": False}


def float_or_zero(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def probe_single_executed_quote(symbol, fetch, now):
    """Check a granted single-stock endpoint, never infer a fill or whole market."""
    try:
        payload = fetch(symbol)
        quote = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(quote, dict):
            return {"status": "INVALID_QUOTE_PAYLOAD",
                    "api_accessible": True, "event_timestamp_verified": False}
        from src.realtime_quote_evidence import fugle_executed_trade
        _, executed_at, status = fugle_executed_trade(quote, now)
        return {
            "status": status,
            "api_accessible": True,
            "event_timestamp_verified": status == "FRESH_EXECUTED_TRADE",
            "last_trade_time": executed_at.isoformat() if executed_at else None,
        }
    except PermissionError:
        return {"status": "PLAN_RESTRICTED", "api_accessible": False,
                "event_timestamp_verified": False}
    except Exception as exc:
        return {"status": "SOURCE_ERROR", "error_type": type(exc).__name__,
                "api_accessible": False, "event_timestamp_verified": False}


def provider_readiness(now=None, snapshot_fetch=None, single_quote_fetch=None):
    now = now or datetime.now(TZ)
    snapshot_fetch = snapshot_fetch or fugle.snapshot_quotes
    single_quote_fetch = single_quote_fetch or fugle.get_quote
    probes = {market: probe_snapshot(market, snapshot_fetch, now.date().isoformat())
              for market in ("TSE", "OTC")}
    # Two independent samples establish only per-symbol evidence; they do
    # NOT prove breadth, provider bulk access, or exchange-wide certification.
    single_samples = {
        "2330_TSE": probe_single_executed_quote("2330", single_quote_fetch, now),
        "8089_OTC": probe_single_executed_quote("8089", single_quote_fetch, now),
    }
    single = single_samples["2330_TSE"]
    both = all(p["status"] == "AVAILABLE" for p in probes.values())
    if any(p["status"] == "PLAN_RESTRICTED" for p in probes.values()):
        verdict = "BLOCKED_PROVIDER_SNAPSHOT_ENTITLEMENT"
    elif not both:
        verdict = "BLOCKED_SNAPSHOT_SOURCE_OR_DATE"
    else:
        verdict = "BULK_SNAPSHOT_ACCESSIBLE_NOT_YET_MARKET_CERTIFIED"
    return {
        "schema": "SKY_PROVIDER_ENTITLEMENT_PREFLIGHT_V1",
        "generated_at_tpe": now.isoformat(),
        "markets": probes,
        "single_stock_sample": single,
        "single_stock_samples": single_samples,
        "provider_status": verdict,
        "whole_market_live_certified": False,
        "strategy_trade_authorized": False,
        "required_next_gate": (
            "Official TWSE/TPEx universe reconciliation, per-exchange executed "
            "quote and provider snapshot freshness, individual candidate "
            "lastTrade/time verification, Production E2E and scheduled runs."
        ),
        "important_note": (
            "Snapshot lastPrice may include trial matching. Snapshot lastUpdated "
            "is snapshot time, not proof of per-symbol executed trade event."
        ),
    }


def main():
    out = Path("output/provider_readiness")
    out.mkdir(parents=True, exist_ok=True)
    result = provider_readiness()
    (out / "latest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = (
        "# Sky Provider Readiness\n\n"
        f"資料時間：{result['generated_at_tpe']}\n\n"
        f"資料權限：**{result['provider_status']}**\n\n"
        f"TSE：{result['markets']['TSE']['status']}\n\n"
        f"OTC：{result['markets']['OTC']['status']}\n\n"
        f"單檔 2330：{result['single_stock_sample']['status']}\n\n"
        "全市場盤中即時行情尚未認證，不產生買進訊號。\n"
    )
    (out / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
