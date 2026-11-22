from research.w6_execution_attempts import validate_attempt, ingest_attempts
import json


def base():
    return dict(attempt_id="a1", decision_id="d1", symbol="2409",
                execution_type="AGGRESSIVE_LIMIT", source="test",
                source_type="QUOTE_ONLY", observation_timestamp="2026-10-28T09:05:00+08:00",
                execution_attempt_timestamp="2026-10-28T09:05:01+08:00",
                fill_status="UNKNOWN", fill_price=None, research_only=True)


def test_unknown_is_allowed_but_is_not_fill():
    assert validate_attempt(base()) == []


def test_quote_cannot_claim_fill():
    x=base()
    x.update(fill_status="FILLED",fill_price=50.1,
             fill_timestamp="2026-10-28T09:05:02+08:00",filled_shares=1000)
    assert "FINAL_FILL_STATUS_REQUIRES_AUTHORIZED_EXECUTION_SOURCE" in validate_attempt(x)


def test_retired_paper_fill_is_rejected_even_with_legacy_pass_marker():
    x=base()
    x.update(source_type="AUTHORIZED_PAPER_ENGINE",fill_status="FILLED",fill_price=50.1,
             fill_timestamp="2026-10-28T09:05:02+08:00",filled_shares=1000)
    assert "RETIRED_PAPER_EXECUTION_SOURCE" in validate_attempt(x)
    assert "FINAL_FILL_STATUS_REQUIRES_AUTHORIZED_EXECUTION_SOURCE" in validate_attempt(x)
    x["paper_gate_verdict"]="PASS_TO_PAPER_TRADING"
    assert "RETIRED_PAPER_EXECUTION_SOURCE" in validate_attempt(x)


def test_retired_paper_source_is_rejected_even_without_a_fill():
    x=base()
    x["source_type"]="AUTHORIZED_PAPER_ENGINE"
    assert "RETIRED_PAPER_EXECUTION_SOURCE" in validate_attempt(x)


def test_source_backed_broker_execution_remains_valid():
    x=base()
    x.update(source_type="BROKER_EXECUTION", broker_execution_id="broker-1",
             fill_status="FILLED", fill_price=50.1,
             fill_timestamp="2026-10-28T09:05:02+08:00", filled_shares=1000)
    assert validate_attempt(x) == []


def test_no_inferred_fill():
    x=base()
    x.update(fill_status="MISSED",fill_price=50.0)
    assert "NON_FILL_CANNOT_HAVE_FILL_DATA" in validate_attempt(x)


def test_attempt_cannot_precede_observation():
    x=base()
    x["execution_attempt_timestamp"]="2026-10-28T09:04:00+08:00"
    assert "ATTEMPT_BEFORE_OBSERVATION" in validate_attempt(x)


def test_ingest_validates_and_deduplicates(tmp_path):
    p=tmp_path/"in.jsonl"
    row=base()
    p.write_text(json.dumps(row)+"\n"+json.dumps(row)+"\n")
    result=ingest_attempts(p,tmp_path/"out.jsonl")
    assert result["accepted"]==1
    assert result["rejected"]==1
