from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .event_intelligence import scan_recent_events
from .official import load_official_universe
from .premarket_ranking import rank_premarket_candidates
from .global_market_context import build_global_context
from .global_sector_mapping import map_global_context_to_sectors

TZ = ZoneInfo("Asia/Taipei")
OUT = Path("output/premarket")

def _persist_redis(payload: dict):
    url = os.getenv("REDIS_URL", "").strip()
    key = os.getenv("PREMARKET_REDIS_KEY", "sky:p0evt:latest").strip()
    if not url:
        return {"backend": "none", "persistent": False, "ok": False, "reason": "REDIS_URL_NOT_SET"}
    try:
        import redis
        client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=5, socket_timeout=10)
        client.set(key, json.dumps(payload, ensure_ascii=False))
        return {"backend": "redis", "persistent": True, "ok": True, "key": key}
    except Exception as exc:
        return {"backend": "redis", "persistent": True, "ok": False, "error": f"{type(exc).__name__}: {exc}"}

def run():
    now = datetime.now(TZ)
    OUT.mkdir(parents=True, exist_ok=True)

    universe, ust = load_official_universe()
    symbols = [str(x["symbol"]) for x in universe if x.get("symbol")]
    universe_by_symbol = {str(x["symbol"]): x for x in universe if x.get("symbol")}
    max_symbols = int(os.getenv("PREMARKET_EVENT_MAX_SYMBOLS", "2000"))
    lookback_days = int(os.getenv("PREMARKET_LOOKBACK_DAYS", "3"))
    scan_symbols = symbols[:max_symbols]

    events, errors, source_health = scan_recent_events(
        scan_symbols,
        lookback_days=lookback_days,
        now=now,
        max_symbols=max_symbols,
        workers=int(os.getenv("PREMARKET_EVENT_WORKERS", "8")),
    )

    global_context = build_global_context(now=now, lookback_days=lookback_days)
    if global_context.get("macro_events"):
        events = list(events) + list(global_context["macro_events"])

    sector_context = map_global_context_to_sectors(global_context)

    counts = Counter(e["event_type"] for e in events)
    ranked_candidates = rank_premarket_candidates(
        events,
        universe_by_symbol=universe_by_symbol,
        now=now,
        limit=int(os.getenv("PREMARKET_RANK_LIMIT", "50")),
    )
    payload = {
        "generated_at": now.isoformat(),
        "module": "P0-EVT",
        "mode": "PREMARKET_EVENT_SCAN",
        "source": "MOPS",
        "lookback_days": lookback_days,
        "universe_count": len(symbols),
        "scanned_symbol_count": len(scan_symbols),
        "coverage_pct": round((len(scan_symbols) / len(symbols) * 100), 2) if symbols else 0,
        "full_market_event_scan": bool(symbols and len(scan_symbols) >= len(symbols)),
        "official_universe_health": ust,
        "events_found": len(events),
        "errors_count": len(errors),
        "event_type_counts": dict(counts),
        "source_health": source_health,
        "global_context": global_context,
        "sector_context": sector_context,
        "ranked_candidates": ranked_candidates,
        "events": events,
        "errors": errors[:100],
        "warnings": [],
    }

    if not payload["full_market_event_scan"]:
        payload["warnings"].append(
            "本次 P0-EVT 為部分官方母池掃描，不得宣稱全市場事件掃描；"
            "未掃描標的視為 UNKNOWN，不得視為無事件。"
        )

    persist = _persist_redis(payload)
    payload["persistence"] = persist

    (OUT / "latest_event_snapshot.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        f"Sky 盤前情報掃描｜{now:%Y-%m-%d %H:%M}",
        f"官方母池：{len(symbols)}｜已掃描：{len(scan_symbols)}｜覆蓋率：{payload['coverage_pct']}%",
        f"事件總數：{len(events)}｜錯誤：{len(errors)}",
        f"持久化：{persist.get('backend')}｜{'成功' if persist.get('ok') else '未完成'}",
        "",
        "【來源健康度】",
    ]
    for k, v in source_health.items():
        lines.append(f"{k}｜ok={v.get('ok')}｜events={v.get('events')}｜errors={v.get('errors')}")
    lines += [
        "",
        "【國際隔夜背景】",
    ]
    vix = global_context.get("vix")
    us10y = global_context.get("us10y")
    lines.append(
        f"VIX：{vix.get('value') if vix else 'UNKNOWN'}｜"
        f"US10Y：{us10y.get('value') if us10y else 'UNKNOWN'}%｜"
        f"全球風險狀態：{global_context.get('risk_state', 'UNKNOWN')}"
    )
    adr = global_context.get("adr_context") or {}
    gold = global_context.get("gold_context") or {}
    lines.append(
        f"ADR：{adr.get('status', 'NOT_CONNECTED')}｜"
        f"黃金：{gold.get('status', 'NOT_CONNECTED')}｜"
        f"BIS政策事件：{len(global_context.get('bis_policy_events') or [])}"
    )
    coverage = global_context.get("coverage") or {}
    missing = [k for k, ok in coverage.items() if not ok]
    if missing:
        lines.append("尚未接通：" + "、".join(missing))

    lines += ["", "【全球背景→台股族群映射】"]
    for s in sector_context:
        lines.append(
            f"{s['sector']}｜背景分數 {s['context_score']}｜{s['bias']}｜"
            f"+{','.join(s['positive_factors']) or '-'}｜-{','.join(s['negative_factors']) or '-'}"
        )

    lines += [
        "",
        "【事件分類】",
    ]
    if counts:
        for k, v in counts.most_common():
            lines.append(f"{k}: {v}")
    else:
        lines.append("目前未取得事件；不代表市場無重大事件。")

    lines += ["", "【盤前候選排序｜P0-O】"]
    if ranked_candidates:
        for r in ranked_candidates[:20]:
            lines.append(
                f"{r['ranking_position']}. {r['symbol']} {r.get('name','')}｜"
                f"分數 {r['premarket_score']}｜Catalyst {r['catalyst_score']}｜"
                f"Risk -{r['risk_penalty']}｜{r['classification']}"
            )
    else:
        lines.append("目前沒有事件型候選；不強迫產生名單。")

    lines += ["", "【最新事件】"]
    for e in events[:30]:
        lines.append(
            f"{e['announce_date']} {e['announce_time']}｜{e['symbol']} {e.get('name','')}｜"
            f"{e['event_type']}｜{e['subject']}"
        )
    if not events:
        lines.append("無可列示事件。")

    if payload["warnings"]:
        lines += ["", "【限制】", *payload["warnings"]]

    (OUT / "latest_premarket.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    run()
