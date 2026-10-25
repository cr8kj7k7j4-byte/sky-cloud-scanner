from datetime import datetime, timedelta, timezone
import json
import pandas as pd

from research.build_intraday_pit_replay import run_pipeline
from research.intraday_replay_validator import CANONICAL_RULE_COLUMNS


def _frame():
    ts = datetime(2026, 1, 5, 9, 30, tzinfo=timezone(timedelta(hours=8)))
    row = {
        "decision_id": "d1", "run_id": "r1", "strategy_id": "sky-day-v14",
        "strategy_version": "1.4", "symbol": "2330", "exchange": "TWSE",
        "session_date": "2026-01-05",
        "observation_timestamp": ts.isoformat(),
        "feature_cutoff_timestamp": (ts - timedelta(seconds=1)).isoformat(),
        "decision_timestamp": ts.isoformat(),
        "data_timezone": "Asia/Taipei",
        "feature_schema_version": "test",
        "rule_schema_version": "w2-10-rule-v1",
        "cost_model_version": "test-cost-v1",
        "research_split": "OOS",
        "data_quality_status": "OK",
        "leakage_audit_status": "PASS",
        "market_context_status": "OK",
        "sector_mapping_status": "OK",
        "execution_context_status": "OK",
        "replay_coverage_status": "OK",
        "market_regime": "Neutral", "market_return": 0.0,
        "market_breadth": 0.5, "market_volatility": 0.02,
        "sector": "Semi", "sector_return": 0.01,
        "sector_rs_vs_market": 0.01, "stock_rs_vs_sector": 0.01,
        "cumulative_vwap": 100.0, "price_vs_vwap_pct": 0.001,
        "atr14": 2.0, "price_extension_atr": 0.2,
        "rvol": 1.2, "session_position": 0.5, "stop_distance_pct": 0.01,
        "phase": "P3",
        "candidate_pool_id": "p1", "candidate_pool_size": 1,
        "rank_score": 80.0, "ranking_position": 1, "ranking_decile": 1,
        "ranking_model_version": "rank-v1",
        "planned_entry": 100.0, "planned_stop": 99.0,
        "planned_target_1": 102.0, "gross_rr": 2.0,
        "execution_adjusted_rr": 1.6,
        "net_r_045": 0.5, "net_r_065": 0.3,
    }
    for c in CANONICAL_RULE_COLUMNS:
        row[c] = True
    return pd.DataFrame([row])


def test_builder_attaches_pit_and_passes_w2_contract(tmp_path):
    decisions = tmp_path / "decisions.csv"
    pit = tmp_path / "pit.json"
    out = tmp_path / "out"
    _frame().to_csv(decisions, index=False)
    pit.write_text(json.dumps([
        {
            "symbol": "2330", "exchange": "TWSE", "name": "TSMC",
            "listed_from": "1994-09-05", "listed_to": None,
            "source": "official"
        }
    ]), encoding="utf-8")
    result = run_pipeline(str(decisions), str(pit), str(out))
    assert result["status"] == "PASS"
    replay = pd.read_csv(out / "intraday_pit_replay.csv")
    assert bool(replay.loc[0, "pit_universe_member"])
    assert result["w2_contract"]["gate"] == "PASS"


def test_builder_fails_closed_when_symbol_not_in_pit_universe(tmp_path):
    decisions = tmp_path / "decisions.csv"
    pit = tmp_path / "pit.json"
    out = tmp_path / "out"
    _frame().to_csv(decisions, index=False)
    pit.write_text("[]", encoding="utf-8")
    result = run_pipeline(str(decisions), str(pit), str(out))
    assert result["status"] == "DATA_BLOCKED"
    assert "PIT_UNIVERSE_COVERAGE_FAIL" in result["w2_contract"]["reasons"]
