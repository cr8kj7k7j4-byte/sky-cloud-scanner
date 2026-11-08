from research.six_model_zero_candidate_diagnostics import diagnose, diagnose_all


def sample(**changes):
    base = {
        "ui_name": "fixture-model", "model_id": "fixture-1", "model_version": "test",
        "run_id": "test-001", "run_at": "2026-11-06T10:05:00+08:00",
        "source_timestamp": "2026-11-06T10:04:00+08:00",
        "universe": 2000, "market_data": 1900, "valid_executed_trades": 1800,
        "model_inputs": 1700, "research_candidates": 0, "ledger_readback": 0,
        "mobile_visible": 0, "trade_candidates": 0,
        "model_completed": True, "rejection_reasons": {"SETUP_NOT_MET": 1700},
    }
    return base | changes


def test_no_signal_requires_real_rejection_reasons():
    assert diagnose(sample(), market_open=True)["status"] == "NO_SIGNAL"
    result = diagnose(sample(rejection_reasons={}), market_open=True)
    assert result["status"] == "DATA_ERROR"


def test_no_runner_is_not_deployed_not_no_signal():
    assert diagnose(sample(run_id=None), market_open=True)["status"] == "NOT_DEPLOYED"


def test_ledger_mismatch_fails_closed():
    assert diagnose(sample(research_candidates=4, ledger_readback=2), market_open=True)["status"] == "LEDGER_ERROR"


def test_stale_quote_is_explicit():
    assert diagnose(sample(source_timestamp="2026-11-06T09:00:00+08:00"), market_open=True)["status"] == "DATA_STALE"


def test_sunday_never_claims_live_signal():
    result = diagnose(sample(), market_open=False)
    assert result["status"] == "MARKET_CLOSED"
    assert result["trade_authorized"] is False


def test_duplicate_model_identity_is_flagged():
    result = diagnose_all([sample(), sample(ui_name="different card")], market_open=True)
    assert result["status"] == "FAIL_CLOSED"
    assert result["duplicate_model_ids"] == ["fixture-1"]


def test_missing_counters_not_interpreted_as_zero_candidates():
    assert diagnose(sample(market_data=None), market_open=True)["status"] == "DATA_ERROR"


def test_quote_timestamp_cannot_be_in_future():
    assert diagnose(sample(source_timestamp="2026-11-06T10:06:00+08:00"), market_open=True)["status"] == "DATA_ERROR"


def test_valid_research_never_authorizes_production():
    record = sample(research_candidates=3, ledger_readback=3, mobile_visible=3,
                    trade_candidates=0)
    result = diagnose_all([record], market_open=True)
    assert result["models"][0]["status"] == "HEALTHY"
    assert result["production_promotion_eligible"] is False
