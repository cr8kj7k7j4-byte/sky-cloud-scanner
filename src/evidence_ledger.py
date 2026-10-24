from dataclasses import dataclass, asdict
from datetime import datetime


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
