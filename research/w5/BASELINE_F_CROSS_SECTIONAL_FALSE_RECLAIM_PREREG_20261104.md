# W5/W2 Baseline F — Cross-sectional Market-confirmed False-Reclaim Short

Pre-registration: 2026-11-04 (before F results)
Owner: W5 new hypothesis; W2 historical research. Production unchanged.
Status: EXPLORATORY_REUSED_2026_NOT_FRESH_OOS

## Structural change relative to rejected E
Add an independent **PIT contemporaneous cross-sectional market state** from all eligible source-file securities at the **completed breakdown minute**, not a retune of E's 4-tick, time, stop, or exit parameters.

Frozen hypothesis: individual failed opening reclaim is more likely to persist downward if (i) the equal-weighted exchange median open-to-now return is negative, and (ii) the candidate's same-minute open-to-now return is below its exchange median. These are sign tests on contemporaneous market and residual return, not optimized rank cutoffs.

## Frozen inputs
- historical source: original Baseline E short 1m PIT shard artifacts from GitHub run 40329668748;
- source dates: 2026-01-01..2026-10-22; both halves were previously used by E so ALL F results are EXPLORATORY, never untouched OOS;
- every peer uses only a completed 1-minute close divided by its own session open;
- peer census is computed independently for TWSE and TPEx per session and minute, excludes candidate symbol from the median;
- data-quality gate: at least 100 valid other-symbol peer observations at that instant;
- no future prices enter the market gate.

## Entry architecture
Use **the unchanged first E sequence** (strength -> retest -> reclaim -> completed breakdown -> next-minute short in opening-price-minus-4-legal-ticks zone). Each symbol-session at most one E candidate. Then apply the above contemporaneous market sign gates to that E candidate. Do not select a later candidate after an initial one is rejected.

## Exit / cost
Use E's 30m/60m stop-aware outcomes: stop on a later bar high > session open, fill conservatively at max(open, trigger bar open); 60-minute is primary. Gross actual short share-return is **(entry - cover) / entry**, NOT E's legacy entry/cover - 1. Existing E raw gross can be converted exactly by r_correct = r_legacy / (1+r_legacy), preserving the same cover prices and causal entry. Run both filtered F and all-source E corrected-control through the identical metric formula; their difference is exploratory descriptive evidence, not confirmatory.

Fixed round-trip costs 0.45% primary / 0.65% stress. No parameter, rank, stop, time, or cost tuning after seeing result.

## Governance
Primary reject if F sample >=200 and cost-0.45 expectancy <=0 or PF <=1; HOLD if <200. A positive backtest is only HOLD_REQUIRES_FRESH_OOS_SHORT_ELIGIBILITY, NOT PROMOTE. Independently need never-before-used future dates, short-sale eligibility at time, borrowability, real bid-ask/impact/fill and portfolio capital checks, market regime, W4 forward thresholds (>=200, >=20 trading days, >=2 regimes, >=95% complete, <=20% single-stock concentration) and W0/P0-G review. No automatic shorts or Production changes.
