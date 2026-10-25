# W6 → W3 Handoff｜L1 Forward Execution Collection — 2026-10-25

## Purpose

W6 P1 Spread + Slippage Baseline is blocked by lack of sufficient observed point-in-time L1/fill evidence.
W3 is requested to provide a forward-collection path only. This does not change Production trading behavior.

## Required observation grain

`one symbol × one observation_timestamp × one execution attempt`

## Minimum fields

Identity:
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

Quote:
- bid
- ask
- bid_size if available
- ask_size if available
- quote_timestamp
- quote_source
- quote_age_ms if available
- quote_sequence_id if available

Plan:
- trigger_price
- reference_price
- requested_price
- max_chase_price
- execution_type
- requested_shares
- risk_per_share

Execution result:
- fill_status
- fill_price
- fill_timestamp
- filled_shares
- cancel_timestamp
- cancel_reason

Post-fill observation:
- future_price_1m
- future_price_3m
- future_price_5m

Context:
- session_date
- liquidity_bucket if PIT-valid
- volume / turnover when PIT-valid
- spread_bps
- cost_model_version
- research_only=true

## Fail-closed rules

1. Missing bid/ask => spread remains NULL.
2. Missing fill evidence => fill_status UNKNOWN, never infer FILLED.
3. Trigger price or midpoint cannot be substituted for fill price.
4. Future quotes cannot establish earlier passive fillability without sequencing evidence.
5. No OHLC-derived fake order-book data.
6. Preserve source timestamp separately from ingestion timestamp when possible.
7. Any dropped-message or stale-quote condition must be explicitly flagged.

## Integration target

Research consumer:
`research/w6_execution_baseline.py`

Evidence contract:
`research/W6_L1_EXECUTION_EVIDENCE_CONTRACT_V1.md`

Canonical downstream:
- P0-L decision/trade ledger
- W4 Shadow/Paper validation
- W6 P1/P2/P4/P5 research

## Acceptance gate

W6 may start P1 empirical baseline only after:
- point-in-time quote timestamps are verified;
- actual/paper fill status is explicit;
- null/missing evidence is preserved;
- source/ingest timestamp policy is documented.

L2/order-book collection is a separate future gate and is not required to start P1.
