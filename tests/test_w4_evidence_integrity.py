from src.w4_evidence_integrity import audit_forward_strategy_evidence


def record():
    return {
        "run_id": "r1",
        "observed_at": "2026-11-03T09:15:00+08:00",
        "symbol": "2330",
        "research_context": {"regime": "UNKNOWN_LOW"},
        "monitor": {"state": "WATCH"},
        "risk": {"status": "DENY"},
        "strategy": {"trigger": None, "stop": None, "target": None},
        "outcome": {"ranking": {"status": "COMPLETE"}},
    }


def test_ranking_only_never_becomes_trade():
    result = audit_forward_strategy_evidence([record()])
    assert result["ranking_rows_loaded"] == 1
    assert result["eligible_strategy_records"] == 0
    assert result["complete_strategy_outcomes_with_modelled_costs"] == 0
    assert result["observed_execution_fills"] == 0
    assert result["reasons"]["monitor_not_triggered"] == 1
    assert result["unknown_regime_rows"] == 1


def test_trade_outcome_is_not_complete_without_cost_provenance():
    row = record()
    row.update(monitor={"state": "TRIGGERED"}, risk={"status": "ALLOW"},
               strategy={"trigger": 50, "stop": 49, "target": 52})
    row["outcome"]["strategy_counterfactual"] = {"status": "COMPLETE", "r_multiple": 0.5}
    result = audit_forward_strategy_evidence([row])
    assert result["eligible_strategy_records"] == 1
    assert result["complete_strategy_outcomes_with_modelled_costs"] == 0
    assert "missing_cost_fee_rate_per_side" in result["reasons"]


def test_modelled_cost_complete_does_not_prove_fill():
    row = record()
    row.update(monitor={"state": "TRIGGERED"}, risk={"status": "ALLOW"},
               strategy={"trigger": 50, "stop": 49, "target": 52})
    row["outcome"]["strategy_counterfactual"] = {
        "status": "COMPLETE", "r_multiple": 0.2,
        "execution_cost_profile": "USER_CASH_DAYTRADE_20261022",
        "cost_assumptions": {
            "fee_rate_per_side": 0.000333, "sell_tax_rate": 0.0015,
            "entry_impact_rate": 0.0001, "exit_impact_rate": 0.0001,
        },
    }
    result = audit_forward_strategy_evidence([row])
    assert result["complete_strategy_outcomes_with_modelled_costs"] == 1
    assert result["observed_execution_fills"] == 0
    assert result["production_eligible"] is False


def test_invalid_or_preledger_or_missing_symbol_is_excluded():
    a = record()
    a["observed_at"] = "2026-10-24T15:00:00+00:00"
    b = record()
    b["symbol"] = ""
    c = record()
    c["observed_at"] = "not-a-date"
    result = audit_forward_strategy_evidence([a, b, c])
    assert result["post_ledger_valid_rows"] == 0
    assert result["reasons"]["missing_or_preledger_timestamp"] == 2
    assert result["reasons"]["missing_symbol"] == 1


def test_missing_zero_cost_is_allowed_if_explicitly_sourced():
    row = record()
    row.update(monitor={"state": "TRIGGERED"}, risk={"status": "ALLOW"},
               strategy={"trigger": 50, "stop": 49, "target": 52})
    row["outcome"]["strategy_counterfactual"] = {
        "status": "COMPLETE", "r_multiple": 0.1,
        "execution_cost_profile": "TEST_EXPLICIT",
        "cost_assumptions": {
            "fee_rate_per_side": 0, "sell_tax_rate": 0,
            "entry_impact_rate": 0, "exit_impact_rate": 0,
        },
    }
    assert audit_forward_strategy_evidence([row])["modelled_cost_complete_ratio"] == 1.0


def test_forward_trade_provenance_blocks_ranking_only():
    from src.w4_evidence_integrity import audit_forward_trade_provenance
    row = record()
    row.update(record_id="observation-1", observation_record_id="observation-1",
               decision_id=None, decision_provenance_status="RANKING_OBSERVATION_ONLY")
    result = audit_forward_trade_provenance([row])
    assert result["status"] == "PRODUCTION_DECISION_PROVENANCE_BLOCKED"
    assert result["canonical_observation_identity_count"] == 1
    assert result["can_certify_strategy_trades"] is False
    assert result["unverified_trade_provenance_claims"] == 0


def test_unverified_claims_never_automatically_pass():
    from src.w4_evidence_integrity import audit_forward_trade_provenance
    row = record()
    row.update(decision_id="claimed-123", decision_provenance_status="APPROVED")
    result = audit_forward_trade_provenance([row])
    assert result["status"] == "PRODUCTION_DECISION_PROVENANCE_BLOCKED"
    assert result["unverified_trade_provenance_claims"] == 1
    assert result["authoritative_forward_rule_source_verified"] is False


def test_legacy_ranking_without_id_stays_blocked():
    from src.w4_evidence_integrity import audit_forward_trade_provenance
    result = audit_forward_trade_provenance([record()])
    assert result["canonical_observation_identity_count"] == 0
    assert result["provenance_status_counts"]["LEGACY_UNSPECIFIED"] == 1
