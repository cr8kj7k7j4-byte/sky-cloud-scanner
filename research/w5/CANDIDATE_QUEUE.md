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

| Candidate | W5 Status | Reason | Next step |
|---|---|---|---|
| Overnight-to-First-30m Reversal for Taiwan | HOLD | 有新 target/timing 結構差異，但 canonical intraday PIT replay dataset 尚未完成，target/label 尚未預註冊 | W3A 完成 PIT replay dataset 後重新檢查 fresh OOS 與 preregistration readiness |
| Taiwan Dynamic Futures/ETF/Spot Lead-Lag State | HOLD | 新 cross-market PIT data family，但同步 timestamp、session、roll data contract 尚未成立 | W3A/W6 驗證同步資料、timestamp causality、roll/session architecture |
| Taiwan Broker-Identity / Skill-Conditioned Flow | HOLD | 新 identity-tagged data family，但歷史 PIT、授權、vendor 可得性皆未確認 | W7/W3A 做 vendor/data feasibility；資料不可得則 ARCHIVE |

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
