# W5 Preregistration — Top100 Velocity Baseline vs Sky Day Trading v1.4

Date: 2026-10-26
Owner: W5｜Sky Candidate Strategy Lab
Status: PREREGISTERED_RESEARCH_CANDIDATE / DATA_BLOCKED
Production impact: NONE

## 1. Research question

Does the user's original intraday hypothesis:

> current-day top-100 gainers -> identify the fastest currently strengthening stocks

produce higher after-cost expectancy than the current Sky Day Trading v1.4 decision stack, and which later-added rules contribute incremental value versus suppress profitable momentum?

The purpose is not to restore an old rule by intuition. It is to reconstruct the original alpha hypothesis as a frozen baseline and compare it fairly against later Sky rules.

## 2. Structural distinction from frozen families

This candidate is NOT a local retune of:
- Fixed-time Intraday Ranking
- P0-S 5m Breakout
- Event-driven Intraday Ranking / Catalyst Stack
- Transparent Intraday ML Ensemble

The structural hypothesis is dynamic cross-sectional *change*:
- rolling membership in current-day top-100 gainers;
- price velocity;
- gain-rank velocity;
- volume acceleration;
- optionally relative-strength acceleration.

The primary signal is therefore temporal acceleration / rank migration inside a dynamically refreshed strong-stock universe, not a fixed-time cross-sectional score or a threshold tweak to an archived breakout family.

If implementation collapses into a fixed-time rank or ordinary breakout rule, the experiment must be stopped as DUPLICATE_FROZEN_FAMILY.

## 3. Universe

Eligible Taiwan listed / OTC common stocks available point-in-time at each observation timestamp.

Base eligibility:
- current price <= TWD 100 for new-entry experiments, consistent with current Sky default;
- exclude limit-up names;
- exclude inadequate liquidity;
- exclude excessive spread;
- exclude symbols lacking causal point-in-time observations.

At every decision timestamp, construct the Top100 pool using **only information observable at that timestamp**:

Top100_t = top 100 eligible stocks ranked by current-day return from prior close to price_t.

No end-of-day rankings may be backfilled into earlier timestamps.

## 4. Baseline A — Original Top100 Velocity

Baseline A is intentionally simple.

Candidate must:
1. belong to Top100_t;
2. show positive short-horizon price velocity;
3. show positive gain-rank velocity (moving toward rank 1);
4. show positive volume acceleration.

Primary concept:

PriceVelocity_t = change in intraday return over a frozen lookback.

RankVelocity_t = prior gain-rank - current gain-rank.
Positive values mean the stock is climbing the gainers ranking.

VolumeAcceleration_t = recent volume rate / prior comparable volume rate - 1.

No Market Gate, Sector Gate, Phase, VWAP, Anti-Chase, Setup/Trigger, or RR filter is included in Baseline A except mandatory tradability/risk/accounting constraints.

## 5. Frozen parameter policy

Exact lookbacks and thresholds must be fixed before outcome evaluation.

Initial research grid is prohibited.

Use one preregistered specification per experiment. No result-driven search across:
- Top N other than 100;
- velocity lookbacks;
- rank-velocity lookbacks;
- volume thresholds;
- stop/target values;
- holding periods;
- time-of-day exclusions.

Any alternative specification requires a separate preregistration and cannot be selected based on results from this experiment.

## 6. Champion–Challenger ladder

Compare the following sequentially:

A. Top100 + Velocity only
B. A + Anti-Chase
C. B + VWAP quality
D. C + Market Gate
E. D + Sector / Relative Strength
F. E + Phase
G. F + Setup / Trigger
H. G + RR Gate
I. Full reproducible Sky Day Trading v1.4 stack

The ladder is an ablation / incremental-value study, not a search for the highest backtest metric.

For every added layer record:
- delta after-cost expectancy;
- delta PF;
- delta win rate;
- delta average win / average loss;
- delta max drawdown;
- delta trade count;
- delta turnover;
- missed large winners;
- avoided large losers.

A rule is not justified merely because win rate increases.

## 7. Primary evaluation metrics

Promotion-relevant priority:

1. After-cost Expectancy
2. Profit Factor
3. Max Drawdown
4. Cross-fold / cross-regime stability
5. Average Win / Average Loss
6. MAE / MFE
7. Win Rate
8. Turnover and capacity

Win rate is descriptive only and must not be treated as true predictive probability.

## 8. Cost model

Primary round-trip cost: 0.45%
Stress round-trip cost: 0.65%

Execution assumptions must be causal and consistent across all variants.

If a candidate is positive only before cost, it fails.

## 9. Validation

Mandatory gates:
- point-in-time alignment;
- survivorship audit;
- leakage audit;
- preregistration;
- Train / Validation / OOS separation where model fitting is involved;
- walk-forward >= 3 folds;
- Bull / Neutral / Bear regime analysis;
- 0.45% and 0.65% cost stress;
- portfolio / concentration / capacity;
- Shadow / Paper before any promotion;
- P0-R;
- P0-G.

No result from the existing ~100-symbol historical artifact can be described as promotion-grade evidence for this strategy.

## 10. Current blocker

Formal historical evaluation is DATA_BLOCKED because current intraday history covers only about 100 symbols, roughly 4.8%-5.3% of the governed PIT universe, while the research gate requires promotion-grade whole-universe coverage.

This experiment specifically requires broad-universe synchronized intraday history because Top100_t cannot be reconstructed correctly from a 100-symbol subset.

Until coverage is resolved:
- no win-rate superiority claim;
- no profitability superiority claim;
- no production change;
- forward Shadow/Paper evidence may be collected prospectively if the live scanner can construct the full Top100_t causally.

## 11. Decision rules

PROMOTE_CANDIDATE only if:
- the Top100 Velocity hypothesis demonstrates positive after-cost expectancy;
- results are stable across folds/regimes;
- capacity and concentration gates pass;
- it survives Shadow/Paper sufficiency;
- the winning architecture outperforms or adds robust incremental value versus v1.4.

HOLD if evidence is insufficient or data coverage fails.

REJECT if after-cost expectancy or stability fails.

If later-added Sky rules reduce expectancy without compensating risk reduction, they should be candidates for removal from the challenger architecture; Production remains unchanged until P0-G review.

## 12. Governance statement

This document restores the user's original Top100 -> fastest-strengthening-stock concept as a formal research baseline, not as a production rule.

Sky Day Trading v1.4 remains ACTIVE and unchanged until all promotion gates are passed and W0/P0-G records a formal decision.
