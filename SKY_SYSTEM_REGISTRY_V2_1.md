# Sky System Registry V2.1

> Canonical registry for production, research, rejected and evidence-only components.
> Engineering maturity labels do not imply profitability or future returns.

## Canonical architecture
P0-DATA → P0-K → P0-M → P0-EVT → P0-F → P0-AG → P0-S → P0-C → P0-O → P0-R → P0-X → P0-A → PMS → P0-L → P0-D → P0-G

Research namespaces:
- P0-ML: ML Research & Model Arena
- P0-LAB: Candidate Strategy Lab
- P0-PER: Personal Intelligence

## Production baselines

| Type | System / Model | Status | Notes |
|---|---|---|---|
| Production | Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP | ACTIVE | Current formal intraday baseline. No automatic promotion from research. |
| Production | Sky Swing V1.0 | ACTIVE | Current formal 3–20D long-only swing baseline. |

## Active research candidates

| Candidate | Status | Priority | Current evidence |
|---|---|---:|---|
| Revenue MoM 5D | PRE_PIT_CANDIDATE | 1 | Robustness gates passed, but 2023–2026 historical PIT audit found 0 / 87,588 company-months with verified MOPS filing timestamps (0.0000%). Promotion blocked until historical PIT coverage is resolved or the research window is redefined prospectively. |
| Revenue YoY 5D | HOLD_CONCENTRATION_FAIL | 4 | Primary/stress return gates passed, but top-5-symbol concentration exceeded threshold across splits. Do not promote. |
| Revenue YoY Acceleration 5D | PRE_PIT_CANDIDATE | 2 | Robustness gates passed, but 2023–2026 historical PIT coverage is 0.0000% (0 / 87,588 company-months). Remains pre-promotion research only; statutory-deadline proxies do not satisfy PIT. |
| Revenue YoY 20D | HOLD_CONCENTRATION_FAIL | 5 | Return gates passed, but concentration gate failed; do not promote despite high average returns. |
| Stage 7A Broader Market Alpha | RESEARCH | 5 | Pre-registered broader-market alpha study; no production impact until all gates pass. |

## Evidence-only features

| Evidence | Status | Use |
|---|---|---|
| vol20 market-residual relationship | FEATURE_ONLY | P0-F contextual feature; not a standalone long-only trigger. |
| drawdown20 residual evidence | FEATURE_ONLY | Research evidence only. |
| market breadth / relative strength | FEATURE_ONLY / CONTEXT | Market and ranking context; not standalone production alpha. |

## Rejected candidate families

| Candidate family | Status | Reason |
|---|---|---|
| P0-S 5m Breakout Candidate | REJECTED_OOS | Full 100-symbol validation passed; OOS n=9,111, PF=0.2033, Expectancy=-0.8018R at 0.45% round-trip cost. Do not promote to Paper Trading or live signal. |
| Weak-Regime Mean-Reversion 15D | REJECTED | Signal-level edge failed to survive ranking/capacity/broad-basket portfolio implementation. |
| Fixed-time intraday ranking | REJECTED | OOS and post-cost evidence insufficient. |
| Event-driven intraday ranking / catalyst stack | REJECTED | OOS and post-cost evidence insufficient. |
| Transparent intraday ML feature ensemble | REJECTED | Negative post-cost Train/Valid/Test performance. |
| Low-vol market-residual long-only | REJECTED_AS_STRATEGY | Stable IC did not convert into robust tradable long-only edge. |

## Historical Universe / Survivorship audit

- Live audit run: GitHub Actions #40176306214 (2026-10-25)
- Governed research window: 2023-01-01 onward
- Official sources healthy: TWSE_BASIC / TPEX_BASIC / TWSE_NEW / TPEX_NEW / TWSE_DELIST / TPEX_DELIST
- Official events: 2,499
- Windowed intervals: 2,116
- Window unresolved events: 0
- Interval validation: PASS
- Historical source coverage: PASS
- Current interval coverage: TPEx 100.0000%; TWSE 99.9081%
- PIT membership: 2023-12-31 = 1,904; 2024-12-31 = 1,960; 2025-12-31 = 2,028; 2026-09-30 = 2,069
- Historical Universe Gate: **PASS for the governed 2023+ research window**
- Survivorship bias is materially present when today's listing universe is used backward; historical studies in the 2023+ window must use the PIT universe.
- Full-history strict ledger still contains 163 pre-window unresolved events. This does not invalidate the 2023+ window gate and must not be described as complete all-history coverage.

## Historical Revenue PIT coverage audit

- Audit run: GitHub Actions #40168078271 (2026-10-25)
- Scope: TWSE + TPEx monthly revenue, 2023-01 through 2026-09
- Expected company-months: 87,588
- Verified MOPS filing timestamps: 0
- Historical PIT coverage: 0.0000%
- Gate: FAIL
- Governance consequence: Revenue candidates remain PRE_PIT_CANDIDATE.
- The MOPS latest-finance endpoint `t51sb10` supports latest records only; its more-info form exposed only `Stp` and `TK`, with no year/month/date history selector in the probed official interface.

## Promotion gate

A Research Candidate may become Production only after ALL of the following:
1. Point-in-time data alignment verified.
2. Leakage and survivorship checks pass.
3. Fixed, pre-registered rules.
4. Walk-forward validation passes.
5. OOS validation passes.
6. 0.45% primary and 0.65% stress-cost tests pass.
7. Portfolio-level PF / Expectancy / Max Drawdown are acceptable.
8. No catastrophic single-year or market-regime failure.
9. No single-stock or single-industry dependency.
10. Paper / shadow trading sample passes.
11. P0-R risk controls pass.
12. P0-G records Champion / Challenger promotion decision.

## Hard governance rules
- Research cannot bypass P0-C or P0-R.
- News and event evidence are not direct trade signals.
- No single Agent can create an executable trade.
- Missing evidence is UNKNOWN / VERIFY_BEFORE_TRADE.
- TRIGGERED does not mean automatic buy.
- Formal production baselines remain unchanged until promotion gates pass.
