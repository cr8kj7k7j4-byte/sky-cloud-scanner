# W5 Preregistration — Opening Acceleration Scanner Baseline C

Date: 2026-10-26
Owner: W5｜Sky Candidate Strategy Lab
Status: PREREGISTERED_STRUCTURAL_CHALLENGER / DATA_GATE_PENDING
Production impact: NONE

## 1. Research question

Can a causal 09:00–09:15 whole-market opening scanner identify first-wave intraday leaders by measuring how quickly a stock enters the current-day Top100 gainers, while requiring price to remain above the session open and confirming short-horizon return/rank/volume acceleration?

This is not a rescue of Baseline A or B.

## 2. Structural distinction from Baseline A / B

Baseline A/B:
- relied on 5-minute bars;
- first tradable observation was 09:15;
- evaluated already-formed Top100 membership at fixed later timestamps;
- Baseline B added an opening-price gate.

Baseline C:
- begins at 09:01 after the first completed 1-minute bar;
- rebuilds the whole-market current-day gain ranking every minute;
- explicitly measures Top100 entry time and rank migration velocity;
- focuses on 09:01–09:15 opening formation;
- requires price > session open;
- measures 1/3/5/10-minute return and rank acceleration;
- records volume velocity/acceleration;
- seeks first-wave activation before extension.

Therefore Baseline C is a structurally distinct hypothesis, not threshold/Top-N/stop-target retuning of an archived family.

## 3. Data gate

Required source:
- governed PIT-active Taiwan equity universe;
- whole-universe 1-minute intraday candles;
- Asia/Taipei timestamps;
- no end-of-day universe/rank leakage.

Historical source window target:
2023-05-23 through latest eligible complete session.

Before any outcome test:
1. verify Fugle 1-minute endpoint access;
2. verify causal timestamp semantics;
3. establish whole-universe symbol coverage and symbol-day coverage;
4. reject duplicate/conflicting/out-of-membership bars;
5. freeze a 1-minute source run ID.

If the 1-minute data gate fails, Baseline C remains DATA_BLOCKED.

## 4. Observation window

Primary decision-clock window:
- 09:01 through 09:15, inclusive.

Causal candle convention:
- Fugle minute-candle timestamp is treated as the bar start label.
- At decision clock 09:01, only the completed 09:00 bar may be used.
- At decision clock t, features use the bar labeled t-1 minute.
- The entry proxy is the open of the bar labeled t.
- Therefore no same-minute close is visible before its bar completes.

09:00 is initialization; the first actionable decision clock is 09:01.

## 5. Universe and causal price

At each minute t:
1. symbol is PIT-active;
2. valid prior-session close exists;
3. latest completed 1-minute close is available;
4. price > 0;
5. price <= TWD 100;
6. current-day return < +9.5% near-limit guard;
7. session open is known from the 09:00 bar.

Current-day return:
price_t / prior_session_close - 1.

No end-of-day values may be backfilled into t.

## 6. Current Top100 and entry dynamics

At every minute t:
- rank every eligible symbol by current-day return;
- Top100_t = ranks 1–100.

For each symbol record:
- current gain rank;
- prior 1m / 3m / 5m / 10m rank where available;
- first minute it enters Top100;
- minutes since first Top100 entry;
- whether this is a new Top100 entrant.

Rank velocity over horizon h:
(rank_{t-h} - rank_t) / h.

Positive rank velocity means movement toward rank 1.

## 7. Opening-price gate

Mandatory:
price_t > session_open.

This is a structural gate inherited from the user's opening hypothesis, not a claim that Baseline B succeeded.

## 8. Frozen acceleration features

Return horizons:
- ret_1m
- ret_3m
- ret_5m
- ret_10m

Rank velocity horizons:
- rank_velocity_1m
- rank_velocity_3m
- rank_velocity_5m
- rank_velocity_10m

