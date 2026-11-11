"""Read only previously accepted #512 live candles into #508 provenance ledger.

This importer is NOT an order/signal producer and NEVER fabricates paper fills.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path

ACCEPTED_RUN = "42950211804"
ACCEPTED_SHA = "b9e2f57b02b6c22b0f45d3fb7ae21e2a1cca0ac0"
ACCEPTED_ARTIFACT = "13824108931"
EXPECTED = {"2409": "TWSE", "5202": "TPEx"}

def aware(s):
    if not isinstance(s, str):
        raise ValueError("MISSING_AWARE_TIME")
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.utcoffset() is None:
        raise ValueError("UNZONED_TIME")
    return d.astimezone(timezone.utc)

def adapt(payload, *, actual_run, actual_sha, artifact_id,
          verified_future_source=None):
    # Historical acceptance stays pinned. A new source is admissible ONLY
    # when the workflow supplies independently verified GitHub metadata.
    expected = (ACCEPTED_RUN, ACCEPTED_SHA, ACCEPTED_ARTIFACT)
    if verified_future_source is not None:
        proof = verified_future_source
        if (not isinstance(proof, dict)
                or proof.get("github_run_verified") is not True
                or proof.get("successful_completed_run") is not True
                or proof.get("unique_artifact_verified") is not True
                or proof.get("source_workflow_matches_accepted") is not True
                or proof.get("production_eligible") is not False):
            raise ValueError("UNVERIFIED_FUTURE_BAR_SOURCE")
        expected = (str(proof.get("run_id")), str(proof.get("head_sha")),
                    str(proof.get("artifact_id")))
        if any(not x or x == "None" for x in expected):
            raise ValueError("INCOMPLETE_FUTURE_BAR_PROVENANCE")
    if (str(actual_run) != expected[0] or actual_sha != expected[1]
            or str(artifact_id) != expected[2]):
        raise ValueError("EXTERNAL_RUN_PROVENANCE_MISMATCH")
    if (not isinstance(payload, dict) or payload.get("head_sha") != actual_sha
            or str(payload.get("run_id")) != str(actual_run)
            or payload.get("schema") != "SKY_V14_TICKER_5M_RESEARCH_PROVENANCE_V1"
            or payload.get("production_eligible") is not False
            or payload.get("automatic_order") is not False
            or payload.get("stage2_quote_verified") is not False):
        raise ValueError("UNTRUSTED_MARKET_RECEIPT")
    at = aware(payload.get("time_tpe"))
    samples = payload.get("samples")
    if not isinstance(samples, list) or len(samples) != len(EXPECTED):
        raise ValueError("SAMPLE_COUNT_MISMATCH")
    output = {}
    for item in samples:
        if not isinstance(item, dict):
            raise ValueError("INVALID_SAMPLE")
        sym,ex = item.get("symbol"), item.get("exchange")
        if sym not in EXPECTED or EXPECTED[sym] != ex or sym in output:
            raise ValueError("SYMBOL_EXCHANGE_DUPLICATE_OR_MISMATCH")
        raw = item.get("raw_five_min_candles")
        if (not isinstance(raw, dict) or raw.get("symbol") != sym
                or raw.get("exchange") != ex or str(raw.get("timeframe")) != "5"
                or not isinstance(raw.get("data"), list)):
            raise ValueError("INVALID_RAW_CANDLE_SOURCE")
        candles = raw["data"]
        accepted = []
        rejected = 0
        previous = None
        for q in candles:
            if not isinstance(q, dict):
                raise ValueError("INVALID_RAW_CANDLE")
            start = aware(q.get("date"))
            if previous is not None and start <= previous:
                raise ValueError("OUT_OF_ORDER_OR_DUPLICATE_CANDLE")
            previous = start
            tpe = start.astimezone(timezone(timedelta(hours=8)))
            if tpe.date() != at.astimezone(timezone(timedelta(hours=8))).date() or tpe.minute % 5:
                raise ValueError("NONCAUSAL_CANDLE_GRID_OR_DATE")
            for key in ("open", "high", "low", "close"):
                val=q.get(key)
                if type(val) not in (int,float) or not math.isfinite(val) or val <= 0:
                    raise ValueError("BAD_OHLC")
            if q["low"] > min(q["open"],q["close"]) or q["high"] < max(q["open"],q["close"]):
                raise ValueError("INVALID_OHLC_ENVELOPE")
            if start + timedelta(minutes=5) > at:
                rejected+=1
                continue
            accepted.append({"symbol":sym,"source_type":"MARKET_OBSERVATION",
                "source_artifact":f"sky-512-5m-evidence-{actual_run}:{artifact_id}",
                "started_at":start.isoformat(),
                "completed_at":(start+timedelta(minutes=5)).isoformat(),
                **{key:q[key] for key in ("open","high","low","close")}})
        if (len(accepted) != item.get("valid_today_five_min_bars")
                or rejected != item.get("excluded_unfinished_five_min_bars",0)+item.get("rejected_future_five_min_bars",0)
                or not accepted or accepted[-1]["started_at"] != aware(item.get("last_feature_bar_time_tpe")).isoformat()
                or item.get("bar_sequence_valid") is not True):
            raise ValueError("CANDLE_FILTER_COUNTS_DO_NOT_RECONCILE")
        output[sym]={"exchange":ex, "accepted_count":len(accepted),
            "excluded_not_finished_or_future":rejected, "completed_bars":accepted}
    if set(output) != set(EXPECTED):
        raise ValueError("MISSING_EXCHANGE_SAMPLE")
    return {"schema":"SKY_P0R_VERIFIED_SOURCE_BARS_V1",
        "source_run_id":str(actual_run),"source_sha":actual_sha,
        "source_artifact_id":str(artifact_id),"observed_at":at.isoformat(),
        "bar_sources":output,
        "market_bars_available":True,
        "approved_precommitted_signal_available":False,
        "paper_events_produced":0,
        "paper_fill_count":0,
        "reconciled":False,
        "verdict":"BARS_VERIFIED_PRECOMMITTED_SIGNAL_MISSING",
        "production_eligible":False,"automatic_order":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--run-id",required=True)
    ap.add_argument("--head-sha",required=True)
    ap.add_argument("--artifact-id",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--verified-future-source",default=None,
                    help="JSON receipt generated from GitHub API, never caller claims")
    args=ap.parse_args()
    attestation=(json.loads(Path(args.verified_future_source).read_text(encoding="utf-8"))
                 if args.verified_future_source else None)
    result=adapt(json.loads(Path(args.input).read_text(encoding="utf-8")),
        actual_run=args.run_id,actual_sha=args.head_sha,artifact_id=args.artifact_id,
        verified_future_source=attestation)
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["verdict"],"source_run_id":result["source_run_id"],
        "bars":{k:v["accepted_count"] for k,v in result["bar_sources"].items()},
        "paper_fill_count":0,"production_eligible":False}))
if __name__=="__main__":
    main()
