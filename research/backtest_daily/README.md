# Daily (隔日方向) backtest framework — DRAFT

Status: **framework only. No strategy is approved and no results are reported.**

## What is here
- `config.py` — frozen cost model (0.45% primary / 0.65% stress) and risk profile values taken from `docs/SKY_RISK_PROFILE.md`.
- `engine.py` — next-open entry, stop-first same-bar rule, gap fills, time exit, 1R + notional position sizing.
- `metrics.py` — after-cost expectancy, profit factor, win rate, max drawdown.
- `tests/test_engine.py` — 13 offline unit tests with synthetic bars (no network, no API key).

## What is NOT here (on purpose)
- No Fugle data fetch. The historical endpoint and its rate limits must be verified against the official Fugle docs before a fetch script is written.
- No strategy rule. The signal rule must be pre-registered and approved first (Validation Protocol Gate 1).
- No run on real data.

## Governance notes
- Time splits are in `config.py`. 2026 data up to 2026-10-22 was already used as research test, so the 2026 segment is labelled `research_test_2026`, **not fresh OOS**. Fresh OOS needs dates after the pre-registration date.
- Risk values follow `docs/SKY_RISK_PROFILE.md` (1R = 5,000). The 1R = 100,000 discussion is not applied until the profile is formally updated.

## Run the tests
```
cd research/backtest_daily
python3 -m unittest tests/test_engine.py
```
