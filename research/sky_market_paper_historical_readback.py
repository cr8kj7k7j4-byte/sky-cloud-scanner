"""Reconcile archived #511, five-minute and #508 research evidence without network I/O."""
import argparse
from datetime import timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

from research.sky_p0r_512_source_adapter import (
    ACCEPTED_ARTIFACT, ACCEPTED_RUN, ACCEPTED_SHA, adapt, aware,
)

TPE = timezone(timedelta(hours=8))
SNAPSHOT_RUN = "42863180723"
PAPER_RUN = "43368502780"


def read_artifact(path, member, digest):
    archive = path.read_bytes()
    if hashlib.sha256(archive).hexdigest() != digest:
        raise ValueError(f"Artifact digest mismatch for {member}")
    with ZipFile(io.BytesIO(archive)) as source:
        return json.loads(source.read(member))


def reconcile(snapshot_zip, candles_zip, paper_zip):
    snapshot = read_artifact(
        snapshot_zip, "receipt.json",
        "1a2f0aca045c9c31b632bec395af3e8b9b4fb460df9a2d892c95065eb14c5f00",
    )
    candles = read_artifact(
        candles_zip, "v14_ticker_5m_evidence.json",
        "46138c011f0b8fa21696d1b4976294f740a7caa2f4d95aea95085bc317e10328",
    )
    paper = read_artifact(
        paper_zip, "sky_p0r_paper_ledger_readback/explicit_e2e_gate.json",
        "6c37d4b1f316fc91cd002b5db82aa7ba9b01613d59de47584f05c63d1f30642b",
    )
    bars = adapt(candles, actual_run=ACCEPTED_RUN, actual_sha=ACCEPTED_SHA,
                 artifact_id=ACCEPTED_ARTIFACT)
    if (
        snapshot["schema"] != "SKY_SNAPSHOT_INTEGRITY_RESEARCH_RECEIPT_V1"
        or snapshot["run_id"] != SNAPSHOT_RUN
        or snapshot["head_sha"] != "444dbf1abf7488b185c31b76b4c0c5f0e3833b4d"
        or paper["schema"] != "SKY_P0R_EXPLICIT_E2E_GATE_V1"
        or paper["workflow_run_id"] != PAPER_RUN
        or paper["head_sha"] != "6f096ccf0be265780c079224c4ae625c0a8a9fd9"
        or any(item["production_eligible"] is not False or item["automatic_order"] is not False
               for item in (snapshot, candles, paper))
    ):
        raise ValueError("Source provenance or research scope mismatch")
    market = snapshot["snapshot_integrity"]
    if any(
        market[exchange]["api_response_valid"] is not True
        or market[exchange]["snapshot_time_is_execution_time"] is not False
        for exchange in ("TWSE", "TPEx")
    ):
        raise ValueError("Snapshot source semantics mismatch")
    bar_date = aware(bars["observed_at"]).astimezone(TPE).date().isoformat()
    same_session = all(market[exchange]["snapshot_date"] == bar_date
                       for exchange in ("TWSE", "TPEx"))
    reasons = [] if same_session else ["SNAPSHOT_BAR_SESSION_MISMATCH"]
    if paper["signal_reason"]:
        reasons.append(paper["signal_reason"])
    if paper["paper_fill_count"] == 0:
        reasons.append("NO_PAPER_FILLS_IN_SOURCE")
    return {
        "schema": "SKY_HISTORICAL_MARKET_PAPER_READBACK_V1",
        "verdict": "INSUFFICIENT_DATA",
        "reasons": reasons,
        "snapshot_run_id": SNAPSHOT_RUN,
        "snapshot_artifact_id": "13786157016",
        "snapshot_head_sha": snapshot["head_sha"],
        "snapshot_integrity": market,
        "snapshot_fresh_executed_count": snapshot["fresh_executed_count"],
        "bar_run_id": ACCEPTED_RUN,
        "bar_artifact_id": ACCEPTED_ARTIFACT,
        "bar_head_sha": ACCEPTED_SHA,
        "bar_trading_date_tpe": bar_date,
        "bar_counts": {symbol: sample["accepted_count"]
                       for symbol, sample in bars["bar_sources"].items()},
        "same_trading_session": same_session,
        "paper_run_id": PAPER_RUN,
        "paper_artifact_id": "14011521151",
        "paper_head_sha": paper["head_sha"],
        "source_paper_verdict": paper["paper_e2e_verdict"],
        "source_paper_fill_count": paper["paper_fill_count"],
        "production_eligible": False,
        "automatic_order": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "candles", "paper"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.snapshot, args.candles, args.paper),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
