from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import exp

CATALYST_WEIGHTS = {
    "EARNINGS": 24,
    "REVENUE": 20,
    "GUIDANCE": 22,
    "INVESTOR_EVENT": 12,
    "CONTRACT_ORDER": 18,
    "CORPORATE_ACTION": 12,
    "OTHER": 6,
}
RISK_PENALTIES = {
    "ATTENTION": 18,
    "DISPOSITION": 35,
}

def _recency_weight(event, now):
    try:
        d = datetime.fromisoformat(str(event.get("announce_date"))).date()
        age = max(0, (now.date() - d).days)
        return exp(-0.55 * age)
    except Exception:
        return 0.5

def rank_premarket_candidates(events, universe_by_symbol=None, now=None, limit=50):
    now = now or datetime.now()
    universe_by_symbol = universe_by_symbol or {}
    grouped = defaultdict(list)
    for event in events or []:
        symbol = str(event.get("symbol") or "").strip()
        if symbol:
            grouped[symbol].append(event)

    ranked = []
    for symbol, rows in grouped.items():
        catalyst_score = 0.0
        risk_penalty = 0.0
        catalyst_types = set()
        risk_types = set()
        latest = None
        for e in rows:
            et = str(e.get("event_type") or "OTHER").upper()
            w = _recency_weight(e, now)
            if et in RISK_PENALTIES:
                risk_penalty += RISK_PENALTIES[et] * w
                risk_types.add(et)
            else:
                catalyst_score += CATALYST_WEIGHTS.get(et, CATALYST_WEIGHTS["OTHER"]) * w
                catalyst_types.add(et)
            key = (str(e.get("announce_date") or ""), str(e.get("announce_time") or ""))
            if latest is None or key > latest[0]:
                latest = (key, e)

        raw = catalyst_score - risk_penalty
        score = max(0.0, min(100.0, 50.0 + raw))
        meta = universe_by_symbol.get(symbol) or {}
        ranked.append({
            "symbol": symbol,
            "name": meta.get("name") or (latest[1].get("name") if latest else ""),
            "exchange": meta.get("exchange"),
            "premarket_score": round(score, 2),
            "catalyst_score": round(catalyst_score, 2),
            "risk_penalty": round(risk_penalty, 2),
            "catalyst_types": sorted(catalyst_types),
            "risk_types": sorted(risk_types),
            "event_count": len(rows),
            "latest_event": latest[1] if latest else None,
            "classification": (
                "RISK_REVIEW"
                if "DISPOSITION" in risk_types or "ATTENTION" in risk_types
                else "WATCH"
            ),
            "trade_signal": False,
            "note": "盤前事件排序僅用於候選優先序，不代表勝率、方向或買進訊號",
        })

    ranked.sort(
        key=lambda x: (
            x["classification"] != "RISK_REVIEW",
            x["premarket_score"],
            x["catalyst_score"],
            x["event_count"],
        ),
        reverse=True,
    )
    for i, row in enumerate(ranked[:limit], 1):
        row["ranking_position"] = i
    return ranked[:limit]
