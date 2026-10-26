# W5 Preregistration — Opening Acceleration Baseline E / Dual-Path False-Start Filter

Date: 2026-10-27
Owner: W5｜Sky Candidate Strategy Lab
Status: PREREGISTERED_STRUCTURAL_CHALLENGER
Production impact: NONE
Parent evidence:
- Baseline C / Run 40267006806 / REJECT_AFTER_COST_EXPECTANCY
- Baseline D false-start reclaim / Run 40329437017 / REJECT_AFTER_COST_EXPECTANCY

## 1. Research question

Can a causal dual-path entry architecture preserve strong opening leaders that never revisit the session open while still rejecting weak pullback failures?

The two paths are:

A. `initial acceleration → no pullback → strength follow-through → next-bar entry`

B. `initial acceleration → pullback to session open → reclaim follow-through → next-bar entry`

This is not a retune of Baseline D. It changes the branch structure so "no-pullback strength" is no longer automatically discarded.

## 2. Frozen seed population

Use exactly the frozen Baseline C selected seed population:
- full PIT-active Taiwan equity universe;
- causal 09:01–09:15 decision clocks;
- same acceleration features / equal-weight score;
- Top 3 qualified symbols per decision minute;
- same-symbol max one seed per session;
- Baseline C seed must satisfy its existing 4-tick anti-chase gate.

No changes to ranking weights, Top-N, acceleration thresholds, costs, or seed construction.

## 3. Common causal convention

For each Baseline C seed at t0:
1. Do not enter at t0.
2. Observe only completed 1-minute bars after t0.
3. Entry may occur only at the open of the next 1-minute bar after confirmation.
4. Entry must occur no later than 09:15.
5. Entry must remain in `(session_open, fourth_legal_tick_above_open]`.
6. If next-bar entry is above the 4th tick, classify as `MISSED_4TICK_NO_CHASE`.
7. No same-bar confirmation/entry and no future-bar information may be used.

## 4. Path A — No-Pullback Strength

Before any completed bar has touched session_open:

A confirmation occurs when a completed bar:
- has low > session_open;
- has close > session_open;
- has close > the immediately preceding completed bar high.

Then enter at the next 1-minute bar open, subject to the common causal/4-tick gates.

If a bar touches session_open before Path A confirms, Path A is permanently disabled and control passes to Path B.

No alternative follow-through threshold, distance, or lookback search is allowed.

## 5. Path B — Pullback Recovery

Once any completed post-seed bar has low <= session_open:

A reclaim confirmation occurs on the first later completed bar whose:
- close > session_open; and
- close > the immediately preceding completed bar high.

Then enter at the next 1-minute bar open, subject to the common causal/4-tick gates.

If no such confirmation appears early enough for entry by 09:15, there is no trade.

## 6. Frozen branch priority

Path A has priority only while no pullback has occurred.
Once a pullback occurs, only Path B is allowed.
There is no path switching after a confirmation has fired.

## 7. Exit and invalidation

After entry:
- first future 1-minute low < session_open triggers the same structural open-stop proxy;
- primary economic horizon: 60-minute stop-aware exit;
- secondary: 30-minute and session close;
- report MFE, MAE, +5% right-tail, near-limit proxy.

No stop/target optimization.

## 8. Cost model

- Primary round-trip: 0.45%.
- Stress: 0.65%.

## 9. Required diagnostics

Report separately for Path A, Path B, and combined:
- selected / evaluable trades;
- gross expectancy / PF;
- 0.45% expectancy / PF / win rate;
- 0.65% expectancy / PF;
- open-stop rate;
- MFE / MAE;
- +5% rate;
- H1 / H2;
- symbol concentration.

Also report seed disposition:
- `PATH_A_ENTRY`
- `PATH_B_ENTRY`
- `PATH_A_MISSED_4TICK`
- `PATH_B_MISSED_4TICK`
- `PULLBACK_NO_RECLAIM`
- `NO_CONFIRMATION_BY_ENTRY_WINDOW`

## 10. Primary comparison questions

1. Does Path A retain materially more of C's +5% winners than Baseline D?
2. Does Path B continue to reject the high-failure pullback-no-reclaim population?
3. Does combined E improve after-cost expectancy versus C and D?
4. Are any gains stable across H1/H2 rather than isolated to one period?

## 11. Decision rule

`PROMOTE_CANDIDATE_TO_W4` only if combined:
- >=200 evaluable trades;
- 0.45% after-cost expectancy > 0;
- 0.45% PF > 1;
- no single symbol >20%;
- H1/H2 are not structurally contradictory;
- 0.65% stress is not catastrophic.

`HOLD` for incomplete causal evidence or insufficient sample.

`REJECT_AFTER_COST_EXPECTANCY` if 0.45% expectancy <=0.

`REJECT_AFTER_COST_PF` if expectancy >0 but PF <=1.

Any survivor goes only to W4 Shadow/Paper. Production remains unchanged.

## 12. OOS governance

2026-01-01 through 2026-10-22 is reused structural research data and is NOT fresh OOS.
No result from this run may be described as untouched OOS.
Future confirmation requires frozen rules plus Forward Shadow/Paper evidence.
