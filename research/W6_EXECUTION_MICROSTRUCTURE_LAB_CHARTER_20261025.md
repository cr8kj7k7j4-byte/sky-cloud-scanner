# W6｜Sky Execution & Market Microstructure Lab — Charter

- Date: 2026-10-25
- Scope: Research / Execution Evidence Only
- Production impact: NONE
- Governance status: PROPOSED_FOR_W0_REGISTRATION
- GitHub Single Source of Truth applies.

## Mission

W6 does not decide directional alpha. W2 answers whether a Trigger has alpha; W6 answers how the same Trigger should be executed to improve after-cost expectancy without fabricating fills.

Primary objectives:
1. Reduce slippage.
2. Reduce spread cost.
3. Reduce chase execution.
4. Reduce adverse selection.
5. Improve effective fill quality.
6. Improve execution-adjusted RR.
7. Reduce Backtest → Paper → Live execution drift.

## Allowed scope

- Execution Alpha
- Market Microstructure
- Order Flow
- Bid/Ask Spread
- Slippage
- Fill Quality
- Aggressive / Passive Execution
- Order Book
- Adverse Selection
- Intraday Liquidity
- Execution-adjusted RR

W6 must not:
- create a directional alpha strategy;
- modify Production stop/target rules;
- change Sky Production directly;
- treat low slippage as equivalent to high profitability;
- ignore missed trades or opportunity cost;
- assume trigger-price fills;
- use midpoint as automatically executable;
- use future quotes;
- simulate L2/order-book evidence from OHLC bars.

## Governance dependencies

Read before research:
- SKY_SYSTEM_REGISTRY_V2_1.md
- research/RESEARCH_FREEZE_REGISTRY.md
- docs/SKY_VALIDATION_PROTOCOL_V1_0.md
- docs/SKY_V2_1_BASELINE_FREEZE_20261025.md
- docs/SKY_MASTER_CONTROL_STATUS_20261025.md
- docs/SKY_PARALLEL_WORKSTREAMS.md
- research/P0L_CANONICAL_LEDGER_CONTRACT.md
- research/INTRADAY_PIT_REPLAY_CONTRACT_V1.md
- docs/W4_SHADOW_PAPER_LIVE_EVIDENCE_CONTRACT.md
- P0-X / P0-R / P0-L / PMS implementation

## Research priority

P1 Spread + Slippage Baseline
P2 Aggressive vs Passive Entry
P3 Pullback vs Breakout Chase
P4 Fill Probability
P5 Adverse Selection
P6 Order Flow Imbalance
P7 Microprice / Book Pressure
P8 Execution Router

## Time slices

- 09:00–09:05
- 09:05–09:15
- 09:15–09:30
- 09:30–09:50
- 09:50–10:15
- 10:15+

Formal Sky scan times remain:
09:05, 09:15, 09:30, 09:50, 10:15.

## Price slices

- <20
- 20–50
- 50–100
- >100 research-only for the existing new-entry universe

## Execution-adjusted RR

Raw RR
→ Fee-adjusted RR
→ Tax-adjusted RR
→ Spread-adjusted RR
→ Slippage-adjusted RR
→ Fill-probability-adjusted RR
→ Execution-adjusted Net RR

No idealized fill may be used merely to pass an RR gate.

## A/B execution families

A. Immediate aggressive / marketable execution
B. Trigger then pullback
C. Passive limit
D. Breakout + confirmation
E. Breakout + VWAP / structural retest

Compare at minimum:
- Fill Rate
- Missed Trade Rate
- Avg Entry Improvement
- Spread
- Slippage
- Slippage in R
- MAE
- MFE
- Expectancy
- PF
- Max DD
- Net R
- Adverse Selection

## Adverse selection horizons

Measure post-fill signed return at:
- 1 minute
- 3 minutes
- 5 minutes

Do not infer actual fill if the order was not filled.

## Microstructure data gate

Before any L1/L2/tick/order-book claim, verify:
1. source;
2. timestamp precision;
3. point-in-time bid/ask;
4. snapshot/update sequencing;
5. dropped-message handling;
6. historical replay capability;
7. look-ahead protection;
8. forward-only limitations.

If insufficient, status:
INSUFFICIENT_MICROSTRUCTURE_DATA

OHLC/K bars may not substitute for full order-book evidence.

## W2 / W4 handoff

W2 owns Trigger alpha validation.
W6 owns execution hypothesis, metrics, slippage model, fill model.
W4 validates research assumptions against Shadow / Paper / Small Live evidence.

Any execution improvement is only:
EXECUTION_CANDIDATE

It must return to W0/P0-G for governance and W2/W4 validation as applicable.

## Required W6 output

- Candidate
- Execution Type
- Data Source
- Sample
- Fill Rate
- Missed Trade Rate
- Avg Spread
- Avg Slippage
- Slippage R
- MAE
- MFE
- Expectancy
- PF
- Max DD
- Adverse Selection
- Time-of-day Stability
- Liquidity Stability
- Main Risk
- Status

Allowed Status:
- EXECUTION_CANDIDATE
- HOLD
- REJECT
- INSUFFICIENT_DATA
- ARCHIVE

## Current bootstrap finding

Existing main already contains execution-aware research hooks:
- W2 Intraday PIT Replay Contract includes execution_adjustment_gate, execution_adjusted_rr, fill_probability, expected slippage/spread and liquidity fields.
- W4 evidence contract requires spread, slippage/execution impact, Fill Rate and Missed trades.
- P0-L canonical TradeDecisionRecord preserves a generic execution object and quote bid/ask fields.
- TradeRecord currently stores slippage as a single aggregate field.
- Shadow outcome currently uses TRIGGER_PRICE_COUNTERFACTUAL and explicitly is not an actual-fill record.

Initial gap:
there is no dedicated canonical W6 Execution Router, fill-probability model, adverse-selection model, or verified historical L1/L2 replay contract yet.

Therefore microstructure claims requiring historical order-book evidence remain:
INSUFFICIENT_MICROSTRUCTURE_DATA

Next executable path:
build forward-collectable L1 execution evidence and an execution ledger/schema first, then validate P1 Spread + Slippage Baseline before attempting L2/order-flow features.
