# W4｜Sky Research / Forward Evidence Contract (current)

> **Owner override 2026-11-21:** Dedicated simulated-trading Paper/Shadow ledgers, simulated fills/positions/PnL, replay and related acceptance dependencies are permanently retired under [owner directive](SKY_PAPER_LEDGER_PERMANENT_REMOVAL_20261121.md). Historical wording below is updated for forward **research observations only**. Do not restore retired workflows or treat a research observation as a fill.

> Scope: evidence collection and validation only. W4 must not invent or develop new strategies.

## Canonical modules

- PMS
- P0-L
- P0-R
- P0-A
- P0-G

GitHub remains the Single Source of Truth.


## Forward evidence version lineage

Every new independently retained forward **research-observation** record must preserve separate identities for:

- `strategy_id`: Production strategy identity.
- `strategy_version`: W0/P0-G governed Production baseline.
- `system_version`: Sky operating-system architecture version.
- `scanner_version`: forward collector/scanner implementation version.
- `historical_full_rule_replay_status`: historical provenance status.

Current governed values:
- strategy_id: `Sky Day Trading`
- strategy_version: `v1.4 Dynamic Capital Rotation / P0-C MVP`
- system_version: `Sky V2.1`
- scanner_version: `0.5`
- historical_full_rule_replay_status: `HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE`

The strategy version identifies the current formal Production baseline. It does **not**
mean the missing historical v1.4 full-rule implementation has been reconstructed.

The scanner version identifies the software collector producing forward evidence and
must never replace or be confused with the Production strategy version.

## Required forward research observations

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
- observed_market_price (source and timestamp required when present)
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


## Eligible forward research scan definition

A successful GitHub Actions job or a schedule-time match **does not** by itself make a scan an eligible W4 observation. The retained evidence must instead contain:

1. A completed GitHub run ID, matching exact head SHA and a verified **same-run Artifact** or independently immutable source; an on-demand invocation is not a scheduled run.
2. A non-empty **research observation** with a valid symbol, source identity, trade date and **timezone-aware** observation/source timestamp; a reference price, snapshot capture time and executed-trade time must never be conflated.
3. Data-quality and causal checks appropriate to the signal, with explicit non-trading, non-Production flags. Missing evidence fails closed and remains ineligible.
4. An independently verifiable source/record linkage. A legacy simulated Paper artifact or counterfactual fill **must not** count as qualifying evidence.

No eligible scan is inferred from holidays, empty or malformed results, a missing Artifact, zero rows, mismatched run/SHA, stale or naive timestamps, or a mere successful workflow. Distinguish `WAITING_FOR_FIRST_ELIGIBLE_SCAN` from data/system failure; neither counts toward sample sufficiency.

**Current reusable checks** (do not duplicate them):
- `research/schedule_health.py`: provisional five-slot/55-slot schedule diagnostics; clock matching is **not** cron certification.
- `research/sky_512_artifact_validate.py`: strict 5m source/time/run/SHA readback.
- `scripts/sky_chat_artifact_readback.py`: independent phone result and same-run Artifact readback.
- `src/w4_evidence_integrity.py`: conservative research-observation/provenance counters; not trading authorization.

**Retired/legacy-only**: `research/w4_scan_artifact_eligibility.py` and `research_output/w4_scan_eligibility.json` use the former `shadow_history/output/paper` layout. They are **not** a current acceptance gate and must not be run to manufacture forward evidence. Remove/refactor only after full caller and evidence-preservation review under W0 Issue #363. Do not revive their source format.

## Forward research sufficiency gate

Promotion review is blocked until all are true:

- >= 200 evaluable observations
- >= 20 trading days
- >= 2 Market Regimes
- Outcome completeness >= 95%
- Single-symbol share <= 20%

Before all thresholds pass, canonical W4 status is:

`WAITING_FOR_FUTURE_SAMPLE`

A small but attractive sample must not be promoted early.

## Non-execution research outcome

A prospective **research-only** outcome may be evaluated only under its frozen, independently verified data and strategy assumptions when:

- Monitor = TRIGGERED
- P0-R = ALLOW
- Trigger, Stop and Target are complete

Ranking observations may retain verifiable forward markouts / MFE / MAE. No simulated order, fill, portfolio, event replay or modelled PnL ledger may be created or used as an acceptance gate. Research markouts must never be described as actual trades or realized PnL.

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

Before any authorized Production change, compare **historical exploration** with independently timestamped, immutable **forward research observations** and (only if separately authorized and actually available) broker-sourced executions. Do not use retired Shadow/Paper trading ledgers.

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

Any separately proposed live execution requires explicit user authorization and W0 / P0-G approval, with verified:

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

Historical data may be used for exploratory comparison, but must never be relabeled as new independent prospective evidence. No automatic order, simulated ledger, or unreviewed Production promotion is authorized.
