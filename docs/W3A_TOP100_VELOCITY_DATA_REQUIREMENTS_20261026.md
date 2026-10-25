# W3A Data Requirements — Top100 Velocity Research

Date: 2026-10-26
Priority: tied to current intraday PIT historical coverage blocker

## Objective
Enable causal reconstruction of the intraday rolling Top100 gainers universe for Taiwan equities.

## Minimum historical fields per symbol / timestamp
- symbol
- exchange
- observation_timestamp
- prior_close
- last_price or bar close
- intraday high / low where available
- cumulative volume
- interval volume
- bid / ask or spread fields where historically available
- trading status / suspension / limit state
- point-in-time listing membership

## Derived causal fields
- intraday_return_t = price_t / prior_close - 1
- gain_rank_t across the eligible full market at timestamp t
- top100_member_t
- price_velocity
- rank_velocity
- volume_acceleration

## Non-negotiable requirements
- no end-of-day ranking backfill;
- timestamp causality;
- point-in-time universe membership;
- historical delisted / newly listed handling;
- synchronized cross-sectional snapshots;
- >=95% governed universe coverage for promotion-grade claims;
- data-quality flags and provenance retained.

## Preferred resolution path
1. Reuse current official/PIT universe contract.
2. Identify a source that can provide broad-universe synchronized intraday history.
3. Produce source/licensing/cost/coverage evidence before purchase.
4. Build the smallest reproducible sample that proves causal Top100 reconstruction.
5. Scale only after data contract passes validation.

No purchase is authorized by this document. If paid data is required, stop at a comparison of vendor, coverage, license, and price for user approval.
