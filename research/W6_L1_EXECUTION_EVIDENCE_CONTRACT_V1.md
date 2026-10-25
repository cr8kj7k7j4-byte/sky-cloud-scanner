# W6｜L1 Execution Evidence Contract V1

- Date: 2026-10-25
- Workstream: W6｜Sky Execution & Market Microstructure Lab
- Scope: research evidence only
- Production impact: NONE
- Governing baseline: Sky V2.1 frozen Production
- Status: FORWARD_COLLECTION_READY

## Purpose

建立 W6 第一層可驗證 execution evidence，先解決 P1 Spread + Slippage Baseline，再進入 Aggressive/Passive、Fill Probability 與 Adverse Selection。

本契約只接受 decision-time 可觀察到的 L1 quote / execution evidence；不得由 OHLC K 棒反推完整 order book。

## Row grain

一列固定代表：

`one symbol × one observation_timestamp × one execution attempt`

同一 Trigger 可以建立多個 counterfactual execution arm，但任何未實際成交的 arm 不得標示為 FILLED。

## Required identity

- decision_id
- run_id
- strategy_id
- strategy_version
- symbol
- exchange
- observation_timestamp
- trigger_timestamp
- execution_attempt_timestamp
- data_timezone
- execution_type
- cost_model_version
- source
- research_only=true

## L1 quote fields

- bid
- ask
- bid_size when available
- ask_size when available
- quote_timestamp
- quote_source
- quote_age_ms when available
- quote_sequence_id when available

Derived:
- spread_abs
- spread_bps
- midquote_reference

Midquote is a reference only. It is never assumed executable.

## Execution attempt fields

- reference_price
- trigger_price
- requested_price
- max_chase_price
- order_style
- urgency
- fill_status
- fill_price
- fill_timestamp
- filled_shares
- requested_shares
- cancel_timestamp
- cancel_reason

Allowed fill_status:
- FILLED
- PARTIAL
- MISSED
- CANCELLED
- REJECTED
- UNKNOWN

Rules:
1. FILLED/PARTIAL requires fill_price.
2. MISSED/CANCELLED/REJECTED must not carry an invented fill_price.
3. Future quote cannot determine whether an earlier passive order was fillable unless sequencing evidence exists.
4. Trigger price is not a fill price.
5. Midpoint is not a fill price.

## P1 derived metrics

- absolute_slippage
- entry_slippage_bps
- exit_slippage_bps
- slippage_r
- spread_bps
- spread_to_price
- spread_to_volatility when volatility input is PIT-valid
- fill_rate
- missed_trade_rate

## Adverse Selection

For an actual/paper fill, preserve post-fill point-in-time prices at:
- +1 minute
- +3 minutes
- +5 minutes

For long entry:
`signed_forward_return = future_price / fill_price - 1`

Adverse selection flag:
`signed_forward_return < 0`

Do not calculate adverse-selection from a fictional fill.

## Fixed slices

Time:
- 09:00–09:05
- 09:05–09:15
- 09:15–09:30
- 09:30–09:50
- 09:50–10:15
- 10:15+

Price:
- <20
- 20–50
- 50–100
- >100 research-only

Execution type:
- AGGRESSIVE_MARKETABLE
- AGGRESSIVE_LIMIT
- PASSIVE_LIMIT
- PULLBACK_LIMIT
- BREAKOUT_CONFIRMATION
- BREAKOUT_RETEST
- VWAP_RETEST

## P1 minimum evidence

Before declaring a stable Spread/Slippage Baseline:
- preserve raw sample count;
- report null coverage separately;
- do not merge actual and counterfactual fills;
- stratify by time bucket and price bucket;
- report distribution, not only mean;
- explicitly report sample insufficiency.

W6 research status remains HOLD / INSUFFICIENT_DATA until observed evidence exists.

## Historical L2 / Order Book gate

Current status:
`INSUFFICIENT_MICROSTRUCTURE_DATA`

L2 work cannot begin until source, timestamp precision, sequencing, dropped-message handling, replay capability and look-ahead protection are verified.

Therefore P6/P7 (Order Flow Imbalance / Microprice / Book Pressure) remain blocked from empirical promotion.

## Integration

- P0-X remains the existing cost/RR engine.
- P0-L remains the canonical decision/trade ledger.
- W6 forward evidence may feed execution calibration and W4 Shadow/Paper.
- W4 validates fill/slippage assumptions against paper/live evidence.
- W2 owns directional Trigger alpha.
- W0/P0-G alone decides promotion.

## Initial status

P1 Spread + Slippage Baseline: HOLD — forward observed samples required.
P2 Aggressive vs Passive: HOLD — depends on P1 collection.
P3 Pullback vs Breakout Chase: HOLD — depends on P1/P2.
P4 Fill Probability: HOLD — fill/miss labels required.
P5 Adverse Selection: HOLD — actual/paper fills required.
P6 Order Flow Imbalance: INSUFFICIENT_DATA.
P7 Microprice / Book Pressure: INSUFFICIENT_DATA.
P8 Execution Router: HOLD — may only be built after validated upstream evidence.
