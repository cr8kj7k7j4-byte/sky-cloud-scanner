from __future__ import annotations

from datetime import datetime, timezone

def build_news_evidence_ledger(articles, run_time=None):
    generated_at = run_time or datetime.now(timezone.utc).isoformat()
    records = []
    for a in articles or []:
        title = (a.get("subject") or "").strip()
        url = a.get("source_url")
        source = a.get("source") or "unknown"
        published_at = a.get("published_at")
        tier = a.get("source_tier")
        score = a.get("authority_score")
        sectors = a.get("affected_sectors") or []
        if not title or not url or not published_at:
            continue
        records.append({
            "kind": "fact",
            "category": "industry_news",
            "statement": title,
            "source": source,
            "source_url": url,
            "published_at": published_at,
            "observed_at": generated_at,
            "source_tier": tier,
            "authority_score": score,
            "affected_sectors": sectors,
            "trade_signal": False,
            "note": "僅作 P0-K/P0-EVT 外部證據，不直接形成交易訊號",
        })
    return {
        "generated_at": generated_at,
        "record_count": len(records),
        "records": records,
    }
