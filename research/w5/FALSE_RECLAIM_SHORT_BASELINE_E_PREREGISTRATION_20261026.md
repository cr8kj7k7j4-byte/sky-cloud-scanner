# W5 Preregistration — False-Reclaim Short Baseline E

Date: 2026-10-26
Owner: W5｜Sky Candidate Strategy Lab
Status: PREREGISTERED_STRUCTURAL_CHALLENGER
Production impact: NONE
Primary window: 2026-01-01 through 2026-10-22

## 1. Research question

After an early long-side activation, session-open retest, reclaim above the session open, and a subsequent failure back below the session open, does a causal short entry have positive after-cost expectancy?

This is a new short-side entry architecture. It is not the arithmetic inverse of rejected Baseline C or D.

## 2. Causal event sequence

All conditions use completed 1-minute bars only.

1. PRIOR STRENGTH
   - at least one completed bar closes strictly above the session open.

2. OPEN RETEST
   - after prior strength, a completed bar has low <= session_open.

3. RECLAIM
   - after the retest, a later completed bar closes strictly above session_open.

4. FALSE RECLAIM / BREAKDOWN
   - after the reclaim, a later completed bar closes strictly below session_open.

5. SHORT ENTRY
   - entry proxy is the next 1-minute bar open;
   - latest legal entry time is 09:15;
   - entry must remain strictly below session_open;
   - to avoid chasing an already-extended breakdown, entry must be no lower than the fourth legal Taiwan tick below session_open.

One entry maximum per symbol/session.

## 3. Short stop

After entry:
- first future 1-minute bar with high > session_open triggers stop;
- fill proxy = max(session_open, trigger_bar_open) when available;
- no stop widening;
- no averaging.

## 4. Outcomes

Primary: 60-minute stop-aware short return.

Also report:
- 30-minute short return;
- session-close short return;
- short MFE / MAE;
- opening-price stop rate;
- downside excursion >= 5%;
- near-limit-down proxy.

Short gross return is calculated as:
entry_price / exit_price - 1.

## 5. Costs

Primary round-trip cost: 0.45%.
Stress cost: 0.65%.

## 6. Universe

Use governed PIT-active Taiwan equity universe.
No Top100 hard gate.
No TWD100 price cap.

Important execution caveat:
This first research pass measures the economic signal on the full PIT universe. It does not claim every historical symbol-session was actually short-sale/day-trade eligible or borrowable. Therefore even a positive result cannot be promoted directly to live trading without a point-in-time short-eligibility/borrowability gate.

## 7. Decision

REJECT if 0.45% after-cost expectancy <= 0 or PF <= 1.
HOLD if sample < 200 or if point-in-time short eligibility remains unresolved.
PROMOTE_CANDIDATE_TO_EXECUTION_VALIDATION only if:
- after-cost expectancy > 0;
- PF > 1;
- sample >= 200;
- half-year stability is acceptable;
- no symbol concentration > 20%;
- then separately validate historical short eligibility, borrow constraints, slippage and cover risk.

No Production change from this experiment alone.
