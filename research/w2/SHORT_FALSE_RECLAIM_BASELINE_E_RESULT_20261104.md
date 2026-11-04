# W2 | False-Reclaim Short Baseline E — recovered backtest decision

- Evaluation date: 2026-11-04 (Asia/Taipei)
- Strategy: False-Reclaim **SHORT** Baseline E (2026-10-26 preregistration)
- Research period: 2026-01-01 to 2026-10-22; reused historical research data, NOT untouched OOS.
- Source data: historical PIT universe; original 20 shard download jobs from GitHub Actions run 40329668748.
- Successful recovery run: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41752940845
- Result artifact: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41752940845/artifacts/13287186847
- Recovery engineering commit: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/commit/2f11254abfaac0516fd9add712eeab7ae688062d

## Verified results (60-minute stop-aware short return)

| Metric | Observed |
| --- | ---: |
| Historical input files | 1,996 |
| Evaluable signal trades | 10,732 |
| Unique symbols | 1,346 |
| Max single-symbol share | 0.2836% |
| Gross expectancy per trade | +0.224093% |
| Gross profit factor | 1.7920 |
| 0.45% cost expectancy | **-0.225907%** |
| 0.45% profit factor | **0.6402** |
| 0.65% stress expectancy | **-0.425907%** |
| 0.65% profit factor | **0.4584** |
| 2026 H1 (0.45% cost) | -0.229811% (6,656 observations) |
| 2026 H2 (0.45% cost) | -0.219531% (4,076 observations) |
| Opening-price stop hit rate | 78.5506% |

## Decision and boundaries

**REJECT_AFTER_COST_EXPECTANCY**. The preregistered main economic gate is failed: net expectancy < 0 and PF < 1 in both halves. No research-based trade signal, Paper/Live promotion, or Production change is authorized. Do not rescue by locally retuning stop/target, timing, thresholds, Top N, weights or indicator periods. If a structurally different hypothesis is proposed, require new preregistration, PIT short eligibility/borrowability, transaction cost/capacity evidence, train/validation/OOS separation and the full governance protocol.

**Caveats:** PIT short eligibility and actual borrowability have NOT been validated; therefore these results are economic signal proxies, not executable realized trades. Historical 2026 data reused for this backtest cannot be called fresh OOS. The `Opening Acceleration Baseline E Dual-Path` workflow is a separate LONG-side experiment and should not be conflated with this short strategy.

Status: W2 evidence **COMPLETE / REJECTED**; formal freeze-registry update belongs to W0/P0-G governance review. No Production modification.
