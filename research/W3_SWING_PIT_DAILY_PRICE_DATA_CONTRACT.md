# W3｜Sky Swing Canonical PIT Historical Daily Price Data Contract v1.0

Status: W3 implementation contract for W1 data blocker handoff  
Research strategy ownership: W1  
Trading strategy changes: NONE

## 1. Purpose

Provide the canonical 2023-01-01+ daily adjusted OHLCV dataset required by:

- research/W1_SWING_DATA_BLOCKER_HANDOFF_TO_W3_20261025.md
- research/SKY_SWING_CANONICAL_PIT_REPLAY_PREREGISTRATION.md
- research/validate_swing_pit_readiness.py

This work unlocks data readiness only. It does not promote, retune or modify Sky Swing.

## 2. Membership source

The sole historical membership authority is the canonical pit_intervals.json emitted by:

research/audit_historical_universe.py

Current-listing samples are forbidden as promotion-grade historical universes.

Per-date rule:
listed_from <= D <= listed_to, with listed_to open-ended when null.

TWSE/TPEx market transfers remain separate intervals. Exchange is resolved per bar date.

## 3. Price source

Primary governed price source:

FinMind dataset: TaiwanStockPriceAdj

Reason:
- TWSE + TPEx daily OHLCV
- 1994-10-01 onward
- free individual-symbol queries
- explicit adjusted-price dataset
- current FinMind documentation states adjusted-history corrections include ex-right/ex-dividend holiday shifts, capital reductions and combined corporate-action cases

Sky does not infer unknown corporate actions.

## 4. Canonical bar schema

Each daily bar preserves:

- symbol
- exchange
- date
- trading_date
- open
- high
- low
- close
- volume
- turnover when available
- source
- source_as_of
- retrieved_at
- adjusted
- adjustment_method
- listed_from
- listed_to

File envelope also retains:
- schema_version
- symbol
- source
- retrieved_at
- adjusted
- adjustment_method
- sha256

## 5. Missing-data policy

Forbidden:
- forward-fill over unlisted periods
- forward-fill over delisted periods
- forward-fill over suspensions
- synthetic replacement of missing historical names with current names
- silent cross-market splicing

A missing eligible bar stays missing and appears in the coverage audit.

## 6. Corporate actions

Canonical research consumes adjusted OHLC from TaiwanStockPriceAdj.

Policy:
- adjustment is source-provided, not reverse-engineered by Sky
- raw official exchange data may be used for spot verification
- unknown/unresolved corporate actions fail closed
- market-transfer continuity is governed independently by pit_intervals.json

## 7. Parallel retrieval

The GitHub workflow shards canonical symbols across multiple runners so that free per-symbol API rate limits are not exceeded by a single runner.

Optional FINMIND_TOKEN may raise quota but is not required by the contract.

## 8. Acceptance gates

Mandatory:
- canonical PIT gate PASS
- interval validation PASS
- adjusted=true on all accepted bars
- zero duplicate symbol/exchange/date rows
- zero unresolved continuity conflicts
- all registered audit dates >=95% price-history coverage
- no current-universe substitution
- no forward fill
- research/validate_swing_pit_readiness.py returns READY_FOR_CANONICAL_SWING_REPLAY

Coverage PASS is data readiness, not profitability evidence.
