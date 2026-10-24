# Sky V2.1 Anti-Chase Proxy Ablation

- Date: 2026-10-24
- Status: RESEARCH EVIDENCE ONLY
- Trade ledger: `sky_swing_v18_addon_trade_comparison.csv`
- Trades: 1,161
- Outcome: `base_net_R` (cost-adjusted research outcome)
- Objective: test whether simple Entry-vs-Trigger deviation is a valid Anti-Chase gate.

## Tested proxy

`chase_pct = max((entry - trigger) / trigger, 0)`

This proxy uses only entry-time information and does not use any future-path fields.

## Distribution

- 1,022 / 1,161 trades entered exactly at Trigger.
- 139 trades entered above Trigger.
- 90th percentile chase_pct: ~0.16%
- 95th percentile: ~0.47%
- 99th percentile: ~1.19%
- Maximum: ~2.28%

This means the historical ledger contains only a narrow range of Entry-vs-Trigger deviations.

## Bucket results

| Entry above Trigger | Trades | Net Expectancy | PF | Win rate |
|---|---:|---:|---:|---:|
| 0% | 1,022 | +0.221R | 1.656 | 42.3% |
| 0.1–0.25% | 44 | **+0.417R** | **2.498** | 52.3% |
| 0.25–0.5% | 41 | +0.120R | 1.323 | 41.5% |
| 0.5–1.0% | 39 | +0.342R | 2.059 | 43.6% |
| >1.0% | 15 | +0.124R | 1.313 | 33.3% |

## Cap surface

| Max chase_pct | Trades | Net Expectancy | PF |
|---|---:|---:|---:|
| 0% | 1,022 | +0.221R | 1.656 |
| 0.25% | 1,066 | +0.229R | 1.685 |
| 0.50% | 1,107 | +0.225R | 1.671 |
| 0.75% | 1,133 | +0.227R | 1.678 |
| 1.00% | 1,146 | +0.229R | 1.683 |
| All | 1,161 | +0.227R | 1.678 |

No tested Entry-vs-Trigger cap produced a material, stable improvement over baseline.

## Year-by-year warning

The sign is unstable:

- 2021 and 2022: above-trigger entries underperformed.
- 2023: roughly similar.
- 2024, 2025, 2026: above-trigger entries outperformed the exact-trigger group.

Therefore, Entry-vs-Trigger deviation is not a stable standalone definition of chasing.

## Interpretation

### What this supports
- Small Entry-vs-Trigger deviation can be useful as a **ranking / entry-quality feature**.
- It should not be promoted as a Hard Anti-Chase veto by itself.
- A minor breakout confirmation above Trigger is not automatically "追高".

### What this rejects
Do NOT define Anti-Chase as:
- entry > trigger
- entry more than X% above trigger, using the tested narrow range alone

The historical distribution and cost-adjusted outcomes do not support that simplification.

## Why the proxy is incomplete

True Anti-Chase requires contemporaneous context that this ledger does not contain:

- distance from VWAP
- intraday / daily price extension
- gap from prior close
- current-day return
- RVOL / abnormal volume
- breakout bar size
- upper resistance distance
- ATR-normalized extension
- spread / liquidity
- phase / setup type
- market / sector relative strength

These are the actual variables needed to distinguish healthy confirmation from late-stage chasing.

## Proposed Historical Replay Anti-Chase contract

Persist at decision time:

- entry_vs_trigger_pct
- price_vs_vwap_pct
- vwap_slope
- day_return_pct
- gap_pct
- atr14
- price_extension_atr
- breakout_bar_atr
- rvol
- volume_zscore
- resistance_distance_pct
- stop_distance_pct
- stop_distance_atr
- spread_pct
- phase
- setup
- market_regime
- sector_rs
- stock_rs

## Candidate composite rule for research

Do not promote yet. Test a composite score such as:

- VWAP deviation risk
- ATR extension risk
- day-return extension
- resistance proximity
- structural stop distance
- liquidity/spread risk

Then compare:
- Base
- Trigger-slip only
- VWAP only
- ATR-extension only
- Stop-distance only
- Composite Anti-Chase

Metrics:
- base_net_R / execution-adjusted R
- PF
- Net Expectancy
- MDD
- MAE
- MFE
- tail-loss frequency
- sample count
- turnover / cost drag

## Promotion status

**Trigger-slip Anti-Chase: REJECTED AS STANDALONE HARD GATE**

**Composite Anti-Chase: DATA INCOMPLETE — NEXT VALIDATION**
