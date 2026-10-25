# W2｜Intraday Point-in-Time Replay Contract V1.0

- Workstream: W2｜Sky 當沖驗證實驗室
- Date: 2026-10-25
- Production Baseline: Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP
- Status: RESEARCH CONTRACT / FAIL-CLOSED
- Production impact: NONE

## 1. Purpose

建立唯一可用於 Day Trading Full Model、Remove-One Ablation、Walk-forward、
Regime Stability、Cost Stress 與 Ranking Decile 驗證的歷史決策重播資料契約。

此表不是成交簿，也不是 Paper / Live ledger。它是一張「在每個 decision timestamp
實際可觀察到什麼」的 point-in-time candidate table，之後才與 P0-L outcome join。

核心順序：

Market
→ Sector / Relative Strength
→ Stock Quality
→ Multi-timeframe
→ Phase
→ Setup
→ Trigger
→ Anti-Chase
→ RR Gate
→ P0-O Ranking
→ P0-R Risk Gate
→ Execution
→ PMS

## 2. Row Grain

每一列固定代表：

`one symbol × one observation_timestamp × one candidate decision`

同一股票同一天可有多列，但每列必須有唯一 `decision_id`。

建議唯一鍵：

`strategy_id + strategy_version + symbol + observation_timestamp + run_id`

## 3. Mandatory Identity / Timestamp Fields

- decision_id
- run_id
- strategy_id
- strategy_version
- symbol
- exchange
- session_date
- observation_timestamp
- feature_cutoff_timestamp
- decision_timestamp
- data_timezone
- feature_schema_version
- rule_schema_version
- cost_model_version

Rules:

1. Timestamp 必須為 Asia/Taipei 或 timezone-aware。
2. `feature_cutoff_timestamp <= decision_timestamp`。
3. outcome timestamp 必須晚於或等於 decision timestamp。
4. 任何 feature 不得使用 decision timestamp 之後資料。
5. 已知 current-only 欄位不得歷史回填成 PIT evidence。

## 4. Mandatory Data Governance Fields

- pit_universe_member
- universe_source
- universe_effective_from
- universe_effective_to
- data_quality_status
- leakage_audit_status
- sector_mapping_status
- market_context_status
- execution_context_status
- replay_coverage_status

Allowed status:
- OK
- MISSING
- UNKNOWN
- BLOCKED

Promotion-grade replay 只接受 mandatory context coverage >= 95% 且 leakage audit PASS。

## 5. Canonical 10 Rule Columns

每列必須保留 Full Model 10 條 Rule 的布林結果：

1. `market_gate`
2. `sector_rs_gate`
3. `multi_timeframe_gate`
4. `phase_gate`
5. `setup_gate`
6. `trigger_gate`
7. `anti_chase_gate`
8. `rr_gate`
9. `opportunity_ranking_gate`
10. `execution_adjustment_gate`

重要：

- Gate 必須由 frozen rule definition 產生。
- Remove-One Ablation 只關閉 Gate；不得重新計算新的最佳 threshold。
- `opportunity_ranking_gate` 必須保留原 candidate pool 與 rank context，不能只保存最後 Top N。
- `execution_adjustment_gate` 必須使用 decision-time 可得的 execution assumptions，不得套用事後最佳滑價。

## 6. Market / Sector / Stock Context

Mandatory where claimed:

### Market
- market_regime
- market_return
- market_breadth
- market_volatility

### Sector / RS
- sector
- sector_effective_from
- sector_effective_to
- sector_return
- sector_rs_vs_market
- stock_rs_vs_sector

### Stock Quality / Liquidity
- price
- volume
- turnover_twd
- liquidity_bucket
- spread_bps
- spread_bucket

Current-only sector mapping 不得用於歷史日期。

## 7. Multi-timeframe / Phase / Setup / Trigger

Recommended mandatory replay fields:

- mtf_short_state
- mtf_mid_state
- mtf_long_state
- phase
- setup_id
- trigger_id
- trigger_price
- trigger_timestamp
- trigger_quality
- false_breakout_definition_version

若某 Rule 在 Production 依賴特定欄位，該欄位即升格為 mandatory。

## 8. Anti-Chase / Entry Quality

Core fields:

- entry_reference_price
- cumulative_vwap
- price_vs_vwap_pct
- vwap_slope
- day_return_pct
- gap_pct
- atr14
- price_extension_atr
- breakout_bar_atr
- rvol
- volume_zscore
- session_low_at_decision
- session_high_at_decision
- session_position
- resistance_distance_pct
- stop_distance_pct
- stop_distance_atr
- spread_bps

