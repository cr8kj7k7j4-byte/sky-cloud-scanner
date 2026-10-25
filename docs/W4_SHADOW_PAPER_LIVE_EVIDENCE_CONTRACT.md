# W4｜Sky Shadow / Paper / Live Evidence Contract

> Scope: evidence collection and validation only. W4 must not invent or develop new strategies.

## Canonical modules

- PMS
- P0-L
- P0-R
- P0-A
- P0-G

GitHub remains the Single Source of Truth.

## Required Shadow / Paper evidence

Each observation should preserve, when available:

- strategy_id
- strategy_version
- symbol
- observation_timestamp
- market_regime
- sector
- ranking_position
- rank_score
- phase
- setup
- trigger
- trigger_price
- assumed_entry
- max_acceptable_price
- stop
- target_1
- target_2
- P0-R decision
- risk_per_share
- data_quality
- forward_return
- MFE
- MAE
- R_multiple
- gross_return
- fee
- tax
- spread
- slippage / execution impact
- net_return
- exit_reason
- ambiguous_same_bar
- missing_data
- outcome_completeness

Unavailable evidence must remain null/unknown; it must not be inferred or fabricated.


## Eligible scan definition

A scheduled scanner workflow success is **not** automatically an eligible W4 observation source.

A scan run counts toward W4 pipeline collection only when:
- its Paper artifact is present;
- the artifact contains at least one valid record;
- the record observation timestamp is on/after the canonical ledger activation time;
- the record contains a non-empty symbol.

Therefore:
- market holidays;
- empty scans;
- zero-record artifacts;
- pre-ledger artifacts;
- malformed Paper files

do **not** count as eligible scan runs.

Machine audit:
- `research/w4_scan_artifact_eligibility.py`
- `research_output/w4_scan_eligibility.json`

This rule prevents weekday cron success on exchange holidays from inflating sample progress or producing false pipeline-failure signals.

## Shadow Sufficiency Gate

Promotion review is blocked until all are true:

- >= 200 evaluable observations
- >= 20 trading days
- >= 2 Market Regimes
- Outcome completeness >= 95%
- Single-symbol share <= 20%

Before all thresholds pass, canonical W4 status is:

`WAITING_FOR_FUTURE_SAMPLE`

A small but attractive sample must not be promoted early.

## Counterfactual outcome

Strategy Counterfactual Outcome is eligible only when:

- Monitor = TRIGGERED
- P0-R = ALLOW
- Trigger, Stop and Target are complete

Ranking Outcome may calculate forward return / MFE / MAE, but must never be described as an actual trade or realized PnL.

When the same K bar touches Stop and Target, apply the conservative ordering:

- Stop first
- `ambiguous_same_bar = true`

## Costs

Without complete costs, Gross / MFE / MAE may be retained, but complete Net PnL must not be claimed.

Minimum complete cost model:

- commission / fee
- transaction tax
- spread
- slippage / execution impact

## PMS hard rules

1. No averaging down.
2. No adding to losing positions.
3. Add only after favorable movement and a valid secondary trigger.
4. Stop cannot be widened.
5. Trailing stop may only reduce risk.
6. Exit when the original trade thesis fails.
7. After two consecutive stop-outs or daily loss reaches -2R, block new trades.

## Live validation

Before Production Live, compare:

Backtest vs Shadow vs Paper vs Small Live

Track at minimum:

- Expectancy delta
- PF delta
- Fill Rate
- Slippage
- Missed trades
- Rejected trades
- Data failure
- Operational error
- MAE
- MFE
- Max DD
- Execution latency

Small Live requires explicit W0 / P0-G approval and user-supplied:

- total capital
- 1R
- maximum position
- maximum acceptable daily loss

W4 must not decide position size without these inputs.

## Drift monitoring

Track:

- Expected vs realized
- PF deterioration
- Expectancy deterioration
- Win/Loss distribution shift
- MAE drift
- MFE drift
- Slippage drift
- Trigger rate drift
- Regime dependency
- Data quality drift

Material deterioration can move risk state to:

- CAUTION
- DEFENSIVE
- LOCKDOWN

## Canonical W4 report

Every W4 status output is organized as:

1. Sample Progress
2. Data Completeness
3. Strategy Performance
4. Risk
5. Drift
6. Promotion Readiness
7. Outstanding Days / Samples

Historical data may be used for backtest comparison, but must not be relabeled as new forward Shadow/Paper evidence.
