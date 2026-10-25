# W5 Preregistration — Top100 Velocity Baseline

Date: 2026-10-26
Owner: W5｜Sky Candidate Strategy Lab
Status: PREREGISTERED_RESEARCH_CANDIDATE / HISTORICAL_BASELINE_ELIGIBLE
Production impact: NONE

## 1. Research question

Does the user's original intraday hypothesis:

> current-day Top100 gainers -> identify the fastest currently strengthening stocks

contain a causal, reproducible after-cost intraday edge?

Historical work evaluates the challenger itself. It does not claim a historical full-rule comparison versus Sky Day Trading v1.4 because W0 PR #118 formally closed that lane as not fully reconstructable from the current GitHub SSOT.

Champion-versus-challenger comparison against live Production v1.4 is reserved for prospective Shadow/Paper evidence.

## 2. Structural distinction from frozen families

This candidate is not a local retune of:
- Fixed-time Intraday Ranking;
- P0-S 5m Breakout;
- Event-driven Intraday Ranking / Catalyst Stack;
- Transparent Intraday ML Ensemble.

The distinct hypothesis is dynamic cross-sectional acceleration:
- rolling membership in current-day Top100 gainers;
- price velocity;
- gain-rank velocity;
- volume-rate acceleration.

If implementation collapses into fixed-time ranking or ordinary breakout threshold tuning, stop as `DUPLICATE_FROZEN_FAMILY`.

## 3. Historical source eligibility

Canonical source:
- corrected PIT whole-universe 5-minute Fugle history;
- W3A corrected reconciliation workflow 40221377923;
- 2,022 symbols with bars;
- symbol coverage 99.8519%;
- symbol-day coverage 98.9071%;
- minimum daily coverage 97.3726%;
- 54,187,242 retained 5m bars;
- duplicate/conflicting/out-of-membership bars = 0.

Research window:
2023-05-23 through 2026-10-22.

## 4. Frozen Baseline A specification

### Scan timestamps
Reference scan:
- 09:05 (feature/rank reference only; no trade entry)

Tradable observations:
- 09:15
- 09:30
- 09:50
- 10:15

Asia/Taipei.

A 5-minute candle is usable for features only when:
`bar_start + 5 minutes <= observation_timestamp`.

### Universe
At each timestamp:
1. governed PIT-active Taiwan equity universe;
2. current causal price > 0;
3. price <= TWD 100;
4. valid prior-session close;
5. day return < +9.9% to conservatively exclude limit-up/near-limit observations;
6. enough completed bars for the required feature intervals.

No end-of-day ranking may be backfilled into earlier timestamps.

### Top100
`Top100_t` = the 100 highest current-day returns among eligible names at timestamp t.

Current-day return:
`price_t / prior_session_close - 1`.

### Velocity features
For each tradable observation and its immediately prior official scan:

`price_velocity_per_min = (day_return_t - day_return_prev) / elapsed_minutes`

`rank_velocity_per_min = (gain_rank_prev - gain_rank_t) / elapsed_minutes`

Positive rank velocity means the stock is climbing toward rank 1.

Volume rate:
interval volume between the prior scan and current scan divided by elapsed minutes.

Volume acceleration:
`volume_rate_current / volume_rate_previous - 1`.

The 09:05 scan supplies the first previous-scan reference.

### Signal eligibility
Candidate must:
- be in `Top100_t`;
- price_velocity_per_min > 0;
- rank_velocity_per_min > 0;
- volume_acceleration > 0.

### Frozen score
Within the current Top100 signal candidates:
- percentile rank price velocity;
- percentile rank rank velocity;
- percentile rank volume acceleration.

`velocity_score = mean(three percentile ranks)`.

No optimized weights.

### Frozen selection
Select the top decile by `velocity_score` at each observation.
Because the parent universe is Top100, the selected basket is at most 10 names.

No alternative Top-N is tested in this preregistration.

## 5. Entry / exit / outcome

Entry:
- open of the first 5-minute bar whose start timestamp equals the observation timestamp;
- that bar is not used in decision features.

Exit:
- close of the bar ending 30 minutes after entry.

Baseline A deliberately uses a fixed 30-minute horizon and no stop/target optimization. This isolates directional acceleration edge before trade-management rules are introduced.

Record:
- gross return;
- net return after 0.45% round-trip cost;
- net return after 0.65% round-trip cost;
- MFE during holding window;
- MAE during holding window;
- holding time;
- observation time;
- symbol/date concentration.

## 6. Validation splits

No parameter fitting occurs after outcome visibility.

Chronological reporting:
- DEVELOPMENT: 2023-05-23 through 2024-12-31;
- VALIDATION: 2025-01-01 through 2025-12-31;
- RESEARCH_TEST: 2026-01-01 through 2026-10-22.

2026 is not described as fresh untouched OOS because Sky has already used 2026 data in prior research.

Fresh evidence must come from prospective W4 Shadow/Paper.

## 7. Primary metrics

Priority:
1. After-cost Expectancy
2. Profit Factor
3. Max Drawdown
4. Fold/year/time-of-day stability
5. Average Win / Average Loss
6. MAE / MFE
7. Win Rate
8. Turnover / concentration / capacity proxies

Win rate is descriptive, not probability.

## 8. Cost model

Primary: 0.45% round trip.
Stress: 0.65% round trip.

A candidate that is positive only before cost fails.

## 9. Walk-forward / stability

Report at minimum:
- half-year folds where sample is sufficient;
- year/split;
- observation timestamp;
- exchange where identifiable;
- concentration by symbol;
- number of selected names per observation.

No result-driven threshold changes are allowed.

## 10. Historical ladder boundary

The first authorized historical experiment is Baseline A only.

Later challenger layers may be separately preregistered only after Baseline A evidence is known and without using result-driven parameter rescue.

Historical layer I = “full v1.4” is removed because W0 PR #118 established that authoritative historical full-rule v1.4 replay is unavailable.

Production v1.4 comparison occurs prospectively in W4 Shadow/Paper.

## 11. Decision rules

`PROMOTE_TO_SHADOW_CANDIDATE` only if:
- 0.45% after-cost expectancy > 0;
- PF > 1;
- 0.65% stress is not structurally catastrophic;
- results are not dominated by one fold/year/time slot/symbol;
- drawdown and MAE are acceptable relative to expectancy.

`HOLD` if evidence is mixed or sample coverage is insufficient.

`REJECT` if after-cost expectancy/PF/stability fail.

No historical result changes Production directly.

## 12. Forward Champion–Challenger

If historical Baseline A survives:
- W4 collects prospective Top100 Velocity observations;
- Production v1.4 is recorded in parallel at the same timestamps where feasible;
- comparison uses forward after-cost counterfactual evidence;
- P0-R / W6 / W0 / P0-G remain mandatory before any Production decision.

Sky Day Trading v1.4 remains ACTIVE and unchanged.
