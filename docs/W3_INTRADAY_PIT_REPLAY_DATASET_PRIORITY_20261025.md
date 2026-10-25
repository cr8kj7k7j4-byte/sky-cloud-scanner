# W3｜Intraday PIT Historical Replay Dataset — Priority Handoff 2026-10-25

> Owner: W3｜Sky 資料與系統工程
> Requested by: W0｜Sky 總控與版本治理
> Priority: **P0 / Highest**
> Purpose: unblock W2 canonical intraday validation. This task does not modify Production trading rules.

## 1. Objective

Build the canonical historical intraday point-in-time replay dataset required by:
- `research/INTRADAY_PIT_REPLAY_CONTRACT_V1.md`
- 10-Rule Remove-One Ablation
- Walk-forward / Regime Stability
- 0.45% / 0.65% cost stress
- W2 fail-closed validation runner

Row grain:
`one symbol × one observation_timestamp × one candidate decision`.

## 2. Non-negotiable governance

1. Must be point-in-time aligned.
2. No future bars or hindsight labels in decision-time features.
3. No current-only sector mapping backfilled into history.
4. Unknown execution inputs stay NULL/UNKNOWN/BLOCKED; never impute zero for convenience.
5. Preserve candidate pool context for ranking, not only winners.
6. Outcomes are joined only after the decision-time feature freeze.
7. Counterfactual outcomes must remain clearly labeled and must not be described as actual fills or realized P&L.
8. Dataset must not alter Sky Day Trading v1.4 Production behavior.

## 3. Required minimum coverage gate

Before W2 may execute full validation:
- PIT universe coverage >= 95%
- Market context coverage >= 95%
- Sector mapping coverage >= 95% when Sector/RS is claimed
- Sector RS price coverage >= 95%
- Core Phase / Anti-Chase coverage >= 95%
- OOS rows explicitly tagged
- Outcome completeness >= 95%
- Cost model completeness = 100% for each tested cost scenario
- Leakage audit = PASS

Any failure => `DATA_BLOCKED`.

## 4. Required data domains

### Identity / timestamp
decision_id, run_id, strategy_id, strategy_version, symbol, exchange, session_date,
observation_timestamp, feature_cutoff_timestamp, decision_timestamp, timezone,
feature/rule/cost-model versions, research_split.

### PIT universe / governance
pit_universe_member, universe source/effective dates, data-quality status,
leakage status, replay coverage.

### Market / sector
market regime, index return, breadth, volatility,
effective-dated sector membership, sector return, sector RS, stock RS.

### 10 frozen rule outputs
market_gate, sector_rs_gate, multi_timeframe_gate, phase_gate, setup_gate,
trigger_gate, anti_chase_gate, rr_gate, opportunity_ranking_gate,
execution_adjustment_gate.

### Anti-Chase / phase / execution context
VWAP, VWAP slope, ATR, extension ATR, RVOL, session position, stop distance,
spread if available, planned entry/stop/targets, gross RR, fee/tax-adjusted RR,
execution-adjusted RR, slippage assumptions, liquidity penalty.

### Ranking context
candidate_pool_id, candidate_pool_size, rank_score, ranking_position,
ranking_decile, ranking_model_version.

### Outcome
net_r_045, net_r_065, MFE/MAE, R multiple, false breakout, missed entry,
fill/outcome type and completeness.

## 5. Delivery artifacts

W3 should provide:
1. Versioned dataset/schema contract.
2. Dataset builder/export pipeline.
3. PIT/leakage/coverage audit report.
4. Reproducible manifest with source, period, row count, symbol count and code version.
5. Validation command that can feed directly into:
   `research/w2_intraday_validation_runner.py`.
6. Data-gap report for any field below threshold.

## 6. W0 acceptance

W0 will accept the W3 handoff only when the dataset passes the W2 fail-closed validator.
Passing the data contract does **not** promote any rule to Production.
