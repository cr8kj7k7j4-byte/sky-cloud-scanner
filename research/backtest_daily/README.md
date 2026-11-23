# BRK20 daily historical research — RESEARCH_ONLY / NOT PROMOTABLE

This is a separate historical **swing/day-ahead research experiment**, not Sky's
intraday position-sizing or live-trading engine. No automated orders or retired
simulated trading ledger are part of this workflow.

## What is implemented

- `fetch_fugle_daily.py`: manual-only Fugle historical daily candles downloader.
  Its historical candle and ticker-universe HTTP calls must obtain the shared
  GitHub-ref atomic claim with `SKY_PAID_ATOMIC_ENFORCE=1`. If the guard cannot
  claim, the request fails closed; HTTP 429 is not retried automatically.
  GitHub Actions must supply `GH_TOKEN` and `contents:write` to create the
  shared claim. No automatic schedule is enabled.
- `strategy.py`: pre-registered BRK20 signal rules.
- `engine.py`: historical next-open execution assumptions, 1R-based
  research sizing, stop/target/time-exit logic (no brokerage interface).
- `config.py`: frozen historical research assumptions including the
  0.45% primary / 0.65% stress round-trip cost scenarios.
- `metrics.py` and `run_backtest.py`: after-cost metrics and
  pre-registration checks.
- `tests/`: synthetic/offline checks; the repository Core CI also runs
  `tests/test_pipeline.py` against mocked network/atomic-claim behavior.

## Completed historical run — not an approved strategy

GitHub Actions run
[45026866316](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/45026866316)
completed successfully on main SHA
`25e6ade1cf5b9ec7457c9950e58c5801415bbc80`, with Artifact
`14758257210` (`backtest-daily-brk20`). Historical results after the
0.45% round-trip cost assumption had **negative expectancy** in the train,
validation, and 2026 research-test segments. Consequently BRK20 V1 is
**REJECTED for promotion** and remains research-only. The 2026 segment is
not fresh out-of-sample data. Do not rerun/download merely to reverse the
negative finding or tune this strategy into apparent profitability.

## Risk assumptions: separate the experiments

`config.py` records **BRK20 study Amendment A1**, including
`ONE_R_TWD = 100_000`. This is an archived BRK20 research assumption,
**not** authorization to raise Sky's intraday hard stop/risk budget. Sky's
intraday decision guard remains: single-trade loss cap NT$5,000, stock
capital cap NT$100,000, maximum 3 concurrent positions and daily net-loss
cap NT$10,000, with unknown live risk inputs failing closed. The archived
BRK20 configuration must not flow into the intraday engine, Production or
live sizing.

See `docs/SKY_RISK_PROFILE.md` and its historical A1 amendment for
research provenance. Do not edit pre-registered parameters or past results
as part of engineering hygiene.

## Offline verification

From the repository root:

```sh
python -m unittest research.backtest_daily.tests.test_engine research.backtest_daily.tests.test_pipeline
```

Or use the **existing** PR Core CI; no additional GitHub Workflow or paid
API request is required. The manual full-data workflow is **not** a harmless
test: it makes real Fugle requests, must not be dispatched solely to check
that CI is green, and requires W0 review of existing claims and outputs.
