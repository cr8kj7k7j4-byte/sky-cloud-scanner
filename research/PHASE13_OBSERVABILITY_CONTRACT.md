# Sky 100 Phase 13｜Observability + SLO/SLA + Health Dashboard

## 目的

讓 Sky 可以量化自身健康狀態，並在看不見或不可信時自動禁止新進場。

## V1 服務

- TWSE
- TPEx
- Fugle
- P0-R Risk Engine
- P0-A Alert Engine
- State Store

## 指標

- Availability
- Latency
- Data Freshness
- Error Rate
- Success Rate

## SLO 初版

Critical：
- TWSE
- TPEx
- Risk Engine
- State Store

Non-critical：
- Fugle
- Alert Engine

Critical SLO 任一失敗：
- mode = LOCKDOWN
- new_entries_allowed = false

非 Critical SLO 失敗：
- mode = OBSERVE_ONLY
- new_entries_allowed = false

全部通過：
- mode = NORMAL

任何模式都不授權自動 Live Activation。

## Dashboard

至少顯示：
- 服務狀態
- 可用率
- 延遲
- Freshness
- SLO 是否通過
- Critical Failure
- 系統模式
- 新進場是否允許

SLO 是工程服務品質門檻，不是交易績效指標。
