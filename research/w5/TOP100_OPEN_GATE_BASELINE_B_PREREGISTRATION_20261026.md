# W5 Preregistration — Top100 Velocity Baseline B / Open-Price Gate

Date: 2026-10-26
Status: PREREGISTERED_RESEARCH_CANDIDATE
Production impact: NONE

## Structural hypothesis

The user's original discretionary process monitored the strongest current-day gainers from the open and did not enter names that had fallen below the current trading day's opening price.

This experiment tests whether adding that open-price regime filter changes the economics of the already-frozen Top100 Velocity Baseline A.

## Frozen comparison

Everything from Baseline A remains unchanged except one additional causal gate:

> At the decision timestamp, the entry proxy / contemporaneous price must be strictly above the current trading day's 09:00 opening price.

### Unchanged rules
- 5-minute completed-bar data.
- Decision timestamps: 09:15, 09:30, 09:50, 10:15.
- Top100 by current-day return.
- Price <= TWD 100.
- Current-day return < 9.5% near-limit guard.
- Positive 5m price velocity.
- Positive 5m gain-rank velocity.
- Positive 5m volume acceleration.
- Equal-weight percentile score of price velocity / rank velocity / volume acceleration.
- Top3 new symbols per decision timestamp.
- Maximum one selected observation per symbol per day.
- Entry proxy: open of the 5-minute bar beginning at the decision timestamp.
- Exit: close after 60 minutes.
- Primary round-trip cost: 0.45%.
- Stress cost: 0.65%.

## New rule only

- daily_open = open of the 09:00 five-minute bar for that trading day.
- Entry is eligible only if entry_price > daily_open.
- No tolerance band.
- No distance-from-open optimization.
- No alternate Top-N or holding-period search.

## Decision

This is treated as a structural entry-regime hypothesis, not a rescue by threshold tuning.

If Baseline B still has negative after-cost expectancy / PF < 1 across time folds, it will be rejected and frozen without local retuning.

If it materially improves, it remains research-only and must still pass walk-forward / regime / portfolio / Shadow-Paper / P0-R / P0-G gates.