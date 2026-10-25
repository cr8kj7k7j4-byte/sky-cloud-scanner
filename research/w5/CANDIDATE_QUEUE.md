# W5 Candidate Queue

> 這是 W5 的研究入口佇列，不是 Production Strategy Registry。

## Queue policy
1. 新想法先進 Intake。
2. 先跑 Duplicate / Low-value Gate。
3. 只有 `ACCEPT_FOR_PREREGISTRATION` 才可建立 Pre-registration。
4. W5 不自行送入 Production。
5. 通過者交 W0 決定是否送 W1 / W2。
6. 目前 Master Control 明確要求：Evidence completion → Shadow/Paper → Portfolio/Risk → Production hardening → New Alpha Research。

## Current queue — 2026-10-25

目前 **無 W5 新 Alpha Candidate 被授權為 active research**。

| Candidate | W5 Status | Duplicate / Low-value | PIT feasibility | Pre-registration | Next step |
|---|---|---|---|---|---|
| Overnight-to-First-30m Reversal for Taiwan | HOLD | PASS structural novelty | PARTIAL；Fugle minute history + PIT universe 可用，但 canonical intraday PIT replay 仍 DATA_BLOCKED | NOT YET | W3A replay PASS 後優先重審 |
| Taiwan Dynamic Futures/ETF/Spot Lead-Lag State | HOLD | PASS structural novelty | PARTIAL；minute data 可得，但 synchronized timestamp / session / roll contract 尚缺 | NOT YET | W3A/W6 建立 cross-market timestamp contract |
| Taiwan Broker-Identity / Skill-Conditioned Flow | HOLD | PASS structural novelty | UNKNOWN / HARD DATA GATE；官方日頻資料存在，但 sample/schema/branch lifecycle/PIT mapping 未驗證 | NOT YET | DO_NOT_BUY NOW；先驗證 sample/schema/branch continuity |

## Current formal disposition
- `ACCEPT_FOR_PREREGISTRATION`: 0
- `HOLD`: 3
- `REJECT_DUPLICATE`: 0
- `REJECT_LOW_VALUE`: 0
- `ARCHIVE`: 0

Formal adjudication:
- `research/w5/W7_INBOUND_ADJUDICATION_20261025.md`

## Inherited blocked research context

以下項目屬正式 Registry 既有研究狀態，不在 W5 擅自改狀態：
- Revenue MoM 5D — PRE_PIT_CANDIDATE
- Revenue YoY Acceleration 5D — PRE_PIT_CANDIDATE
- Revenue YoY 5D — HOLD_CONCENTRATION_FAIL
- Revenue YoY 20D — HOLD_CONCENTRATION_FAIL

W5 可研究其「新的結構性解法」，但不得以 threshold、Top-N、weight 或 stop/target 微調救活。

## Intake files
- `research/w5/intake/OVERNIGHT_FIRST30M_REVERSAL_TAIWAN.md`
- `research/w5/intake/TAIWAN_DYNAMIC_CROSSMARKET_LEADLAG.md`
- `research/w5/intake/TAIWAN_BROKER_IDENTITY_FLOW.md`
