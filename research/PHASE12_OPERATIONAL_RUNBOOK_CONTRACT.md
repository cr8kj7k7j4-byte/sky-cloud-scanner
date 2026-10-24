# Sky 100 Phase 12｜Operational Runbook + Rollback Drill + Incident Response

## 目的

正式定義 Sky 在資料、模型、風控、執行、監控或安全異常時，如何降級、停止新進場、回滾與復原。

## Incident Types

- DATA_STALE
- DATA_SOURCE_DOWN
- OFFICIAL_CHAIN_INCOMPLETE
- EXECUTION_COST_ANOMALY
- RISK_ENGINE_ANOMALY
- MODEL_DRIFT
- MONITORING_DOWN
- STATE_STORE_DOWN
- REGIME_MISMATCH
- SECURITY_SECRET_EXPOSURE

## Severity

- SEV0：全面 LOCKDOWN
- SEV1：DEFENSIVE / 禁止新進場，必要時 rollback
- SEV2：CAUTION / 禁止新進場
- SEV3：OBSERVE_ONLY

## Fail Safe

任何 degraded mode 都必須：
- 禁止新進場
- 禁止自動 live activation
- 保留現有持倉的風控與退出管理
- 記錄 incident 與 affected modules

## Rollback Drill

必須驗證：
- Config
- Rules
- Feature Schema
- Model
- Risk Policy
- Monitoring
- State Store
- Smoke Tests

## Recovery

即使所有復原條件通過：
- resume_new_entries_allowed = false
- production_reactivation_allowed = false

表示系統只能完成復原審查，真正恢復交易仍需獨立人工動作。
