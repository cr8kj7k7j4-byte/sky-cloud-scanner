from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json


# Legacy candidate-level evidence API retained for compatibility.
@dataclass(frozen=True)
class EvidenceRecord:
    field: str
    value: object
    source: str
    observed_at: str | None
    kind: str = "fact"
    note: str = ""

    def to_dict(self):
        return asdict(self)


def build_evidence_ledger(candidate, run_time=None):
    candidate = candidate or {}
    observed_at = candidate.get("quote_time") or run_time
    records = []

    def add(field, value, source, kind="fact", note=""):
        if value is None:
            return
        records.append(EvidenceRecord(
            field=field,
            value=value,
            source=source,
            observed_at=observed_at,
            kind=kind,
            note=note,
        ).to_dict())

    quote_source = candidate.get("quote_source") or "unknown"
    add("last", candidate.get("last"), quote_source)
    add("change_pct", candidate.get("change_pct"), quote_source)
    add("volume", candidate.get("volume"), quote_source)
    add("high", candidate.get("high"), quote_source)
    add("low", candidate.get("low"), quote_source)
    add("open", candidate.get("open"), quote_source)

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
        "generated_at": run_time or datetime.utcnow().isoformat(),
        "records": records,
        "fact_count": sum(1 for x in records if x["kind"] == "fact"),
        "derived_count": sum(1 for x in records if x["kind"] == "derived"),
    }


# P0-K persistent evidence API for Phase 14.
@dataclass(frozen=True)
class LedgerEvidenceRecord:
    evidence_id: str
    source_type: str
    source_name: str
    source_uri: str | None
    published_at: str | None
    observed_at: str
    data_time: str | None
    credibility_tier: str
    content_digest: str
    claim: str
    fact_status: str
    notes: str = ""

    def to_dict(self):
        return asdict(self)


def content_hash(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def append_evidence(path, record):
    r = record if isinstance(record, LedgerEvidenceRecord) else LedgerEvidenceRecord(**record)
    item = r.to_dict()
    item["ledger_fingerprint"] = content_hash(
        json.dumps(item, ensure_ascii=False, sort_keys=True)
    )
    item["logged_at"] = datetime.now(timezone.utc).isoformat()

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    return item


def validate_evidence(record):
    fact_status = str(record.get("fact_status") or "")
    allowed = {"OBSERVABLE_FACT", "ANALYTICAL_INFERENCE", "UNCONFIRMED"}
    issues = []
    if fact_status not in allowed:
        issues.append("invalid_fact_status")
    if not record.get("source_name"):
        issues.append("missing_source_name")
    if not record.get("observed_at"):
        issues.append("missing_observed_at")
    if not record.get("content_digest"):
        issues.append("missing_content_digest")
    return {"valid": not issues, "issues": issues}