Historical bid/ask spread unavailable時：
- `spread_bps = null`
- `execution_context_status = MISSING/BLOCKED`
- 不得以 0 代替。

Rejected trigger-slip proxy 不得重新作為 standalone Anti-Chase hard gate。

## 9. RR / Execution Fields

- planned_entry
- planned_stop
- planned_target_1
- planned_target_2
- gross_rr
- fee_tax_adjusted_rr
- execution_adjusted_rr
- fill_probability
- expected_entry_slippage_bps
- expected_exit_slippage_bps
- expected_spread_bps
- liquidity_penalty_bps

Cost scenarios required:

- `net_r_045`: 0.45% primary round-trip cost
- `net_r_065`: 0.65% stress round-trip cost

不得使用 `gross_rr` 冒充 Net RR。

## 10. Opportunity Ranking Fields

- candidate_pool_id
- candidate_pool_size
- rank_score
- ranking_position
- ranking_decile
- ranking_model_version

Ranking 必須對「同一 decision timestamp 的完整合格候選池」計算。

不得事後只保存 winners，再反推 ranking effectiveness。

## 11. P0-R / Capacity / Concentration

Research replay至少保留：

- risk_gate
- one_r_twd (若使用者/研究設定存在)
- planned_position_shares
- planned_notional_twd
- portfolio_heat_before
- concurrent_positions_before
- sector_exposure_before
- symbol_exposure_before
- capacity_estimate_twd
- capacity_bucket

若 1R/portfolio state 歷史不可重建，必須標記 UNKNOWN，不得編造。

## 12. Outcome Join Fields

Outcome 只能在 feature freeze 後 join：

- outcome_status
- fill_status
- actual_entry
- actual_exit
- actual_entry_slippage_bps
- actual_exit_slippage_bps
- fees_twd
- tax_twd
- gross_pnl_twd
- net_pnl_twd
- r_multiple
- mae_r
- mfe_r
- holding_minutes
- false_breakout
- missed_entry
- exit_reason

Counterfactual rows must additionally include:
- `outcome_type = COUNTERFACTUAL`

Actual / Paper / Shadow:
- `outcome_type = ACTUAL | PAPER | SHADOW`

Counterfactual 不得稱為實際成交。

## 13. Full Model / Ablation Metrics

每個策略、成本情境、fold、regime、slice 至少輸出：

- n
- Win Rate
- Avg Win
- Avg Loss
- Expectancy
- PF
- Max DD
- MAE
- MFE
- R Multiple
- Trigger frequency
- False breakout rate
- Missed entry rate
- Slippage sensitivity
- Cost-adjusted return
- Fold stability
- Regime stability

每條 Rule additionally:

- Expectancy Contribution
- PF Contribution
- Drawdown Protection
- Sample Reduction

## 14. Fixed Validation Dimensions

1. OOS
2. Walk-forward
3. Market Regime
4. Time-of-day
5. Liquidity
6. Spread
7. Slippage
8. Trigger Quality
9. False Breakout
10. Missed Entry
11. Execution-adjusted RR
12. Ranking decile
13. Capacity
14. Sector concentration
15. Single-symbol concentration

Slice analysis is diagnostic only. It may not be used for post-hoc subgroup cherry-picking.

## 15. Coverage Gate

Full 10-rule Day Trading Ablation may start only when:

- PIT Universe coverage >= 95%
- Market context coverage >= 95%
- Sector mapping coverage >= 95% when Sector/RS is claimed
- Sector RS price coverage >= 95%
- Core Phase / Anti-Chase coverage >= 95%
- Outcome completeness >= 95%
- Cost model completeness = 100% for tested cost scenario
- Leakage audit = PASS

If any mandatory gate fails:

`DATA_BLOCKED`

No Full Model expectancy or Rule Contribution may be reported as validated evidence.

## 16. Research Governance

Research Freeze Registry has priority.

`ARCHIVED_NO_RETUNE` families may not be revived by:
- threshold search
- Top N search
- stop / target changes
- indicator period changes
- feature weight changes

Re-open requires structural preregistration:
- new target
- new label
- new horizon
- new dataset architecture
- new execution architecture
- new market-neutral / residual framework
- new point-in-time evidence

## 17. W2 Final Status Vocabulary

W2 may output only:
- PROMOTE_CANDIDATE
- HOLD
- REJECT
- ARCHIVE

`PROMOTE_CANDIDATE` means send to W0/P0-G review only.
It does not authorize Production promotion.
