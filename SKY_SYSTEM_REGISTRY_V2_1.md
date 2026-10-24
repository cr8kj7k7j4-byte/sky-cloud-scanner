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
| Revenue MoM 5D | RESEARCH | 1 | Passed initial Train/Valid/Test + 0.45% candidate gate; requires robustness, portfolio, walk-forward, PIT filing-time and paper/shadow validation. |
| Revenue YoY 5D | RESEARCH | 2 | Passed initial candidate gate; weaker Train edge than MoM 5D. |
| Revenue YoY Acceleration 5D | RESEARCH | 3 | Passed initial candidate gate; 2026 edge modest. |
| Revenue YoY 20D | RESEARCH | 4 | Passed initial candidate gate; requires concentration and annual/regime robustness checks. |
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
| Weak-Regime Mean-Reversion 15D | REJECTED | Signal-level edge failed to survive ranking/capacity/broad-basket portfolio implementation. |
| Fixed-time intraday ranking | REJECTED | OOS and post-cost evidence insufficient. |
| Event-driven intraday ranking / catalyst stack | REJECTED | OOS and post-cost evidence insufficient. |
| Transparent intraday ML feature ensemble | REJECTED | Negative post-cost Train/Valid/Test performance. |
| Low-vol market-residual long-only | REJECTED_AS_STRATEGY | Stable IC did not convert into robust tradable long-only edge. |

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
