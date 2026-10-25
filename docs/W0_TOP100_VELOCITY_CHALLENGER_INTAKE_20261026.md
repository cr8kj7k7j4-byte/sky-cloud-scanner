# W0 Intake — Top100 Velocity Challenger

Date: 2026-10-26
Source: W5 preregistration
Production change: NONE

## Decision
- Candidate: Top100 Velocity Baseline
- Status: PREREGISTERED_RESEARCH_CANDIDATE / DATA_BLOCKED
- Production Day Trading v1.4: ACTIVE / UNCHANGED
- Formal promotion: NOT AUTHORIZED

## Why this candidate is allowed
The research reconstructs the user's original alpha hypothesis as a dynamic rolling-universe acceleration model:
- causal Top100 gainers membership;
- price velocity;
- gain-rank velocity;
- volume acceleration.

It is structurally distinct from frozen Fixed-time Intraday Ranking and P0-S 5m Breakout. If implementation degenerates into those archived families, stop the experiment.

## Required comparison
Ablation ladder:
A Top100 + Velocity
B + Anti-Chase
C + VWAP quality
D + Market Gate
E + Sector / Relative Strength
F + Phase
G + Setup / Trigger
H + RR Gate
I full reproducible Sky Day Trading v1.4

Primary decision metric: after-cost expectancy.
Secondary: PF, Max DD, stability, Avg Win/Loss, MAE/MFE, win rate, turnover, capacity.

## Blocker
Promotion-grade full-market synchronized intraday history is unavailable. Existing ~100-symbol artifact cannot reconstruct Top100_t and may not be used to claim superiority.

## Routing
W3A -> resolve data coverage / causal Top100 reconstruction.
W2 -> run preregistered comparison after dataset passes fail-closed PIT gate.
W4 -> collect prospective Shadow/Paper observations when live causal Top100 construction is available.
W0 -> adjudicate only after W2 + W4 + P0-R evidence.
