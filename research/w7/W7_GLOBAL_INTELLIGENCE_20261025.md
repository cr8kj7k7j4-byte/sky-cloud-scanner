# W7 Global Trading Intelligence — 2026-10-25

> Scope: external intelligence only. This document does not modify Production and does not authorize promotion.

## Governance checked
- SKY_SYSTEM_REGISTRY_V2_1.md
- research/RESEARCH_FREEZE_REGISTRY.md
- docs/SKY_VALIDATION_PROTOCOL_V1_0.md
- docs/SKY_V2_1_BASELINE_FREEZE_20261025.md
- docs/SKY_MASTER_CONTROL_STATUS_20261025.md
- docs/SKY_PARALLEL_WORKSTREAMS.md

## Freeze constraints respected
Do not reopen by local retuning:
- P0-S 5m Breakout
- Fixed-time Intraday Ranking
- Event-driven Intraday Ranking / Catalyst Stack
- Transparent Intraday ML Ensemble
- Weak-Regime Mean-Reversion
- Low-vol Market-residual Long-only
- Stage 7A Broader Market Alpha
- VNext Residual Ranking Baseline v1

## 10 intelligence tracks — first-pass disposition

| Track | First-pass finding | W7 disposition |
|---|---|---|
| Intraday Regime Router | Regime descriptors can help segment behavior, but regime-only alpha evidence is mixed. Use only as conditioning/context, not a standalone strategy. | RESEARCH_MORE |
| Order Flow / Microstructure | Strong structural relevance; requires L2/tick/PIT and belongs downstream to execution/microstructure validation. | RESEARCH_MORE |
| ORB with Regime Filters | High overlap risk with frozen breakout family unless materially new target/data/execution architecture is defined. | REJECT_DUPLICATE |
| Gap / Overnight Reversal | Overnight return negatively predicting first-half-hour return is structurally distinct and directly testable. | SEND_TO_W5 |
| Futures / ETF Lead-Lag | Taiwan evidence supports dynamic lead-lag / price discovery effects; potentially useful as market-state input. | SEND_TO_W5 |
| Broker Flow | Taiwan-specific broker identity/flow evidence may provide independent information, but historical PIT data access is the key gate. | SEND_TO_W5 |
| Execution Alpha | High value but should be handled as execution architecture / W6 after governance intake, not as a direction signal. | RESEARCH_MORE |
| Market-neutral / Residual | Existing VNext Residual Ranking v1 is frozen; any successor needs a materially new formulation. No current candidate promoted from W7. | REJECT_DUPLICATE |
| Cross-sectional Ranking | Existing ranking families already carry negative evidence; no simple re-ranking candidate is justified. | REJECT_DUPLICATE |
| ML Ranking vs deterministic | External evidence does not justify nonlinear escalation; regime-aware ML does not automatically outperform. | REJECT_DUPLICATE |

## Sources screened
1. Iwanaga & Sakemoto (2026), "Does overnight return predict the first half-hour return for U.S. market indices?", SSRN.
2. Chang (2026), "Skill-Conditioned Argmax Aggregation for Broker Order Flows: Evidence from Taiwan Equities", SSRN.
3. Lee, Wu & Yang (2013), "Informed Futures Trading and Price Discovery: Evidence from Taiwan Futures and Stock Markets".
4. Finance Research Letters (2026), "Trading on delay: Information frictions and cross-market arbitrage in index futures".
5. Journal of Behavioral and Experimental Finance (2021), "Intraday time-series momentum and investor trading behavior" — Taiwan ETF evidence.
6. Pacific-Basin Finance Journal (2023), "Shorting flows and return predictability in Taiwan".
7. Pascual Miralles & Alfeus (2026), "Do Market Regimes Improve Machine-Learning Stock Ranking?", SSRN.
8. Bianchi, Jiao & Ma (2026 revision), "Transaction Costs and the Stochastic Discount Factor", SSRN.

## Vendor / platform first pass
### Fugle
- Taiwan stocks + futures/options real-time WebSocket and REST.
- Historical stock coverage: listed/OTC stocks back to 2010; futures minute bars from 2017-06.
- Developer: 300 subscriptions / 2 connections; Advanced: 2000 subscriptions / 2 connections.
- Historical API rate limit is 60/min across plans.
- Current action: TRIAL_FIRST. Use current capability to validate whether required PIT granularity is adequate before paying for larger subscription capacity.

### Databento
- Strong global tick/L1/L2/L3 (MBO) and PIT instrument definitions.
- No Taiwan-core advantage identified in first pass.
- Current action: NOT_NEEDED for Sky Taiwan core; keep as W6/global microstructure research option.

### QuantConnect / LEAN
- Flexible custom fill/fee/slippage models and live brokerage integrations.
- Sky already has its own validation architecture and current bottleneck is PIT evidence, not lack of another backtest engine.
- Current action: NOT_NEEDED now.

### Sierra Chart
- Strong tick/market-depth replay on supported global venues.
- Does not directly solve Taiwan historical L2/PIT data gap.
- Current action: RESEARCH_ONLY for W6 methodology benchmarking.

## W7 conclusion
Do not expand modules. The highest-value external intelligence candidates are:
1. Overnight-to-open reversal.
2. Taiwan futures/ETF/spot dynamic lead-lag.
3. Taiwan broker-flow identity/skill aggregation, conditional on PIT data feasibility.

Production remains unchanged.
