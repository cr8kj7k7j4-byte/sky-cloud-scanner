# Sky V2.1 Ablation Matrix — Ranking Proxy

- Date: 2026-10-24
- Status: RESEARCH EVIDENCE ONLY
- Dataset: `sky_swing_v17_corrected_continuous.csv`
- Rows: 1,161
- Observed entry-date range in the file: 2021-08-05 to 2026-10-20
- Outcome field: `v17_R`

## Method

For every entry date, candidates were ranked only with information already available in the ledger at entry time:

1. `fresh_days` = entry_date - event_date (lower is better)
2. `trigger_slip_pct` = abs(entry - trigger) / trigger (lower is better)
3. `stop_pct` = original stop distance / entry (lower is better)

Each factor was converted to a same-day percentile rank, then equal-weighted.
Top N was selected within each entry date.

Important:
- `depth` and `extension` were NOT used because they contain future-path information.
- The CSV does not contain separate fee/tax/slippage fields, so this run does not independently reconstruct transaction costs. It compares all variants on the same `v17_R` outcome basis.

## Baseline

| Version | Trades | PF | Expectancy | Win rate | MDD |
|---|---:|---:|---:|---:|---:|
| Base | 1,161 | 2.132 | +0.322R | 47.6% | -29.65R |
| Full Ranking Top 5 | 1,049 | 2.223 | +0.337R | 48.3% | -22.78R |
| Full Ranking Top 3 | 902 | 2.274 | +0.346R | 48.4% | -16.83R |
| Full Ranking Top 2 | 760 | 2.270 | +0.349R | 49.9% | -13.19R |
| Full Ranking Top 1 | 506 | 2.241 | +0.348R | 49.8% | -10.36R |

## Single-factor ablation

### Top 3

| Factor | PF | Expectancy | MDD |
|---|---:|---:|---:|
| Freshness only | 2.235 | +0.341R | -17.96R |
| Trigger slippage only | 2.197 | +0.332R | -19.24R |
| Stop distance only | 2.248 | +0.342R | -18.58R |
| All 3 factors | 2.274 | +0.346R | -16.83R |

### Top 1

| Factor | PF | Expectancy | MDD |
|---|---:|---:|---:|
| Freshness only | 2.058 | +0.304R | -12.24R |
| Trigger slippage only | 2.341 | +0.352R | -12.37R |
| Stop distance only | 2.408 | +0.392R | -9.64R |
| All 3 factors | 2.241 | +0.348R | -10.36R |

## Remove-one-factor test

### Top 3

| Removed factor | Remaining factors | Expectancy |
|---|---|---:|
| none | freshness + slippage + stop | +0.346R |
| freshness | slippage + stop | +0.354R |
| slippage | freshness + stop | +0.352R |
| stop | freshness + slippage | +0.340R |

### Top 1

| Removed factor | Remaining factors | Expectancy |
|---|---|---:|
| none | freshness + slippage + stop | +0.348R |
| freshness | slippage + stop | +0.383R |
| slippage | freshness + stop | +0.358R |
| stop | freshness + slippage | +0.331R |

## 2024+ later-period robustness proxy

Baseline 2024+:
- PF 1.781
- Expectancy +0.233R
- MDD -29.65R

Top 1:
- Stop distance only: PF 2.342 / Expectancy +0.381R / MDD -9.64R
- Slippage + stop: PF 2.309 / Expectancy +0.364R / MDD -8.66R
- Freshness + stop: PF 2.209 / Expectancy +0.344R / MDD -11.34R
- All 3 factors: PF 2.189 / Expectancy +0.335R / MDD -10.36R
- Trigger slippage only: PF 2.129 / Expectancy +0.303R / MDD -12.37R
- Freshness only: PF 1.782 / Expectancy +0.233R / MDD -12.24R

## Year-by-year robustness

Stop-distance Top 3 improved annual Expectancy versus the unrestricted baseline in 5 of 6 calendar years in the ledger:
- 2021: +0.379R → +0.429R
- 2022: +0.154R → +0.228R
- 2023: +0.611R → +0.516R (worse)
- 2024: +0.411R → +0.444R
- 2025: +0.036R → +0.142R
- 2026: +0.218R → +0.269R

This is more robust than choosing Top 1 only; Top 1 has higher aggregate Expectancy but improves only 3 of 6 individual years.

## Research conclusions

### Strongest current evidence
1. **Opportunity Ranking itself adds value** versus taking every qualified signal.
2. **Lower original stop distance is the strongest of the three current proxy factors.**
3. **Top 3 is currently more robust than Top 1** when judged by year-to-year consistency.
4. **Trigger slippage has positive but secondary value.**
5. **Signal freshness is weak / unstable as a standalone factor**, especially for Top 1.

### What this does NOT prove
- It does not prove the optimal stop-distance threshold.
- It does not prove the factor weights.
- It does not prove execution-adjusted net expectancy after independently rebuilding fees/tax/slippage.
- It does not validate Market Regime, Anti-Chase, VWAP, Sector RS, Phase, or RR Gate because this ledger lacks the required contemporaneous fields.
- It does not authorize Production promotion.

## Proposed next ablation order

1. Stop-distance robustness surface (not a single best cutoff)
2. Market Regime
3. Anti-Chase
4. Sector Relative Strength
5. VWAP / entry-location quality
6. Net RR / execution-adjusted RR
7. Phase P1/P2/P3/P4
8. Combine only factors that survive OOS + Walk-forward + cost/slippage stress

## Promotion status

**PASS TO NEXT VALIDATION — NOT PRODUCTION**

The next production-grade test must use Historical Replay with contemporaneous market/sector/VWAP/volume/phase/RR fields and explicit transaction-cost assumptions.
