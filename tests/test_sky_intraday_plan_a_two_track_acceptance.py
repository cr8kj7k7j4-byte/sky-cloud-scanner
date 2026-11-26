"""Zero-Fugle tests for W0 #363 intraday Plan A's independent A1/A2 gates."""
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.sky_full_universe_information import build
from research.sky_fugle_individual_execution_probe import verify_samples
from research.sky_intraday_plan_a_two_track_acceptance import assess, main, OBSERVATION, EXECUTION

NOW = datetime(2026, 11, 24, 12, 44, tzinfo=ZoneInfo("Asia/Taipei"))


def data():
    universe = [{"symbol": "1101", "exchange": "TWSE", "name": "A"},
                {"symbol": "8089", "exchange": "TPEx", "name": "B"}]
    snaps = {
        "TSE": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "1101", "lastPrice": 42, "tradeVolume": 999, "changePercent": 2}]},
        "OTC": {"date": NOW.date().isoformat(), "data": [
            {"symbol": "8089", "lastPrice": 39, "tradeVolume": 888, "changePercent": 1}]},
    }
    whole = build(universe, snaps, NOW)
    def provider(symbol):
        return {"symbol": symbol, "market": "TSE" if symbol == "1101" else "OTC",
                "date": NOW.date().isoformat(),
                "lastTrade": {"price": 42 if symbol == "1101" else 39,
                              "time": int((NOW + timedelta(seconds=3)).timestamp() * 1000)}}
    probe = verify_samples(whole, now=NOW + timedelta(seconds=4), quote_fetch=provider)
    operational = {"operational_full_market_scan": False,
                   "quote_scope": "PARTIAL_EXECUTED_LIVE",
                   "market_data_gate": "BLOCKED_EXTERNAL_DATA_NO_TRADE",
                   "live_market_evidence": {"valid_whole_market_operational": False}}
    return whole, probe, operational


def test_a1_without_snapshot_last_trade_and_a2_with_real_last_trade():
    whole, probe, operational = data()
    assert whole["fresh_executed_count"] == 0
    assert whole["snapshot_reference_without_trade_time_count"] == 2
    result = assess(whole, probe, operational, run_id="123", run_attempt="1",
                    head_sha="abc", event="workflow_dispatch")
    assert result["snapshot_screen_status"] == OBSERVATION
    assert result["candidate_execution_status"] == EXECUTION
    assert result["full_market_execution_status"].startswith("HOLD")
    assert result["production_eligible"] is False
    assert result["trade_action"] == "禁止交易"
    assert result["run_id"] == "123"
    assert not result["full_market_gate_promoted_by_a1_or_a2"]


def test_missing_or_invalid_sources_fail_closed():
    whole, probe, operational = data()
    for a, b, c in ((None, None, None), ({}, probe, operational),
                    (whole, None, operational)):
        result = assess(a, b, c)
        assert (result["snapshot_screen_status"].startswith("HOLD")
                or result["candidate_execution_status"].startswith("HOLD"))
        assert result["production_eligible"] is False


def test_a1_rejects_bad_source_date_coverage_and_count():
    whole, probe, operational = data()
    for mutate in (
        lambda x: x["snapshot_integrity"]["TPEx"].update({"snapshot_date": "2026-11-23"}),
        lambda x: x["all_symbols"][1].update({"source": "NO_SNAPSHOT_ROW"}),
        lambda x: x["all_symbols"][1].update({"production_eligible": True}),
        lambda x: x.update({"universe_count": 99}),
    ):
        altered = deepcopy(whole)
        mutate(altered)
        result = assess(altered, probe, operational)
        assert result["snapshot_screen_status"].startswith("HOLD")
        assert result["trade_action"] == "禁止交易"


def test_a2_rejects_unrelated_or_fabricated_fresh_trade():
    whole, probe, operational = data()
    for mutate in (
        lambda x: x["rows"][0].update({"symbol": "9999"}),
        lambda x: x["rows"][0].update({"last_trade_time": NOW.replace(year=2025).isoformat()}),
        lambda x: x["rows"][0].update({"latest_executed_price": None}),
        lambda x: x.update({"verified_fresh_executed_count": 500}),
        lambda x: x.update({"full_market_executed_certified": True}),
    ):
        altered = deepcopy(probe)
        mutate(altered)
        result = assess(whole, altered, operational)
        assert result["candidate_execution_status"].startswith("HOLD")
        assert result["production_eligible"] is False



