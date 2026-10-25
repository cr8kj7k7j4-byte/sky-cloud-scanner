# Sky 100 Roadmap — V2.1 Canonical

> 「100 分」定義為工程與驗證成熟度目標，不代表勝率、獲利率或未來報酬保證。
> Canonical namespace 以 /ARCHITECTURE_V2_1.md 與 /SKY_SYSTEM_REGISTRY_V2_1.md 為唯一基準。

## Production pipeline

P0-DATA Data Governance & Quality
→ P0-K Knowledge & Evidence Engine
→ P0-M Market Intelligence Engine
→ P0-EVT Event & Catalyst Intelligence
→ P0-F Feature Store / Feature Engine
→ P0-AG Agent Orchestration
→ P0-S Strategy Builder
→ P0-C Decision Engine
→ P0-O Opportunity Ranking Engine
→ P0-R Risk & Portfolio Management
→ P0-X Execution Engine
→ P0-A Alert & Monitoring Engine
→ PMS Position Management System
→ P0-L Trade Ledger & Outcome Engine
→ P0-D Learning & Validation Engine
→ P0-G Governance & Registry

Research namespaces:
- P0-ML = ML Research & Model Arena
- P0-LAB = Candidate Strategy Lab
- P0-PER = Personal Intelligence

## 已具備

- TWSE / TPEx 官方母池與來源健康檢查
- Fugle 深查介面
- P0-F 基礎 Feature Engine / Feature Store
- P0-M Market Regime / Relative Strength / market intelligence components
- P0-K Evidence Ledger / Knowledge Engine
- P0-EVT Event intelligence foundation
- P0-AG Agent Orchestration
- P0-S Strategy Builder
- P0-C Decision Engine
- P0-O Opportunity Ranking foundation
- P0-R Risk & Portfolio Engine
- P0-X Execution assistance foundation
- P0-A Alert / Monitoring foundation
- PMS / paper-trading related components
- P0-L Trade Logger / Outcome Engine
- P0-D Validation / Walk-forward framework
- P0-G Model Registry / Champion-Challenger governance foundation
- GitHub Actions core module tests
- Governed monthly revenue Evidence Dataset pipeline

## 目前正式 Production Baseline

- Sky Day Trading v1.4 Dynamic Capital Rotation / P0-C MVP
- Sky Swing V1.0

Research Candidate 不得自動覆蓋上述正式版本。

## 目前優先 Research Candidate

> 2026-10-25 更新：P0-S 5m Breakout 已完成 100 檔 OOS，OOS n=9,111、PF=0.2033、Expectancy=-0.8018R，正式標記 REJECTED_OOS，不進 Paper Trading。

1. Revenue MoM 5D — PRE_PIT_CANDIDATE
2. Revenue YoY Acceleration 5D — PRE_PIT_CANDIDATE
3. Stage 7A Broader Market Alpha — RESEARCH
4. Revenue YoY 5D — HOLD_CONCENTRATION_FAIL
5. Revenue YoY 20D — HOLD_CONCENTRATION_FAIL

詳細狀態以 /SKY_SYSTEM_REGISTRY_V2_1.md 為準。

## 仍未完成，不得宣告 100%

1. TPEx 嚴格官方盤中全市場資料鏈
2. Feature Store schema/versioning 與資料品質監控完全 production 化
3. Point-in-time 公司實際公告 timestamp 對齊
4. Broader / point-in-time universe，降低 current-universe survivorship bias
5. Candidate 的正式 Walk-forward + OOS + regime 分層完整驗證
6. Candidate cost/slippage stress matrix
7. Look-ahead / survivorship / leakage 自動檢查
8. Portfolio concentration / correlation / capacity validation
9. Paper / Shadow Trading 累積樣本
10. Alert delivery monitoring / retry / dedup production 化
11. Dashboard / Mobile API
12. Production model promotion / rollback SOP 完整演練

## 模型升版原則

任何 Challenger 只有在以下全部通過後，才可成為 Champion：

- Point-in-time 資料對齊通過
- Leakage / survivorship 檢查通過
- 固定、預先註冊規則
- Walk-forward 通過
- OOS 通過
- 0.45% 主成本測試通過
- 0.65% 成本壓力測試可接受
- Portfolio PF / Expectancy / MDD 通過
- 年度與 Market Regime 無災難性失效
- 無單一股票／單一產業依賴
- Paper / Shadow Trading 通過
- P0-R Risk Gate 通過
- P0-G Promotion Decision 完成紀錄

不得因單次回測較漂亮、單一月份獲利、Accuracy 較高或單一 feature Rank IC 較高就直接升 Production。
