from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


SOURCE_RANK = {
    "official": 100,
    "exchange": 95,
    "company": 90,
    "research": 75,
    "media": 65,
    "community": 30,
    "unknown": 10,
}


@dataclass(frozen=True)
class Evidence:
    symbol: str
    category: str
    statement: str
    source_type: str
    source_name: str
    source_url: Optional[str] = None
    published_at: Optional[str] = None
    observed_at: Optional[str] = None
    confidence: float = 0.0
    status: str = "FACT"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["source_rank"] = SOURCE_RANK.get(self.source_type, SOURCE_RANK["unknown"])
        return data


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def recency_ok(evidence: Evidence, max_age_hours: Optional[float], now: Optional[datetime] = None) -> bool:
    if max_age_hours is None:
        return True
    dt = _parse_dt(evidence.published_at or evidence.observed_at)
    if dt is None:
        return False
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() <= float(max_age_hours) * 3600


def resolve_conflicts(items: Iterable[Evidence]) -> Dict[str, Any]:
    evidence = list(items)
    by_category: Dict[str, List[Evidence]] = {}
    for item in evidence:
        by_category.setdefault(item.category, []).append(item)

    conflicts = []
    for category, group in by_category.items():
        fact_texts = {x.statement.strip() for x in group if x.status == "FACT" and x.statement.strip()}
        if len(fact_texts) > 1:
            conflicts.append({
                "category": category,
                "statements": sorted(fact_texts),
                "severity": "REVIEW_REQUIRED",
            })

    return {
        "conflict": bool(conflicts),
        "conflicts": conflicts,
        "evidence_count": len(evidence),
    }


def build_evidence_ledger(
    items: Iterable[Evidence],
    *,
    max_age_hours: Optional[float] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    rows = []
    stale = 0
    for item in items:
        row = item.to_dict()
        row["recency_ok"] = recency_ok(item, max_age_hours, now)
        if not row["recency_ok"]:
            stale += 1
        rows.append(row)

    resolution = resolve_conflicts(items)
    return {
        "items": rows,
        "evidence_count": len(rows),
        "stale_count": stale,
        "conflict": resolution["conflict"],
        "conflicts": resolution["conflicts"],
        "decision_eligible": bool(rows) and stale == 0 and not resolution["conflict"],
    }


def market_evidence_from_candidate(candidate: Dict[str, Any], observed_at: str) -> List[Evidence]:
    symbol = str(candidate.get("symbol") or "")
    source = str(candidate.get("source") or "TWSE MIS")
    out: List[Evidence] = []

    last = candidate.get("last")
    if last is not None:
        out.append(Evidence(
            symbol=symbol,
            category="market_price",
            statement=f"最新可取得價格 {float(last):.2f}",
            source_type="exchange",
            source_name=source,
            observed_at=observed_at,
            confidence=1.0,
        ))

    volume = candidate.get("volume")
    if volume is not None:
        out.append(Evidence(
            symbol=symbol,
            category="market_volume",
            statement=f"最新可取得成交量 {int(volume)}",
            source_type="exchange",
            source_name=source,
            observed_at=observed_at,
            confidence=1.0,
        ))

    return out


def build_candidate_structured_ledger(candidate: Dict[str, Any], run_time: Optional[str] = None) -> Dict[str, Any]:
    """Canonical P0-K adapter payload for structured candidate evidence.

    This preserves the legacy evidence_ledger.py output contract while keeping
    the evidence-building logic owned by knowledge_engine.py.
    """
    candidate = candidate or {}
    observed_at = candidate.get("quote_time") or run_time
    records = []

    def add(field, value, source, kind="fact", note=""):
        if value is None:
            return
        records.append({
            "field": field,
            "value": value,
            "source": source,
            "observed_at": observed_at,
            "kind": kind,
            "note": note,
        })

    quote_source = candidate.get("quote_source") or "unknown"
    for field in ("last", "change_pct", "volume", "high", "low", "open"):
        add(field, candidate.get(field), quote_source)

    if candidate.get("universe_source"):
        add("universe", candidate.get("symbol"), candidate.get("universe_source"))

    if candidate.get("relative_strength_score") is not None:
        add(
            "relative_strength_score",
            candidate.get("relative_strength_score"),
            "Sky Relative Strength Engine",
            kind="derived",
            note="由候選池橫向比較計算，不代表勝率",
        )

    if candidate.get("market_intelligence"):
        add(
            "market_intelligence",
            candidate.get("market_intelligence"),
            "Sky P0-M Market Intelligence Engine",
            kind="derived",
        )

    return {
        "generated_at": run_time or datetime.now(timezone.utc).isoformat(),
        "records": records,
        "fact_count": sum(1 for x in records if x["kind"] == "fact"),
        "derived_count": sum(1 for x in records if x["kind"] == "derived"),
    }


def build_news_evidence_ledger(articles, run_time: Optional[str] = None) -> Dict[str, Any]:
    """Canonical P0-K news evidence payload.

    News remains evidence only and never becomes a direct trade signal.
    """
    generated_at = run_time or datetime.now(timezone.utc).isoformat()
    records = []
    for article in articles or []:
        title = (article.get("subject") or "").strip()
        url = article.get("source_url")
        published_at = article.get("published_at")
        if not title or not url or not published_at:
            continue
        records.append({
            "kind": "fact",
            "category": "industry_news",
            "statement": title,
            "source": article.get("source") or "unknown",
            "source_url": url,
            "published_at": published_at,
            "observed_at": generated_at,
            "source_tier": article.get("source_tier"),
            "authority_score": article.get("authority_score"),
            "affected_sectors": article.get("affected_sectors") or [],
            "trade_signal": False,
            "note": "僅作 P0-K/P0-EVT 外部證據，不直接形成交易訊號",
        })
    return {
        "generated_at": generated_at,
        "record_count": len(records),
        "records": records,
    }
