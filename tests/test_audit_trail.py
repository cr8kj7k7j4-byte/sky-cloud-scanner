import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.audit_trail import DecisionAuditRecord,append_audit_record,reconstructability_check
from src.evidence_ledger import LedgerEvidenceRecord,append_evidence,content_hash,validate_evidence
from src.decision_explainability import explain_decision

def main():
    with tempfile.TemporaryDirectory() as td:
        evidence=LedgerEvidenceRecord(
            evidence_id="ev-1",
            source_type="MARKET_DATA",
            source_name="TWSE",
            source_uri=None,
            published_at=None,
            observed_at="2026-10-25T09:30:00+08:00",
            data_time="2026-10-25T09:29:59+08:00",
            credibility_tier="A",
            content_digest=content_hash("price snapshot"),
            claim="官方市場資料快照",
            fact_status="OBSERVABLE_FACT",
        )
        ev=append_evidence(Path(td)/"evidence.jsonl",evidence)
        assert validate_evidence(ev)["valid"] is True

        record=DecisionAuditRecord(
            decision_id="d-1",
            symbol="2409",
            decision_time="2026-10-25T09:30:02+08:00",
            action="BLOCK",
            decision_status="REJECTED",
            market_state="NORMAL",
            regime="BULL_MEDIUM",
            strategy_version="sky-v2.1",
            model_version="rule-engine-1.0",
            feature_schema_version="1.0.0",
            rule_config_version="2.1.0",
            data_sources=("TWSE","FUGLE"),
            evidence_ids=("ev-1",),
            passed_gates=("market_gate","sector_rs_gate"),
            blocked_gates=("anti_chase_gate",),
            risk_status="ALLOW",
            execution_status="COMPLETE",
            rationale="價格高於最高可接受買價，禁止追高",
        )
        saved=append_audit_record(
            Path(td)/"audit.jsonl",
            record,
            input_payload={"last":37.8,"max_entry":37.5},
        )
        assert reconstructability_check(saved)["reconstructable"] is True
        exp=explain_decision(saved)
        assert exp["action"]=="禁止交易"
        assert exp["primary_reason"]=="主要否決：anti_chase_gate"
        assert exp["versions"]["strategy"]=="sky-v2.1"

    print("PASS Audit Trail + Decision Explainability + Evidence Ledger tests")

if __name__=="__main__":
    main()
