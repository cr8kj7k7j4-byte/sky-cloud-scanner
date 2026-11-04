from research.w4_w6_lineage_audit import audit_forward_execution_joins


def paper():
    return {"decision_id": "d1", "run_id": "r1", "symbol": "2330",
            "observation_timestamp": "2026-11-04T09:05:00+08:00",
            "strategy_version": "v1.4"}


def attempt():
    return {"attempt_id": "a1", "decision_id": "d1", "run_id": "r1",
            "symbol": "2330", "observation_timestamp": "2026-11-04T01:05:00Z",
            "execution_attempt_timestamp": "2026-11-04T01:05:02Z",
            "execution_type": "AGGRESSIVE_MARKETABLE", "source": "L1",
            "strategy_version": "v1.4", "fill_status": "UNKNOWN",
            "research_only": True}


def test_unknown_attempt_joins_but_is_not_fill():
    result = audit_forward_execution_joins([paper()], [attempt()])
    assert result["verified_joined_attempts"] == 1
    assert result["source_backed_fills"] == 0


def test_wrong_symbol_or_version_fails_closed():
    a = attempt()
    a["symbol"] = "2317"
    b = attempt()
    b["attempt_id"] = "a2"
    b["strategy_version"] = "v1.5"
    result = audit_forward_execution_joins([paper()], [a, b])
    assert result["verified_joined_attempts"] == 0
    assert result["rejected_reasons"]["unmatched_paper_decision"] == 1
    assert result["rejected_reasons"]["strategy_version_mismatch"] == 1


def test_missing_decision_id_cannot_join():
    a = attempt()
    a["decision_id"] = None
    result = audit_forward_execution_joins([paper()], [a])
    assert result["verified_joined_attempts"] == 0
    assert result["rejected_reasons"]["invalid_w6_attempt"] == 1


def test_duplicate_paper_identity_not_joinable():
    result = audit_forward_execution_joins([paper(), paper()], [attempt()])
    assert result["verified_joined_attempts"] == 0
    assert result["rejected_reasons"]["ambiguous_paper_identity"] == 1


def test_broker_fill_requires_provenance():
    a = attempt()
    a.update(fill_status="FILLED", fill_price=50.1,
             fill_timestamp="2026-11-04T01:05:04Z", filled_shares=1000,
             requested_shares=1000, source_type="BROKER_EXECUTION",
             broker_execution_id="broker-trade-1")
    result = audit_forward_execution_joins([paper()], [a])
    assert result["source_backed_fills"] == 1


def test_quote_only_cannot_claim_fill():
    a = attempt()
    a.update(fill_status="FILLED", fill_price=50.1,
             fill_timestamp="2026-11-04T01:05:04Z", filled_shares=1000)
    result = audit_forward_execution_joins([paper()], [a])
    assert result["source_backed_fills"] == 0
    assert result["rejected_reasons"]["invalid_w6_attempt"] == 1