def test_a2_future_trade_within_legacy_clock_skew_is_rejected_by_pit():
    """A report cannot certify a trade which occurred after its observation."""
    whole, probe, operational = data()
    observed = datetime.fromisoformat(probe["checked_at_tpe"])
    # The lower-level parser historically tolerates <=30s future clock skew.
    # This A2 acceptance gate must remain strictly causal.
    altered = deepcopy(probe)
    altered["rows"][0]["last_trade_time"] = (observed + timedelta(seconds=5)).isoformat()
    assert altered["rows"][0]["status"] == "FRESH_EXECUTED_TRADE"
    result = assess(whole, altered, operational)
    assert result["candidate_execution_status"] == "HOLD_INVALID_LAST_TRADE_PRICE_TIME"
    assert result["production_eligible"] is False
    assert result["trade_action"] == "禁止交易"


def test_a2_equal_observation_timestamp_does_not_look_ahead():
    whole, probe, operational = data()
    altered = deepcopy(probe)
    altered["rows"][0]["last_trade_time"] = altered["checked_at_tpe"]
    result = assess(whole, altered, operational)
    assert result["candidate_execution_status"] == EXECUTION
    assert result["production_eligible"] is False


def test_a2_not_inferred_from_snapshot_refresh_or_last_price():
    whole, probe, operational = data()
    altered = deepcopy(probe)
    for row in altered["rows"]:
        row["status"] = "MISSING_LAST_TRADE_EVIDENCE"
        row["latest_executed_price"] = None
        row["last_trade_time"] = None
    altered["verified_fresh_executed_count"] = 0
    assert assess(whole, altered, operational)["candidate_execution_status"] == (
        "HOLD_NO_FRESH_CANDIDATE_EXECUTION")


def test_full_market_flag_cannot_be_promoted_by_a1_or_a2():
    whole, probe, operational = data()
    for candidate in (
        {},
        {"operational_full_market_scan": True,
         "quote_scope": "PARTIAL_EXECUTED_LIVE",
         "market_data_gate": "PASS_FULL_MARKET_LIVE",
         "live_market_evidence": {"valid_whole_market_operational": True}},
    ):
        result = assess(whole, probe, candidate)
        assert result["snapshot_screen_status"] == OBSERVATION
        assert result["candidate_execution_status"] == EXECUTION
        assert result["full_market_execution_status"].startswith("HOLD")
        assert result["trade_action"] == "禁止交易"


def test_workflow_only_joins_existing_evidence_and_uploads_same_run():
    from pathlib import Path
    wf = Path(".github/workflows/scan.yml").read_text(encoding="utf-8")
    assert "python -m research.sky_intraday_plan_a_two_track_acceptance" in wf
    assert wf.index("python -m research.sky_intraday_plan_a_two_track_acceptance") < wf.index("Upload scan report")
    assert "if: always()" in wf
    assert "Verify operational market coverage" in wf
    assert "BLOCKED_EXTERNAL_DATA: full-market actual executed quotes not verified" in wf
    assert "sky-fugle-paid-global-research-v1-live-wholemarket" in wf
    assert "run: python -m unittest tests.test_sky_paid_fugle_api_guard -v" in wf

def test_formal_scan_disables_live_five_minute_probe_but_keeps_a2_claim():
    """V5.4: no live 5m API request; A1/A2 and the atomic Claim remain intact."""
    from pathlib import Path
    wf = Path(".github/workflows/scan.yml").read_text(encoding="utf-8")
    assert "Preserve bounded two-market Fugle 5m evidence inside current paid Claim" not in wf
    assert "existing_five_min_probe(" not in wf
    assert "sky_v14_ticker_candles_probe" not in wf
    assert '"live_five_minute_requests":"DISABLED_V5_4"' in wf
    assert '"independent_tick_vwap_requests":"DISABLED_V5_4"' in wf
    assert "Verify bounded paid Fugle individual last-trades" in wf
    assert "Independently verify paid reservation" in wf
    assert "Reserve shared paid Fugle slot before any paid observations" in wf
    assert "Join MCR research observations" in wf
    assert "Preserve same-run raw-source availability manifest" in wf
    assert "Verify operational market coverage" in wf
    assert "BLOCKED_EXTERNAL_DATA: full-market actual executed quotes not verified" in wf
