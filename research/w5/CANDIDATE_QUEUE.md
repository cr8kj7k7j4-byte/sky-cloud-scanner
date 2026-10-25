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
| Overnight-to-First-30m Reversal for Taiwan | W7_INBOUND | 新 target + 新 causal timing architecture；待 W5 Intake | Duplicate/Low-value Gate → PIT feasibility → preregistration decision |
| Taiwan Dynamic Futures/ETF/Spot Lead-Lag State | W7_INBOUND | 新 cross-market PIT data family；待 W5 Intake | Data sync/PIT audit → W5 decision |
| Taiwan Broker-Identity / Skill-Conditioned Flow | W7_INBOUND | 新 identity-tagged data family；資料取得為 hard gate | Vendor/data feasibility → W5 decision |

## Inherited blocked research context

以下項目屬正式 Registry 既有研究狀態，不在 W5 擅自改狀態：
- Revenue MoM 5D — PRE_PIT_CANDIDATE
- Revenue YoY Acceleration 5D — PRE_PIT_CANDIDATE
- Revenue YoY 5D — HOLD_CONCENTRATION_FAIL
- Revenue YoY 20D — HOLD_CONCENTRATION_FAIL

W5 可研究其「新的結構性解法」，但不得以 threshold、Top-N、weight 或 stop/target 微調救活。
