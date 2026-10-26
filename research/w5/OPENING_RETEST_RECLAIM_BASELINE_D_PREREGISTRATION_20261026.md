# W5 Preregistration — Opening Retest Reclaim Baseline D

Date: 2026-10-26
Owner: W5｜Sky Candidate Strategy Lab
Status: PREREGISTERED_STRUCTURAL_CHALLENGER
Production impact: NONE

## 1. Research question

After an early opening impulse, does waiting for price to retest the session open and then causally reclaim it improve after-cost expectancy versus entering the first opening acceleration wave?

Baseline D is a distinct setup architecture. It does not retune Baseline C thresholds after seeing C's negative result.

## 2. Data

Source dataset:
- governed PIT-active Taiwan equity universe;
- whole-market 1-minute intraday candles;
- source workflow run: 40267006806;
- period: 2026-01-01 through 2026-10-22;
- Asia/Taipei timestamps;
- no Top100 eligibility gate;
- no TWD 100 price ceiling.

The existing compact schema OPENING_ACCELERATION_1M_COMPACT_V1_1_4TICK_STOP is reused. No new market-data download is required.

## 3. Observation / execution window

Observation window:
- 09:00 through 09:15.

Causal convention:
- 09:00 initializes the session open.
- A decision at minute t may use only completed bars through t-1.
- Entry proxy is the open of minute t.
- No same-minute close is visible before completion.
- Earliest practical reclaim entry is determined by the completed launch → retest → reclaim sequence.

## 4. Frozen structural sequence

For each symbol/session, all three states must occur in order using completed 1-minute bars.

### State A — Initial launch
A completed bar must:
- close > session open; and
- high >= the 4th legal Taiwan tick above session open.

This establishes that the stock actually produced an opening impulse before the retest.

### State B — Retest
After State A, a later completed bar must:
- low <= session open.

The retest may close above or below the open. No entry occurs on the retest itself.

### State C — Reclaim
After State B, a later completed bar must:
- close > session open.

Only after this completed reclaim may the next minute be considered for entry.

The launch, retest and reclaim must be causally ordered. A single bar cannot satisfy multiple states.

## 5. Entry

At decision minute t immediately after a completed reclaim:
- entry proxy = minute-t open;
- entry must be strictly above session open;
- entry must be <= the 4th legal tick above session open;
- otherwise classify MISSED_4TICK_NO_CHASE / NO_ENTRY_OPEN_ZONE;
- same symbol max one trade per session.

No later retry after a missed reclaim entry in Baseline D v1.

## 6. Stop

Mandatory session-open stop:
- after entry, first 1-minute bar with low < session open triggers exit;
- fill proxy = min(session open, trigger-bar open) when trigger-bar open exists;
- no averaging down;
- no stop widening.

## 7. Exit / evaluation

Primary economic horizon:
- 60 minutes, stop-aware.

Also report:
- 30-minute stop-aware return;
- session-close return;
- MFE / MAE;
- +5% post-entry excursion;
- near-limit proxy;
- open-stop rate;
- decision-minute distribution.

No profit-target optimization.

## 8. Cost model

Primary round-trip cost: 0.45%.
Stress round-trip cost: 0.65%.

Gross-positive but after-cost-negative fails.

## 9. Selection / portfolio simplification

This baseline tests the setup architecture, not a cross-sectional optimizer:
- every symbol/session that completes the frozen launch → retest → reclaim sequence and has a valid causal entry is an evaluable trade;
- no Top-N, no score weights, no threshold search;
- same symbol max one trade/day.

Portfolio concurrency is not used to rescue signal-level economics. If signal-level evidence survives, portfolio/capacity work is a later gate.

## 10. Decision rule

PROMOTE_CANDIDATE_TO_W4 only if:
- n >= 200;
- 0.45% after-cost expectancy > 0;
- 0.45% PF > 1;
- 0.65% stress is not catastrophic;
- no single symbol > 20%;
- 2026 H1 and H2 are not structurally contradictory.

HOLD for insufficient sample or mixed stability.

REJECT if:
- 0.45% expectancy <= 0; or
- PF <= 1; or
- broad instability is evident.

Promotion, if any, is W4 Shadow/Paper only. Production remains unchanged.
