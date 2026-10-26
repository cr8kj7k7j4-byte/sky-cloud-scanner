# W5 Preregistration — Opening Retest Reclaim Baseline D

Date: 2026-10-26
Owner: W5｜Sky Candidate Strategy Lab
Status: PREREGISTERED_STRUCTURAL_CHALLENGER
Production impact: NONE
Source data: governed whole-market 1-minute PIT artifacts from workflow run 40267006806
Primary research window: 2026-01-01 through 2026-10-22

## 1. Research question

Does waiting for an early strong stock to pull back to the session open and then causally reclaim the session open improve after-cost expectancy versus entering the first opening acceleration wave directly?

Baseline D is structurally distinct from rejected Baseline C. It changes the entry architecture from first-wave acceleration to retest-and-reclaim confirmation. It is not a threshold rescue of Baseline C.

## 2. Observation and execution window

- Opening observation window: 09:00–09:15.
- With 1-minute bars, 09:00 initializes the session open.
- Reclaim evidence must be visible only after a completed bar.
- Earliest causal entry is the next minute open after a completed reclaim bar.
- No entry after the 09:15 decision boundary.

## 3. Whole-market universe

At each session:
- use the full governed PIT-active Taiwan equity universe contained in the frozen source run;
- no Top100 membership requirement;
- no TWD 100 price cap;
- no end-of-day ranking or universe leakage.

## 4. Frozen structural sequence

A symbol becomes eligible only after the following causal sequence occurs:

1. PRIOR STRENGTH:
   - before the retest, at least one completed 1-minute bar closes strictly above the session open.

2. OPEN RETEST:
   - after prior strength has occurred, a completed 1-minute bar touches or crosses the session open: low <= session_open.

3. RECLAIM:
   - after the retest event, a later completed 1-minute bar closes strictly above session_open.
   - the reclaim bar itself is observation-only and cannot be entered using its own close.

4. ENTRY:
   - entry proxy is the next 1-minute bar open after the completed reclaim bar;
   - entry must lie strictly above session_open and at or below the fourth legal Taiwan exchange tick above session_open;
   - otherwise status is NO_ENTRY_OPEN_ZONE or MISSED_4TICK_NO_CHASE.

The same symbol may enter at most once per session.

## 5. Stop

After valid entry:
- the first subsequent 1-minute bar whose low < session_open triggers the opening-price stop;
- fill proxy = min(session_open, trigger_bar_open) when the trigger bar open is available;
- no averaging down;
- no stop widening.

## 6. Outcome horizons

Report:
- 30-minute stop-aware return;
- 60-minute stop-aware return [PRIMARY];
- session-close return;
- MFE / MAE where available;
- +5% post-entry excursion;
- near-limit proxy;
- opening-stop hit rate.

## 7. Cost model

- Primary round-trip cost: 0.45%.
- Stress round-trip cost: 0.65%.

A gross-positive but after-cost-negative result fails.

## 8. Selection policy

Baseline D tests the event pattern itself:
- include every first valid reclaim event per symbol/session;
- do not optimize Top-N, score weights, retest depth, reclaim buffer, volume threshold, or ranking threshold after outcomes are visible.

Cross-sectional ranking, if later justified, must be a separately preregistered structural extension.

## 9. Decision rule

PROMOTE_CANDIDATE_TO_W4 only if:
- evaluable 60m sample >= 200;
- 0.45% after-cost expectancy > 0;
- PF > 1;
- 0.65% stress is not catastrophic;
- no single-symbol concentration > 20%;
- first-half / second-half evidence is not structurally contradictory.

HOLD:
- insufficient sample or mixed stability.

REJECT:
- 0.45% after-cost expectancy <= 0;
- PF <= 1;
- persistent instability.

Promotion, if any, is W4 Shadow/Paper only. Production remains unchanged.
