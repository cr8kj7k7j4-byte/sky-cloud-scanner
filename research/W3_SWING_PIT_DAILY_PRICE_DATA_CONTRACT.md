# W3｜Sky Swing Canonical PIT Historical Daily Price Data Contract v1.1

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

Historical membership is pinned to the last verified canonical main artifact:
- Historical Universe workflow run: 40193567617
- Artifact: historical-universe-audit-40193567617
- Canonical intervals: 2,116
- Historical Universe Gate: PASS
- Interval validation: PASS

The sole historical membership authority is canonical pit_intervals.json.
Current-listing samples are forbidden as promotion-grade historical universes.

Per-date rule:
listed_from <= D <= listed_to, with listed_to open-ended when null.

TWSE/TPEx market transfers remain separate intervals. Exchange is resolved per bar date.

## 3. Price source

Primary governed price source:
- FinMind TaiwanStockPrice — raw daily OHLCV
- FinMind TaiwanStockDividendResult
- FinMind TaiwanStockCapitalReductionReferencePrice
- FinMind TaiwanStockSplitPrice
- FinMind TaiwanStockParValueChange

The paid TaiwanStockPriceAdj dataset is NOT required by this implementation.

## 4. Adjustment method

Method id: SKY_BACKWARD_REFERENCE_RATIO_V1

For an event effective on date E:
- ex-right/dividend ratio = reference_price / before_price
- capital reduction ratio = PostReductionReferencePrice / ClosingPriceonTheLastTradingDay
- stock split ratio = after_price / before_price
- par-value change ratio = after_ref_close / before_close

The canonical stored bar remains raw PIT OHLCV.

W1 materializes an adjusted view through src/pit_adjusted_price.py at each evaluation as_of date A:
- only events with bar_date < event_date <= A are applied;
- events after A are ignored;
- the event-date bar itself is not adjusted by its own event.

This prevents a 2026 split/dividend from changing a 2023 contemporaneous absolute-price rule such as the < TWD 100 entry eligibility.

Fail-closed rules:
- missing/invalid reference prices are recorded as corporate-action data-quality issues;
- two or more distinct corporate-action datasets on the same symbol/date create CORPORATE_ACTION_CONFLICT and the symbol is quarantined rather than blindly multiplying factors;
- unknown corporate actions are never inferred.

Volume and turnover remain raw and are marked volume_adjusted=false.

## 5. Canonical bar schema

Each daily bar preserves:
- symbol
- exchange
- date
- trading_date
- open / high / low / close (raw PIT price)
- adjustment_capability=PIT_ASOF_EVENT_LEDGER
- volume
- turnover when available
- source
- source_as_of
- retrieved_at
- adjusted=false on stored raw bar
- volume_adjusted=false
- adjustment_method
- listed_from / listed_to

File envelope retains:
- schema_version
- symbol
- source
- retrieved_at
- adjusted=false
- adjustment_capability=PIT_ASOF_EVENT_LEDGER
- volume_adjusted
- adjustment_method
- corporate_action_events
- sha256

## 6. Missing-data policy

Forbidden:
- forward-fill over unlisted periods;
- forward-fill over delisted periods;
- forward-fill over suspensions/no-trade days;
- synthetic replacement of historical names with current names;
- silent cross-market splicing.

Raw OHLC rows with zero/non-positive prices are omitted and remain explicit missingness. A missing eligible bar stays missing and is audited.

## 7. Retrieval / quota architecture

The workflow uses 40 symbol shards with max-parallel=8.

At approximately 2,073 canonical symbols this is about 52 symbols per shard. Maximum planned requests are about:
- per-symbol: raw price + dividend result + capital reduction = 3 × ~52
- per-shard global: split + par-value change = 2
- total ≈ 158 requests per runner.

This remains below the documented unauthenticated FinMind hourly request ceiling while also supporting an optional FINMIND_TOKEN when available. Global split/par-value tables are grouped by stock_id before any symbol adjustment is constructed.

Provider 402/429 errors fail fast; invalid entitlement/quota errors are not retried across every symbol.

## 8. Acceptance gates

Mandatory:
- pinned canonical PIT gate PASS;
- interval validation PASS;
- every accepted symbol payload has PIT_ASOF_EVENT_LEDGER adjustment capability;
- zero duplicate symbol/exchange/date rows;
- zero unresolved continuity conflicts;
- corporate-action conflicts quarantined and disclosed;
- all registered audit dates >=95% price-history coverage;
- no current-universe substitution;
- no forward fill;
- research/validate_swing_pit_readiness.py returns READY_FOR_CANONICAL_SWING_REPLAY.

Coverage PASS is data readiness, not profitability evidence.


## 9. PIT causality of adjusted prices

Latest-vintage adjusted prices are not used directly as historical decision prices.

Reason: a later corporate action can retrospectively change earlier adjusted levels. Using that later-adjusted level in an earlier absolute-price rule or threshold would introduce look-ahead.

Canonical use:
1. stored OHLCV = raw contemporaneous daily market data;
2. corporate_action_events = governed event ledger;
3. src/pit_adjusted_price.py = as-of materializer;
4. technical-history views may be adjusted only with events effective on/before the historical as_of date;
5. current-day raw close remains the contemporaneous price for absolute price eligibility.

No missing bar is created during adjustment.
