# Daily (隔日方向) backtest — Pre-registration v1

Status: **PRE-REGISTERED v1, NO RESULTS YET.**
Date: 2026-11-22
Authority: the repository owner delegated rule design and execution to the AI engineer on 2026-11-22 ("請自動執行，我要的是結果"). This is recorded in the commit history. Owner review is still required before any promotion (Gate 10).
Commit timestamp of this file is the evidence that rules were fixed before any result was produced.

## Goal
After-cost, stable excess return. Stability means the edge holds across the splits and the stress cost, not that every day is profitable (SKY_VALIDATION_PROTOCOL_V1_0).

## Universe (point-in-time)
- TSE and OTC common stocks.
- Close price <= 200 on the signal day.
- 20-day average daily volume >= 1,000,000 shares (liquidity floor, chosen to be conservative).
- Only symbols with complete daily bars for the lookback window.

## Long candidate: "BRK20"
Signal on the CLOSE of bar t:
1. close_t > max(high_{t-20..t-1})   (20-day breakout)
2. close_t > MA60_t                  (trend filter)

Entry: OPEN of bar t+1, only if open_{t+1} <= trigger * 1.005, where trigger = max(high_{t-20..t-1}).

Stop: low_t (signal-bar low). Invalid if stop >= entry.
R = entry - stop.
Target: entry + 2R.
Max hold: 5 bars after entry bar. Time exit at close of the 5th bar.
Same-bar stop/target: stop first (engine rule).
Gap fills: at open.

Ranking when more than 3 signals on one day: sort by close_t / max_high20 - 1, descending, keep top 3.

Position sizing: from config.py (1R = 100,000 per 2026-11-22 owner decision; see SKY_RISK_PROFILE amendment). Single-position notional cap for swing = 100,000.

## Short variant: NOT RUN IN v1
Shorting requires verified securities-lending availability and borrow fee, which are not available from the Fugle plan. Any short result would be "可成交性未驗證" and is excluded from the promotion decision.

## Costs
- Primary round-trip: 0.45%
- Stress round-trip: 0.65%
- Both must be reported. A rule that only works at zero or low cost is not promoted.

## Splits
- train: 2025-01-01 to 2025-06-30 (baseline reporting only; no parameter search)
- validation: 2025-07-01 to 2025-12-31 (single pre-registered variant; no tuning)
- research_test_2026: 2026-01-01 to 2026-10-22 (ALREADY USED IN PRIOR RESEARCH; NOT fresh OOS)
- Fresh OOS: only data dated after this file's commit date. Not yet available.

## Promotion thresholds (fixed now)
A candidate is "PASS_RESEARCH" only if ALL hold:
1. n >= 100 trades in validation AND n >= 100 in research_test_2026.
2. After-cost expectancy (primary cost) > 0 in validation AND research_test_2026.
3. Profit factor (primary cost) >= 1.2 in validation AND research_test_2026.
4. After-cost expectancy (stress cost) > 0 in validation.
5. No single calendar month contributes more than 50% of total net return (concentration check).

PASS_RESEARCH is not production. It only permits the next gate (fresh forward shadow test).

## Not covered in v1 (declared gaps)
- Walk-forward folds >= 3 (Gate 3): not yet done.
- Regime stability (Gate 4): no TAIEX regime data in v1. Declared gap.
- Rule ablation (Gate 6): not done. Single variant only.
- Portfolio constraints (Gate 7): per-trade simulation only; concurrency and portfolio heat not enforced in v1. Declared gap.
- Live validation: none.
