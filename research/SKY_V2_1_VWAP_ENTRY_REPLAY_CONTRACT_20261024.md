# Sky V2.1 VWAP / Entry Location Historical Replay Contract

- Date: 2026-10-24
- Status: DATA CONTRACT + RESEARCH INFRASTRUCTURE
- Production status: NOT ELIGIBLE

## Current evidence status

The accessible historical Swing ledgers contain:
- entry
- trigger
- stop
- risk
- exit
- cost-adjusted outcome (base_net_R)

They do **not** contain contemporaneous:
- VWAP at entry
- session high/low at entry time
- intraday location
- RVOL
- bid/ask spread
- VWAP slope
- breakout-bar structure

Therefore VWAP / Entry Location cannot yet be honestly ablated against Net Expectancy.

The existing Sky day-trading workbook includes VWAP-oriented rules such as Price > VWAP and positive VWAP slope, but these are explicitly marked as pending validation rather than historical evidence.

## New replay module

`src/vwap_entry_replay.py`

Required point-in-time fields:
- symbol
- as_of
- entry_price
- vwap

Optional but strongly recommended:
- session_low
- session_high
- rvol
- spread_pct

Derived:
- price_vs_vwap_pct = (entry_price - vwap) / vwap
- session_position = (entry - session_low) / (session_high - session_low)

## Leakage controls

VWAP / Entry Location features must be frozen at decision time.

Forbidden inputs:
- exit price
- base_net_R / v17_R
- MFE / MAE
- future bars
- end-of-day high/low if the trade was entered before the close
- later VWAP values

If an entry occurs at 10:15, all session statistics must be based only on data available through 10:15.

## Planned ablation

Compare:
1. Base
2. Price above VWAP only
3. Positive VWAP slope only
4. Price above VWAP + positive slope
5. VWAP deviation buckets
6. Session-position buckets
7. RVOL buckets
8. Spread buckets
9. Composite Entry Quality
10. Composite Anti-Chase

Primary metrics:
- base_net_R / execution-adjusted R
- Net Expectancy
- PF
- MDD
- MAE
- MFE
- tail-loss frequency
- sample count
- turnover / cost drag
- yearly robustness
- 2024+ OOS proxy

## Research hypotheses

These are hypotheses only:
- Mild positive VWAP deviation may represent healthy confirmation.
- Large positive deviation may represent late-stage chasing.
- Very high session-position without supporting RVOL may be lower quality.
- A positive VWAP slope may matter more than Price > VWAP alone.
- Spread and liquidity should be evaluated jointly with VWAP deviation.

## Promotion criteria

VWAP / Entry Location can enter Production only if:
- point-in-time coverage >= 95%
- timestamps are aligned to the actual decision time
- no look-ahead leakage
- cost-adjusted expectancy improves in walk-forward
- effect survives OOS and Market Regime stratification
- no single year dominates
- thresholds form a stable region rather than a single best point

## Current conclusion

**VWAP / Entry Location remains conceptually important but NOT YET empirically validated in Sky.**

**Status: DATA BLOCKED → REPLAY INFRASTRUCTURE READY**
