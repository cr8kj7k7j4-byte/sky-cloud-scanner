# W1｜Trend Persistence Challenger V1.1 — Prospective Implementation Contract

- Frozen before first fresh-OOS observation: 2026-10-27
- Fresh-OOS signal date: strictly after 2026-10-27
- Production impact: NONE

This file resolves implementation details that were not numerically explicit in the preregistration. It does not change the registered hypothesis, feature family, horizon, costs, or selection threshold.

## Exact calculations

All calculations use adjusted PIT-safe daily bars available through D close.

- MA20 = arithmetic mean of close[D-19:D]
- MA60 = arithmetic mean of close[D-59:D]
- prior20_high = max(high[D-20:D-1])
- ret5 = close[D] / close[D-5] - 1
- ret20 = close[D] / close[D-20] - 1
- range_pct = (high[D] - low[D]) / close[D]
- distance_ma20 = close[D] / MA20 - 1
- gap_abs = abs(open[D] / close[D-1] - 1)
- volume_ratio20 = volume[D] / mean(volume[D-19:D])
- realized_vol20 = population standard deviation of the 20 one-day close-to-close returns ending at D
- breadth(D) = fraction of eligible PIT symbols with close[D] > MA20[D]
- breadth_delta5 = breadth(D) - breadth(D-5 trading sessions)
- RS20 percentile = empirical CDF rank among eligible PIT symbols on the same date: count(value <= x) / n
- RS_delta5 = RS20_percentile(D) - RS20_percentile(D-5 trading sessions)

## Breakout event

The frozen V1.1 event is unchanged:
- breadth >= 0.50
- close > MA20 > MA60
- RS20 percentile >= 0.70
- close > prior20_high
- distance_ma20 <= 0.08
- range_pct <= 0.08
- execution-open price gate < TWD 100 is evaluated at D+1 open

## Exact persistence score

Within the same signal date D and among breakout events only, convert each feature to empirical-CDF percentile using count(value <= x) / n.

Positive direction:
1. breadth
2. breadth_delta5
3. RS20 percentile
4. RS_delta5
5. volume_ratio20
6. ret5
7. ret20

Inverse direction:
8. distance_ma20
9. range_pct
10. realized_vol20
11. gap_abs

For inverse features use 1 - percentile.

Score = arithmetic mean of all 11 transformed values. No imputation, winsorization, interaction, clipping, nonlinear transform, or alternate weighting is allowed.

Selection = same-date empirical-CDF percentile of score >= 0.90. Ties are included.

## Forward outcome

For signal date D:
- entry = open on the first market trading session after D (D+1)
- exit = close on the fifth market trading session after D (D+5)
- gross_F5 = exit / entry - 1
- net_045 = gross_F5 - 0.0045
- net_065 = gross_F5 - 0.0065

If D+1 open or D+5 close is unavailable for the symbol, the outcome remains incomplete and is not synthesized.

## Prospective data rule

- 2026-10-27 may be stored as a seed feature day but may not generate fresh-OOS signals.
- Only signal_date > 2026-10-27 is fresh OOS.
- Current-day snapshot must be collected after market close with >=80% operational whole-market quote coverage.
- The daily snapshot source is recorded explicitly; MIS OTC remains an operational fallback and is not mislabeled as TPEx-official certification.
- Missing market benchmark keeps the Bull/Neutral/Bear gate DATA_BLOCKED. No cross-sectional proxy may silently replace it.

## Formal decision

Before any final decision:
- >=200 evaluable fresh-OOS signals
- >=20 fresh trading days
- outcome completeness >=95% for outcomes that have matured to D+5
- single-symbol share <=20%

REJECT_CANDIDATE when the sufficiency gate is met and either:
- 0.45% expectancy <= 0, or
- 0.45% PF <= 1, or
- 0.65% expectancy <= 0.

PROMOTE_CANDIDATE is impossible while the regime gate is DATA_BLOCKED, and additionally requires all preregistered regime/capacity/Shadow/P0-R/P0-G gates.
