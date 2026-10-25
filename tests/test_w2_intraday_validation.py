from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from research.intraday_replay_validator import (
    CANONICAL_RULE_COLUMNS,
    validate_replay_frame,
)
from research.intraday_rule_ablation import run_ablation
from research.w2_intraday_validation_runner import run_validation


def make_frame(days: int = 60, rows_per_day: int = 2) -> pd.DataFrame:
    rows = []
    base = datetime(2026, 1, 5, 9, 30, tzinfo=timezone(timedelta(hours=8)))
    counter = 0
    for d in range(days):
        for j in range(rows_per_day):
            ts = base + timedelta(days=d, minutes=j * 5)
            counter += 1
            row = {
                "decision_id": f"d{counter}",
                "run_id": f"r{d}",
                "strategy_id": "sky-day-v14",
                "strategy_version": "1.4",
                "symbol": "2330" if j == 0 else "2317",
                "exchange": "TWSE",
                "session_date": ts.date().isoformat(),
                "observation_timestamp": ts.isoformat(),
                "feature_cutoff_timestamp": (ts - timedelta(seconds=1)).isoformat(),
                "decision_timestamp": ts.isoformat(),
                "data_timezone": "Asia/Taipei",
                "feature_schema_version": "test",
                "rule_schema_version": "w2-10-rule-v1",
                "cost_model_version": "test-cost-v1",
                "research_split": "OOS",
                "pit_universe_member": True,
                "data_quality_status": "OK",
                "leakage_audit_status": "PASS",
                "market_context_status": "OK",
                "sector_mapping_status": "OK",
                "execution_context_status": "OK",
                "replay_coverage_status": "OK",
                "market_regime": ["Bull", "Neutral", "Bear"][d % 3],
                "market_return": 0.01,
                "market_breadth": 0.55,
                "market_volatility": 0.02,
                "sector": "Semi",
                "sector_return": 0.012,
                "sector_rs_vs_market": 0.002,
                "stock_rs_vs_sector": 0.003,
                "cumulative_vwap": 50.0,
                "price_vs_vwap_pct": 0.002,
                "atr14": 1.0,
                "price_extension_atr": 0.4,
                "rvol": 1.5,
                "session_position": 0.6,
                "stop_distance_pct": 0.01,
                "phase": "P3",
                "candidate_pool_id": f"pool-{d}",
                "candidate_pool_size": rows_per_day,
                "rank_score": 80.0 - j,
                "ranking_position": j + 1,
                "ranking_decile": 1 if j == 0 else 2,
                "ranking_model_version": "test-rank-v1",
                "planned_entry": 50.0,
                "planned_stop": 49.0,
                "planned_target_1": 52.0,
                "gross_rr": 2.0,
                "execution_adjusted_rr": 1.7,
                "mae_r": -0.3,
                "mfe_r": 1.2,
                "r_multiple": 0.6,
                "false_breakout": False,
                "missed_entry": False,
                "actual_entry_slippage_bps": 2.0,
                "actual_exit_slippage_bps": 3.0,
                "net_r_045": 0.6 if counter % 3 else -0.4,
                "net_r_065": 0.45 if counter % 3 else -0.55,
            }
            for rule in CANONICAL_RULE_COLUMNS:
                row[rule] = True
            rows.append(row)

    # One candidate fails Anti-Chase but remains otherwise eligible. Removing the
    # rule must therefore increase the sample count without retuning anything.
    rows[-1]["anti_chase_gate"] = False
    return pd.DataFrame(rows)


class W2IntradayValidationTests(unittest.TestCase):
    def test_complete_pit_frame_passes_contract(self):
        report = validate_replay_frame(make_frame())
        self.assertEqual(report["gate"], "PASS")
        self.assertEqual(report["reasons"], [])

    def test_missing_sector_context_blocks(self):
        df = make_frame()
        df["sector_mapping_status"] = "MISSING"
        report = validate_replay_frame(df)
        self.assertEqual(report["gate"], "DATA_BLOCKED")
        self.assertIn("SECTOR_MAPPING_COVERAGE_FAIL", report["reasons"])

    def test_remove_one_reports_sample_reduction(self):
        df = make_frame()
        report = run_ablation(df, outcome_column="net_r_045")
        anti = report["single_rule_ablation"]["anti_chase_gate"]
        self.assertEqual(anti["delta_vs_full"]["sample_reduction_count"], 1)
        self.assertGreater(
            anti["without_rule_metrics"]["n"],
            report["full_metrics"]["n"],
        )

    def test_runner_fails_closed_on_bad_timestamp(self):
        df = make_frame()
        df.loc[0, "feature_cutoff_timestamp"] = (
            pd.Timestamp(df.loc[0, "decision_timestamp"]) + pd.Timedelta(minutes=1)
        ).isoformat()
        report = run_validation(df)
        self.assertEqual(report["contract_validation"]["gate"], "DATA_BLOCKED")
        self.assertIsNone(report["ablation_primary_045"])
        self.assertEqual(report["w2_final_status"], "HOLD")


if __name__ == "__main__":
    unittest.main()
