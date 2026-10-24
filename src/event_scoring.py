from __future__ import annotations

from datetime import datetime, timezone
from math import exp

EVENT_IMPORTANCE = {
    "EARNINGS": 90,
    "REVENUE": 80,
    "GUIDANCE": 90,
    "CONTRACT_ORDER": 78,
    "CORPORATE_ACTION": 70,
    "INVESTOR_EVENT": 60,
    "MONETARY_POLICY": 92,
    "EXPORT_CONTROL_POLICY": 95,
    "INDUSTRY_NEWS": 55,
    "ATTENTION": 65,
    "DISPOSITION": 85,
    "OTHER": 40,
}

CATALYST_BASE = {
    "EARNINGS": 88,
    "REVENUE": 76,
    "GUIDANCE": 90,
    "CONTRACT_ORDER": 82,
    "CORPORATE_ACTION": 65,
    "INVESTOR_EVENT": 58,
    "MONETARY_POLICY": 85,
    "EXPORT_CONTROL_POLICY": 90,
    "INDUSTRY_NEWS": 52,
    "ATTENTION": 35,
    "DISPOSITION": 20,
    "OTHER": 38,
}

SOURCE_DEFAULTS = {
    "MOPS": 100,
    "TWSE_ATTENTION": 100,
    "TWSE_DISPOSAL": 100,
    "TPEX_ATTENTION": 100,
    "TPEX_DISPOSAL": 100,
    "FEDERAL_RESERVE": 100,
    "BIS": 100,
    "FRED": 95,
    "CBOE": 95,
    "CBC_TAIWAN": 100,
    "OFFICIAL_COMPANY": 95,
    "TRUSTED_MEDIA": 82,
    "UNKNOWN": 40,
}

def _clamp(x):
    return max(0.0, min(100.0, float(x)))

def _event_datetime(event):
    published = event.get("published_at")
    if published:
        s = str(published).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            pass
    d = str(event.get("announce_date") or "")
    t = str(event.get("announce_time") or "")
    if d:
        try:
            hh = int(t[:2]) if len(t) >= 2 else 0
            mm = int(t[2:4]) if len(t) >= 4 else 0
            ss = int(t[4:6]) if len(t) >= 6 else 0
            return datetime.fromisoformat(d).replace(hour=hh, minute=mm, second=ss)
        except Exception:
            return None
    return None

def score_event(event, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    et = str(event.get("event_type") or "OTHER").upper()
    event_score = EVENT_IMPORTANCE.get(et, EVENT_IMPORTANCE["OTHER"])
    catalyst_score = CATALYST_BASE.get(et, CATALYST_BASE["OTHER"])

    if event.get("event_role") == "RISK_EVENT":
        catalyst_score = min(catalyst_score, 35)

    explicit = event.get("authority_score")
    if explicit is not None:
        source_confidence = _clamp(explicit)
    else:
        tier = str(event.get("source_tier") or "").upper()
        source = str(event.get("source") or "UNKNOWN").upper()
        source_confidence = SOURCE_DEFAULTS.get(tier, SOURCE_DEFAULTS.get(source, SOURCE_DEFAULTS["UNKNOWN"]))

    event_dt = _event_datetime(event)
    if event_dt is None:
        freshness_score = 35.0
        age_hours = None
    else:
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=now.tzinfo)
        else:
            event_dt = event_dt.astimezone(now.tzinfo)
        age_hours = max(0.0, (now - event_dt).total_seconds() / 3600.0)
        freshness_score = _clamp(100.0 * exp(-age_hours / 36.0))

    composite = _clamp(
        0.30 * event_score
        + 0.30 * catalyst_score
        + 0.25 * source_confidence
        + 0.15 * freshness_score
    )

    return {
        "event_score": round(event_score, 2),
        "catalyst_score": round(catalyst_score, 2),
        "source_confidence_score": round(source_confidence, 2),
        "freshness_score": round(freshness_score, 2),
        "event_composite_score": round(composite, 2),
        "event_age_hours": round(age_hours, 2) if age_hours is not None else None,
        "research_only": True,
        "trade_signal": False,
        "note": "研究特徵，不代表勝率、真實機率或可直接交易訊號",
    }

def attach_event_scores(events, now=None):
    return [{**e, **score_event(e, now=now)} for e in (events or [])]
