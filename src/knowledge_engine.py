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
