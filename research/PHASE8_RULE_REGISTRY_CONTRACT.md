# Sky 100 Phase 8｜P0-G Rule Registry + Champion Configuration

## 目的

Phase 8 將規則與正式配置納入 P0-G Governance & Registry，讓每次升版、降版與回滾都可追溯。

## Registry 最低欄位

每條 Rule 必須有：
- rule_id
- version
- status
- production_enabled
- owner_module
- rationale
- evidence
- validation
- rollback
- fingerprint
- created_at

## Champion Configuration

正式 Champion 必須明確鎖定：
- 每條核心 Rule 的版本
- Model version
- Feature schema version
- effective_from
- rollback_to

## 核心 Rule

- market_gate
- sector_rs_gate
- anti_chase_gate
- phase_gate
- setup_gate
- trigger_gate
- rr_gate

## Promotion Gate

正式升版必須有：
- Walk-forward
- OOS
- Cost Stress
- Leakage Check
- Survivorship Review
- Regime Stability
- Paper Trading
- Sample Sufficiency

## Rollback

若 Production 發生以下任一情況，必須允許回滾至上一個 Champion：
- 風控異常
- MDD 超過治理門檻
- 資料品質重大異常
- 交易成本假設失效
- Regime 失效證據
- 監控/執行鏈異常

Registry 只負責治理與可追溯性，不代表任何規則具有獲利保證。
