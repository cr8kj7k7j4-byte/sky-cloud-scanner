# W5 Candidate Decision Ledger

> 所有正式 W5 判定都應留下紀錄。此 Ledger 不取代 SKY_SYSTEM_REGISTRY_V2_1.md 或 RESEARCH_FREEZE_REGISTRY.md。

## Decision schema

| Date | Candidate | Category | Status | Structural difference | PIT | OOS | Priority | Reason | W0 handoff |
|---|---|---|---|---|---|---|---|---|---|
| 2026-10-25 | Overnight-to-First-30m Reversal for Taiwan | Intraday / Open reaction | HOLD | 新 target timing：overnight state → first-30m reaction；非 MA/Top-N 微調 | UNKNOWN / blocked by intraday PIT dataset readiness | 可設計；2026 不得稱 fresh OOS | Medium | 有結構差異，但 PIT replay dataset 與 preregistered label 尚未完成 | Not yet |
| 2026-10-25 | Taiwan Dynamic Futures/ETF/Spot Lead-Lag State | Cross-market / Intraday | HOLD | 新 cross-market PIT data family + market-state architecture | UNKNOWN | 可設計 | Medium–High | timestamp causality、session、roll data contract 尚未驗證 | Not yet |
| 2026-10-25 | Taiwan Broker-Identity / Skill-Conditioned Flow | Participant flow / Intraday-Swing | HOLD | 新 identity-tagged participant-flow data family | UNKNOWN / hard data gate | 理論可設計 | Medium | historical PIT、vendor、license、identity stability 未確認 | Not yet |

## Current conclusion

- 三個 W7 inbound Candidate 均未被判定為 frozen-family duplicate。
- 三者也都尚未達到 `ACCEPT_FOR_PREREGISTRATION`。
- 原因不是策略一定無效，而是 Gate 0 / Data Feasibility / PIT 證據不足。
- 在 blocker 解除前不得先跑大量回測、調 threshold、選 horizon 或進 nonlinear ML。

## Recording rules
- REJECT_DUPLICATE：必須記錄對應 frozen/rejected family。
- REJECT_LOW_VALUE：必須記錄是 threshold / period / Top-N / weight / stop-target / cosmetic rename 哪一類。
- HOLD：必須記錄 blocker 與解除條件。
- ACCEPT_FOR_PREREGISTRATION：必須記錄 PIT、fresh OOS、baseline 與成本驗證方案。
- ARCHIVE：必須記錄封存理由與未來可重開條件。
- 不得使用 Production / Champion / Approved for live 等狀態。
