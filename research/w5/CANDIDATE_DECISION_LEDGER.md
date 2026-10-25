# W5 Candidate Decision Ledger

> 所有正式 W5 判定都應留下紀錄。此 Ledger 不取代 SKY_SYSTEM_REGISTRY_V2_1.md 或 RESEARCH_FREEZE_REGISTRY.md。

## Decision schema

| Date | Candidate | Category | Status | Structural difference | PIT | OOS | Priority | Reason | W0 handoff |
|---|---|---|---|---|---|---|---|---|---|
| 2026-10-25 | Overnight-to-First-30m Reversal for Taiwan | Intraday / Open reaction | HOLD | 新 target timing：overnight state → first-30m repricing；非 MA/Top-N 微調 | PARTIAL / DATA_BLOCKED | 可設計；2026 不得稱 fresh OOS | 1 | W3A engineering complete，但現有 100-symbol 5m artifact 對 PIT universe 最大覆蓋僅約 4.8%–5.3%，低於 95%；whole-universe history / decision stream / sector / outcome / execution evidence 尚缺 | Not yet |
| 2026-10-25 | Taiwan Dynamic Futures/ETF/Spot Lead-Lag State | Cross-market / Intraday | HOLD | 新 cross-market PIT data family + synchronized market-state architecture | PARTIAL / DATA_BLOCKED | 可設計 | 2 | 分鐘資料存在，但 synchronized whole-universe history、clock synchronization、stale index、session、roll causality 尚未驗證 | Not yet |
| 2026-10-25 | Taiwan Broker-Identity / Skill-Conditioned Flow | Participant flow / 1D–5D | HOLD | 新 identity-tagged participant-flow data family + past-only skill conditioning | UNKNOWN / HARD DATA GATE | 理論可設計；尚未證實可執行 | 3 | 官方日頻資料存在但昂貴；sample/schema/branch continuity/PIT mapping/licensing reproducibility 未確認；DO_NOT_BUY NOW | Not yet |

## Latest W7 inbound adjudication

Formal review:
- `research/w5/W7_INBOUND_ADJUDICATION_20261025.md`

Final status:
- `ACCEPT_FOR_PREREGISTRATION`: 0
- `HOLD`: 3
- `REJECT_DUPLICATE`: 0
- `REJECT_LOW_VALUE`: 0
- `ARCHIVE`: 0

## Current conclusion
- 三個 W7 inbound Candidate 均通過 structural novelty / duplicate-low-value 初篩。
- 最新 W3A 證據確認：工程層已完成，但 promotion-grade 全市場歷史 PIT replay data 仍未達 Gate。
- 因 Gate 0 尚未滿足，三者均不得進正式 Pre-registration。
- Overnight candidate 資料門檻最低，若 whole-universe replay 解除 DATA_BLOCKED，優先重審。
- Lead-Lag 第二順位，先完成 cross-market timestamp/session/roll causality contract。
- Broker Flow 最後順位，且未取得 sample/schema/branch continuity/PIT mapping 前不得購買資料。
- blocker 解除前不得大量回測、調 threshold、選 horizon 或進 nonlinear ML。

## Recording rules
- REJECT_DUPLICATE：必須記錄對應 frozen/rejected family。
- REJECT_LOW_VALUE：必須記錄是 threshold / period / Top-N / weight / stop-target / cosmetic rename 哪一類。
- HOLD：必須記錄 blocker 與解除條件。
- ACCEPT_FOR_PREREGISTRATION：必須記錄 PIT、fresh OOS、baseline 與成本驗證方案。
- ARCHIVE：必須記錄封存理由與未來可重開條件。
- 不得使用 Production / Champion / Approved for live 等狀態。
