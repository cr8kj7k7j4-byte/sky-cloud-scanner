"""Fail-closed revenue-event-to-Fugle replay eligibility check.

A historical price API response is not issuer publication evidence. Only
independently attested issuer publication and observation may authorize a
later cost-aware strategy replay. This module issues NO trading signals.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path


def aware(value):
    if not isinstance(value, str):
        raise ValueError("missing event timestamp")
    x = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if x.tzinfo is None or x.utcoffset() is None:
        raise ValueError("event timestamp missing timezone")
    return x


def assess(ledger):
    events = ledger.get("events", {})
    if not isinstance(events, dict) or ledger.get("production_signal") is not False:
        raise ValueError("invalid or unsafe event ledger")
    candidates = []
    rejected = {"MISSING_OR_UNVERIFIED_ORIGINAL_FILING": 0,
                "UNVERIFIED_PUBLICATION_SOURCE": 0,
                "UNVERIFIED_FILING_RECEIPT": 0,
                "TIMESTAMP_ORDER_INVALID": 0,
                "NOT_REVENUE_EVENT": 0}
    for key, item in events.items():
        if item.get("provisional_identity", {}).get("category") != "MONTHLY_REVENUE":
            rejected["NOT_REVENUE_EVENT"] += 1
            continue
        published = item.get("issuer_original_published_at")
        if not published:
            rejected["MISSING_OR_UNVERIFIED_ORIGINAL_FILING"] += 1
            continue
        if item.get("issuer_publication_source_verified") is not True:
            rejected["UNVERIFIED_PUBLICATION_SOURCE"] += 1
            continue
        if not item.get("independent_filing_verification_receipt_sha256"):
            rejected["UNVERIFIED_FILING_RECEIPT"] += 1
            continue
        try:
            if aware(published) > aware(item["first_observed_at_utc"]):
                raise ValueError("event published after first-observed")
        except (KeyError, ValueError, TypeError):
            rejected["TIMESTAMP_ORDER_INVALID"] += 1
            continue
        candidates.append(key)
    # Even eligible evidence still requires independent official issuer
    # confirmation, strategy signals, full-universe PIT, fills and risk gates.
    return {
        "model": "FUGLE_REVENUE_EVENT_REPLAY_GATE_V1",
        "status": "INSUFFICIENT_DATA",
        "production_signal": False,
        "revenue_event_evidence_candidates": len(candidates),
        "independent_issuer_filing_review_passed": False,
        "event_backtest_trades_executed": 0,
        "event_backtest_profitability_verified": False,
        "fugle_market_price_provenance": "See Fugle Developer 1Y Run #42416763557",
        "fugle_fixed_non_event_0050_replay": "See Run #42416924677",
        "rejections": rejected,
        "blocked_reason": "Issuer event PIT and GCS durable evidence not verified. No event strategy replay or execution-grade fill inference.",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ledger",default="research_output/disclosure_provisional_events.json")
    ap.add_argument("--out",default="research_output/fugle_event_replay_readiness.json")
    args=ap.parse_args()
    ledger=json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    result=assess(ledger)
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":
    main()
