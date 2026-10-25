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
| — | — | 尚無新 Candidate 通過 Intake | 等待真正具有結構差異的新想法 |

## Inherited blocked research context

以下項目屬正式 Registry 既有研究狀態，不在 W5 擅自改狀態：
- Revenue MoM 5D — PRE_PIT_CANDIDATE
- Revenue YoY Acceleration 5D — PRE_PIT_CANDIDATE
- Revenue YoY 5D — HOLD_CONCENTRATION_FAIL
- Revenue YoY 20D — HOLD_CONCENTRATION_FAIL

W5 可研究其「新的結構性解法」，但不得以 threshold、Top-N、weight 或 stop/target 微調救活。
