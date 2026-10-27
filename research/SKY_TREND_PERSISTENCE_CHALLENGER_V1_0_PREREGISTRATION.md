# W1｜Trend Persistence Challenger V1.0 — Pre-registration

- Date frozen: 2026-10-27
- Status: PREREGISTERED_RESEARCH_CANDIDATE
- Production impact: NONE
- Parent diagnostic: Sky Swing Challenger V1.1 2026 edge-decay analysis
- Purpose: test whether post-breakout continuation/persistence provides independent information beyond the frozen V1.1 breakout event.
- Governance: new structural target/label; not a threshold retune of V1.1.

## 1. Research hypothesis

The 2026 deterioration observed in Swing V1.1 may be explained by weaker post-breakout continuation rather than reduced winner size.

Primary hypothesis:

> A breakout signal has materially different forward expectancy depending on whether short-horizon trend persistence survives the first 1–5 trading days after the signal.

This study tests persistence as a new target/label and explanatory feature family. It does not alter V1.1 thresholds after observing outcomes.

## 2. Universe

- Taiwan TWSE + TPEx canonical PIT universe only.
- Ordinary equities only.
- Long-only research.
- Execution-open price < TWD 100 for any tradable challenger replay.
- Minimum 120 prior trading days.
- Missing or invalid bars fail closed.
- No current-universe backward substitution.
- Corporate-action-adjusted, PIT-safe daily bars required.

## 3. Causality contract

All signal-date features use information available through date D close.

For explanatory labels:
- forward data are used only as labels/outcomes, never as signal inputs.

For any later tradable challenger:
- decision at D close;
- entry no earlier than D+1 open;
- no D+1 high/low/close may leak into D features.

## 4. Frozen breakout event definition

To avoid result-driven event selection, the breakout event is inherited exactly from V1.1:

- close(D) > MA20(D)
- MA20(D) > MA60(D)
- 20D RS percentile >= 0.70
- close(D) > prior 20D high
- close(D)/MA20(D)-1 <= 0.08
- daily range(D)/close(D) <= 0.08
- market breadth >= 0.50

These rules define the event sample only. They are not retuned in this study.

## 5. New target / label family

### 5.1 Continuation return labels

For each breakout event at D:

- F1 = close(D+1) / open(D+1) - 1
- F3 = close(D+3) / open(D+1) - 1
- F5 = close(D+5) / open(D+1) - 1
- F10 = close(D+10) / open(D+1) - 1

Primary target:
- **F5 after-cost continuation return**

Secondary targets:
- F1, F3, F10
- market-residual F5 if a PIT-safe benchmark series is available.

### 5.2 Persistence-state labels

A breakout is classified into one of the following mutually exclusive outcome states using forward outcome data only:

- PERSIST_STRONG: F5 > +2.0%
- PERSIST_WEAK: 0 < F5 <= +2.0%
- FAILED: F5 <= 0

These are diagnostic labels only. The thresholds are frozen before replay.

## 6. Pre-signal feature families

Only features known at D close may be tested:

1. Market breadth level
2. Breadth 5D change
3. Stock 20D RS percentile
4. RS 5D change
5. Distance from MA20
6. Signal-day range %
7. 20D realized volatility
8. 5D / 20D volume ratio
9. Gap from prior close to D open
10. Prior 5D return
11. Prior 20D return
12. Sector-relative strength, only if PIT sector membership is verified
13. Cross-sectional leadership concentration, if computable PIT-safely
14. Market benchmark 5D / 20D return
15. Market benchmark 20D realized volatility

No indicator-period search, nonlinear feature explosion, or unregistered feature additions after first result review.

## 7. Baseline comparisons

Required baselines:

A. All frozen breakout events
B. Simple deterministic persistence-score baseline using only registered features
C. Linear/logistic baseline for persistence classification

Nonlinear ML is out of scope for V1.0.

## 8. Validation split

Because 2026 data have already been inspected in prior research, they must not be called fresh OOS.

Historical diagnostic split:
- Train: 2023-01-01 through 2024-06-30
- Validation: 2024-07-01 through 2025-06-30
- Research Test: 2025-07-01 through 2026-10-22

Research Test is not fresh untouched OOS.

True fresh OOS:
- prospective dates strictly after 2026-10-27 only.

No threshold or model changes may be selected using Research Test performance.

## 9. Walk-forward

Mandatory three time-ordered folds:

- Fold 1 train: 2023-01 to 2023-12; test: 2024-01 to 2024-06
- Fold 2 train: 2023-01 to 2024-06; test: 2024-07 to 2025-03
- Fold 3 train: 2023-01 to 2025-03; test: 2025-04 to 2026-10-22

Report each fold separately. No fold may be hidden.

## 10. Market regime definition

Frozen before replay.

Using PIT-safe market benchmark close and MA60 at D:

- BULL: close > MA60 and MA60 slope over prior 20D > 0
- BEAR: close < MA60 and MA60 slope over prior 20D < 0
- NEUTRAL: all other observations

Regime is diagnostic and validation context only in V1.0. It is not an entry gate.

## 11. Cost model

For tradability analysis:

- Primary round-trip cost: 0.45%
- Stress round-trip cost: 0.65%

For pure label diagnostics, gross labels may be shown, but promotion decisions must use after-cost results.

## 12. Required metrics

For continuous targets:
- n
- mean / median forward return
- positive-rate
- PF where applicable
- bootstrap confidence interval
- yearly results
- walk-forward folds
- Bull / Neutral / Bear

For classification:
- class balance
- precision / recall
- ROC-AUC only as secondary
- calibration
- top-decile vs universe forward expectancy

Primary research success metric:
- after-cost top-decile F5 expectancy that is positive in Validation and Research Test,
- and non-negative in all three walk-forward test folds.

Accuracy alone cannot pass.

## 13. Concentration / capacity

Any candidate ranking must report:
- single-symbol share <= 20%
- top-5-symbol share
- sector concentration where PIT mapping exists
- signal count
- average daily selected names
- liquidity/capacity proxy

Failure blocks promotion.

## 14. Promotion gate for this research

V1.0 may be labeled PROMOTE_CANDIDATE only if all are true:

1. PIT data integrity passes.
2. Validation after-cost F5 expectancy > 0.
3. Research Test after-cost F5 expectancy > 0.
4. All three walk-forward test folds are non-negative.
5. 0.65% stress-cost expectancy remains > 0 overall.
6. No catastrophic Bull/Neutral/Bear regime failure.
7. Concentration/capacity gates pass.
8. No material leakage.
9. Prospective fresh-OOS / Shadow evidence is subsequently accumulated before any Production review.

Otherwise:
- HOLD / REJECT / ARCHIVE.

## 15. Explicit prohibitions

After replay results are visible, do not:
- change the 0.70 RS threshold;
- change MA20 / MA60 periods;
- change breakout lookback;
- change PERSIST_STRONG +2% threshold;
- cherry-pick F1/F3/F5/F10 as the primary target;
- change Train/Validation/Research-Test dates;
- alter fold boundaries;
- tune stop/target/holding period to rescue performance;
- promote a positive subgroup when aggregate validation fails.

Any such change requires a new version and new preregistration.

## 16. Expected decision value

This study should answer one narrow question:

> Can pre-signal information distinguish breakouts that persist from breakouts that fail, with enough stability to survive cost and time splits?

If no, the Swing breakout family should be treated as structurally weak in the current market and not rescued by local retuning.
