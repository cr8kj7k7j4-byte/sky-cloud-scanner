from src.decision_outcome_reconciliation import reconcile_decision_outcomes

ROW = {
    "record_id": "obs-1", "observation_record_id": "obs-1",
    "decision_id": None, "decision_provenance_status": "RANKING_OBSERVATION_ONLY",
    "symbol": "2330", "run_id": "123",
    "observed_at": "2026-11-06T09:10:00+08:00",
    "outcome": {"outcome_type": "SHADOW_EVIDENCE", "strategy_counterfactual": {
        "status": "COMPLETE", "r_multiple": 99.0,
    }},
}


def test_observation_with_counterfactual_never_becomes_strategy_trade():
    got = reconcile_decision_outcomes([ROW])
    assert got["ranking_observations"] == 1
    assert got["approved_strategy_decisions"] == 0
    assert got["eligible_strategy_trades"] == 0
    assert got["realized_net_pnl"] is None
    assert got["cost_adjusted_expectancy_r"] is None


def test_identical_duplicate_kept_one_and_conflicting_id_flagged():
    same = reconcile_decision_outcomes([ROW, dict(ROW)])
    assert same["unique_record_ids"] == 1
    assert same["duplicate_rows"] == 1
    assert same["conflicting_duplicates"] == 0
    collision = reconcile_decision_outcomes([ROW, {**ROW, "symbol": "2317"}])
    assert collision["conflicting_duplicates"] == 1
    assert collision["reasons"]["CONFLICTING_RECORD_ID"] == 1


def test_unapproved_trade_claim_and_fill_never_promoted():
    forged = {**ROW, "decision_id": "trade-123",
              "decision_provenance_status": "UNVERIFIED",
              "execution": {"evidence_type": "ACTUAL_EXECUTION",
                            "fill_status": "FILLED",
                            "fill_price": 100,
                            "fill_timestamp": "2026-11-06T09:11:00+08:00",
                            "fill_source": "BROKER"}}
    forged["outcome"] = {"decision_id": "trade-123",
                          "outcome_type": "LIVE", "net_pnl": 999999}
    got = reconcile_decision_outcomes([forged])
    assert got["verified_fill_candidates_not_promotable"] == 1
    assert got["eligible_strategy_trades"] == 0
    assert got["realized_net_pnl"] is None
    assert got["reasons"]["STRATEGY_DECISION_SOURCE_NOT_CERTIFIED"] == 1


def test_invalid_identity_and_mismatched_outcome_are_rejected():
    mismatched = {**ROW, "record_id": "obs-2",
                  "decision_id": "decision-1",
                  "outcome": {"decision_id": "other", "outcome_type": "LIVE"}}
    got = reconcile_decision_outcomes([{}, mismatched])
    assert got["reasons"]["MISSING_RECORD_ID"] == 1
    assert got["reasons"]["OUTCOME_DECISION_ID_MISMATCH"] == 1
    assert got["eligible_strategy_trades"] == 0
