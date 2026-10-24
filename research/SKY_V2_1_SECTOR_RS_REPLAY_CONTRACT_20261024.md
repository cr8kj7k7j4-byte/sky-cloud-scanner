# Sky V2.1 Sector Relative Strength Historical Replay Contract

- Date: 2026-10-24
- Status: DATA CONTRACT + RESEARCH INFRASTRUCTURE
- Production status: NOT ELIGIBLE

## Why no expectancy result is reported yet

The current 1,161-trade ledgers contain stock-level entry/exit/risk outcomes but do **not** contain:

- point-in-time sector membership
- sector benchmark price history
- sector return at each trade entry date
- stock lookback return vs sector at each entry date

Therefore a real Sector RS ablation cannot be computed without reconstructing contemporaneous data. Using current sector membership alone, or using future realized trade returns to infer a strong sector, would introduce survivorship / look-ahead bias.

## New replay module

`src/sector_rs_replay.py` adds a point-in-time research contract.

### Required stock-return input

For each symbol and entry date:

- symbol
- as_of
- lookback_return

Recommended windows for ablation:

- 5 trading days
- 20 trading days
- 60 trading days

### Required sector mapping

Time-aware mapping:

- symbol
- sector
- effective_from
- effective_to (nullable)

Historical changes must be respected.

### Optional market benchmark

For each date:

- market lookback return

This allows:

- sector_rs_vs_market = sector_return - market_return
- stock_rs_vs_sector = stock_return - sector_return

## Sector benchmark construction

Default research benchmark is the equal-weight cross-sectional mean of contemporaneous member returns.

This avoids requiring a named official sector index for the first replay, but only works after complete point-in-time membership and stock price history are available.

Later comparison should include official TWSE / TPEx sector indices where available.

## Leakage controls

The replay must NOT use:

- exit price
- v17_R
- base_net_R
- MFE / MAE
- future sector membership
- future corporate classifications

to construct the Sector RS feature.

Outcome fields are joined only after the feature is frozen at entry time.

## Planned ablation

Compare:

1. Base
2. Sector RS top 50%
3. Sector RS top 30%
4. Sector RS > 0 vs market
5. Stock RS > sector
6. Sector RS + Stock RS
7. Sector RS + Market Regime
8. Sector RS + Ranking

Metrics:

- trade count
- base_net_R expectancy
- PF
- win rate
- MDD
- tail-loss frequency
- yearly robustness
- 2024+ OOS proxy
- turnover / cost drag

## Promotion rule

Sector RS may enter Production only if:

- point-in-time mapping coverage >= 95%
- price-history coverage >= 95%
- no look-ahead leakage
- improvement survives walk-forward and 2024+ OOS proxy
- no single calendar year dominates the effect
- cost-adjusted expectancy remains positive
- effect survives Market Regime stratification

## Current conclusion

**Sector RS is conceptually important but NOT YET empirically validated in Sky.**

**Status: DATA BLOCKED → REPLAY INFRASTRUCTURE READY**
