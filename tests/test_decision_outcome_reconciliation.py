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


def test_wrong_outcome_observation_link_is_rejected():
    corrupted = {**ROW, "outcome": {
        "source_record_id": "not-obs-1",
        "observation_record_id": "obs-1",
        "outcome_type": "SHADOW_EVIDENCE",
    }}
    got = reconcile_decision_outcomes([corrupted])
    assert got["reasons"]["OUTCOME_SOURCE_RECORD_ID_MISMATCH"] == 1
    assert got["ranking_observations"] == 0
    corrupted2 = {**ROW, "outcome": {
        "source_record_id": "obs-1",
        "observation_record_id": "other",
        "outcome_type": "SHADOW_EVIDENCE",
    }}
    got2 = reconcile_decision_outcomes([corrupted2])
    assert got2["reasons"]["OUTCOME_OBSERVATION_ID_MISMATCH"] == 1
    assert got2["ranking_observations"] == 0


def test_real_shadow_to_backfill_to_w4_dedup_preserves_one_identity(tmp_path):
    import json
    from src.paper_trading import build_paper_snapshot, evaluate_paper_gate, write_paper_run_file
    from research.shadow_outcome_backfill import backfill_record
    from research.shadow_promotion_dashboard import load_shadow_records

    observed_at = "2026-11-06T09:35:00+08:00"
    snapshot = build_paper_snapshot(
        run_id="scan-001", observed_at=observed_at,
        item={"symbol": "2330", "name": "TSMC", "exchange": "TWSE",
              "market": {"last": 100.0}, "last": 100.0,
              "strategy_plan": {}, "risk": {"status": "BLOCK"}},
        gate=evaluate_paper_gate("shadow", "REJECTED_OOS"),
    )
    assert snapshot["record_id"] == snapshot["observation_record_id"]
    assert snapshot["decision_id"] is None

    candles = {"data": [{"date": "2026-11-06T09:40:00+08:00",
                         "high": 101.0, "low": 99.0, "close": 100.5}]}
    filled = backfill_record(snapshot, candles, {})
    assert filled["outcome"]["source_record_id"] == snapshot["record_id"]
    assert filled["outcome"]["observation_record_id"] == snapshot["record_id"]
    assert filled["outcome"]["decision_id"] is None

    raw_dir = tmp_path / "scan" / "output" / "paper"
    out_dir = tmp_path / "backfill" / "output" / "paper"
    raw_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)
    write_paper_run_file(raw_dir / "raw.json", [snapshot])
    (out_dir / "outcomes.json").write_text(
        json.dumps({"records": [filled]}), encoding="utf-8")
    rows, files = load_shadow_records(tmp_path)
    assert len(files) == 2
    assert len(rows) == 1
    assert rows[0]["outcome"]["source_record_id"] == snapshot["record_id"]
    audit = reconcile_decision_outcomes(rows)
    assert audit["rows_loaded"] == 1
    assert audit["unique_record_ids"] == 1
    assert audit["ranking_observations"] == 1
    assert audit["eligible_strategy_trades"] == 0
    assert audit["cost_adjusted_expectancy_r"] is None