Volume:
- volume_rate_1m = current completed 1m volume
- volume_rate_3m = rolling 3m mean volume
- volume_acceleration_1v3 = current 1m volume / prior rolling 3m mean - 1

Acceleration descriptors are causal differences between shorter- and longer-horizon rates; no future bars may enter features.

## 9. Baseline C eligibility

A candidate at t must:
- be in Top100_t;
- price_t > session_open;
- be either a new Top100 entrant or have entered Top100 within the previous 3 completed minutes;
- rank_velocity_1m > 0;
- ret_1m > 0;
- volume_acceleration_1v3 > 0;
- satisfy price/near-limit/data-quality gates.

No alternative threshold search is allowed in Baseline C.

## 10. Frozen score

Within all eligible candidates at each minute:
- percentile(rank_velocity_1m)
- percentile(rank_velocity_3m when available)
- percentile(ret_1m)
- percentile(ret_3m when available)
- percentile(volume_acceleration_1v3)

Score = equal-weight mean of available frozen components.

No optimized weights.

## 11. Frozen selection

At each minute:
- select Top 3 eligible symbols by score;
- same symbol max one selection per session;
- tie break: better current gain rank, then symbol ascending.

No alternative Top-N search after outcome visibility.

## 12. Entry and outcomes

At decision clock t:
- feature bar = completed 1-minute candle labeled t-1 minute;
- entry proxy = open of the 1-minute candle labeled t.

The entry bar is never used in decision features.

Outcome horizons are all reported, but the primary economic decision metric uses 60 minutes:
- 30-minute exit
- 60-minute exit [PRIMARY]
- session close

Also record:
- MFE to 30m / 60m / close;
- MAE to 30m / 60m / close;
- whether post-entry high reaches +5%;
- near-limit-up proxy: post-entry high >= +9.5% vs prior close;
- holding time.

### Mandatory opening-price stop

After entry, if any subsequent 1-minute bar has:
`low < session_open`

the trade exits immediately via a stop-market proxy.

Fill proxy:
- if that stop-trigger bar opens below `session_open`, use the trigger bar open;
- otherwise use `session_open`.

This prevents a gap below the opening price from receiving an unrealistically favorable fill at the opening-price level.

The opening-price stop is mandatory for Baseline C and is frozen before historical strategy outcomes are observed.

No profit-target optimization in Baseline C.

## 13. Cost model

Primary round trip: 0.45%.
Stress: 0.65%.

A gross-positive / after-cost-negative result fails.

## 14. Validation

Chronological reporting:
- DEVELOPMENT: 2023-05-23 through 2024-12-31
- VALIDATION: 2025-01-01 through 2025-12-31
- RESEARCH_TEST: 2026-01-01 onward

2026 is not claimed as untouched OOS.

Required:
- half-year folds;
- yearly results;
- minute-of-entry stability;
- exchange;
- symbol concentration;
- market-regime breakdown where canonical regime data are available;
- 0.45% and 0.65% costs.

## 15. Ablation plan

Run frozen remove-one ablations only after Baseline C:
1. remove opening-price gate;
2. remove Top100 freshness / recent-entry condition;
3. remove rank velocity;
4. remove return acceleration component;
5. remove volume acceleration.

No threshold retuning inside ablations.

## 16. Decision rule

PROMOTE_CANDIDATE only if:
- primary stop-aware 60m 0.45% after-cost expectancy > 0;
- PF > 1;
- sample >= 200;
- validation/research-test are not structurally negative;
- no single symbol dominates;
- 0.65% stress is not catastrophic;
- remove-one evidence shows at least one structurally useful component rather than pure basket noise.

HOLD:
- insufficient sample/coverage or mixed stability.

REJECT:
- after-cost expectancy <= 0;
- PF <= 1;
- persistent fold instability;
- obvious concentration artifact.

Promotion, if any, is to W4 Shadow/Paper only. Production remains unchanged.
