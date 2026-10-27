# W1｜Trend Persistence Challenger V1.1 — Prospective Exact Pre-registration

- Date frozen: 2026-10-27
- Status: PREREGISTERED_PROSPECTIVE_CHALLENGER
- Production impact: NONE
- Historical 2023-2026 data: contaminated by prior inspection; research-only
- Fresh OOS starts strictly after: 2026-10-27

## 1. Purpose
Prospectively test whether a fixed, equal-weight persistence score can distinguish post-breakout continuation from failure without retuning the frozen Swing breakout event.

## 2. Breakout event
Use the exact frozen event:
- breadth >= 0.50
- close > MA20 > MA60
- 20D RS percentile >= 0.70
- close > prior 20D high
- close / MA20 - 1 <= 0.08
- daily range / close <= 0.08
- execution open < TWD 100

No threshold changes are permitted in V1.1.

## 3. Primary outcome
Primary horizon: F5
- F5 = close(D+5) / open(D+1) - 1

Primary decision metric:
- after-cost F5 expectancy

Costs:
- primary 0.45% round trip
- stress 0.65% round trip

## 4. Exact persistence score
All features use information available by D close.

For every breakout event on date D, compute same-date cross-sectional percentile ranks among breakout events.

Positive-direction percentiles:
1. breadth
2. breadth 5D change
3. 20D RS percentile
4. RS percentile 5D change
5. volume / 20D average volume
6. prior 5D return
7. prior 20D return

Inverse-direction percentiles:
8. distance from MA20
9. signal-day range / close
10. 20D realized volatility
11. absolute gap from prior close to D open

For inverse features use: 1 - percentile.

Score:
- arithmetic mean of the 11 transformed percentile features
- all weights exactly 1/11
- no missing-feature imputation; missing any required feature = no score
- no winsorization
- no nonlinear transform
- no feature interactions

Selection:
- same-date score percentile >= 0.90
- ties included
- no Top-N override

## 5. Fresh OOS
Only observations with signal date > 2026-10-27 count toward formal validation.

Historical 2023-01-01 through 2026-10-22 may be used only as exploratory/context evidence and must never be relabeled as fresh OOS.

## 6. Prospective sufficiency gate
Before any promotion review:
- >= 200 evaluable breakout events with scores
- >= 20 trading days
- >= 2 market regimes
- outcome completeness >= 95%
- single-symbol share <= 20%

## 7. Regime definition
Use PIT-safe market benchmark:
- BULL: benchmark close > MA60 and MA60 20D slope > 0
- BEAR: benchmark close < MA60 and MA60 20D slope < 0
- NEUTRAL: otherwise

No regime may be added or redefined after prospective observations accumulate.

## 8. Promotion thresholds
PROMOTE_CANDIDATE requires all:
1. fresh-OOS top-decile 0.45% expectancy > 0
2. fresh-OOS top-decile PF > 1
3. fresh-OOS 0.65% stress expectancy > 0
4. no catastrophic regime failure
5. concentration gate passes
6. capacity/liquidity gate passes
7. outcome completeness >= 95%
8. Shadow/Paper gate subsequently passes
9. P0-R and P0-G approval

Otherwise HOLD / REJECT / ARCHIVE.

## 9. Explicit prohibitions
Do not alter after fresh OOS begins:
- feature list
- feature signs
- 1/11 weights
- top-decile cutoff
- F5 primary horizon
- cost assumptions
- breakout thresholds
- regime definition
- sufficiency thresholds

Any change requires a new version ID and new preregistration.
