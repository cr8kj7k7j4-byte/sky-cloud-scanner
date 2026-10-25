# W2｜Top100 Velocity Baseline A — Execution Status 2026-10-26

## Status
IMPLEMENTED / LIVE BACKTEST PENDING

## Frozen candidate
Dynamic Top100 Velocity Baseline A.

Historical source:
- corrected PIT whole-universe 5m Fugle history
- workflow run 40221377923
- 54,187,242 retained bars
- symbol coverage 99.8519%
- symbol-day coverage 98.9071%

## Historical scope
2023-05-23 through 2026-10-22.

## Frozen observation schedule
- 09:05 reference only
- 09:15 trade observation
- 09:30 trade observation
- 09:50 trade observation
- 10:15 trade observation

## Frozen signal
Current causal Top100 gainers and:
- positive price velocity per minute
- positive gain-rank velocity per minute
- positive volume-rate acceleration

Score:
equal-weight mean of the three within-group percentile ranks.

Selection:
top decile of signal candidates.

## Frozen outcome
- entry = open of the first 5m bar starting at observation timestamp
- exit = close of the bar ending 30 minutes later
- no stop/target optimization
- primary cost = 0.45% round trip
- stress cost = 0.65% round trip

## Validation labels
- DEVELOPMENT: through 2024-12-31
- VALIDATION: calendar 2025
- RESEARCH_TEST: 2026-01-01 through 2026-10-22

2026 is not fresh untouched OOS.

## Historical comparison boundary
No historical full-rule v1.4 comparison is performed.
W0 PR #118 closed that lane as unreconstructable from authoritative historical evidence.

If Baseline A survives, Production v1.4 versus challenger comparison moves to W4 prospective Shadow/Paper.

## Production impact
NONE.
