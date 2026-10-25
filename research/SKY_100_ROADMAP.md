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

## Evidence & Promotion Phase（2026-10-25 起）

Architecture Consolidation 已完成；目前主軸轉為「證據累積＋升版治理」。

已完成：
- P0-K / P0-C / P0-O / PMS / P0-L canonical owner 收斂。
- PR #23～#29 平行 Production 路線已抽取/關閉。
- sky_rules.py 已降為 compatibility aliases，Production runtime 直接走 canonical P0-C / P0-F / P0-O。
- P0-D robustness validation 與 P0-G rule/model governance 已收斂。
- Shadow Sample Sufficiency Gate 與 Ranking/Model Promotion Scorecard 已由 PR #53 合併。

Shadow Sample Sufficiency 預設候選門檻：
- 至少 200 筆可評估樣本
- 至少 20 個交易日
- 至少 2 種 Market Regime
- Outcome 完整率至少 95%
- 單一股票占比不得高於 20%

以上門檻為治理候選值，不是經歷史最佳化證明的最佳參數；後續只能透過正式研究與治理紀錄調整。

Promotion Scorecard：
- 分數代表升版證據成熟度，不代表勝率、獲利機率或未來報酬。
- 即使 Score = 100，也只代表「可進 P0-G 治理審查」。
- production_eligible 預設仍為 false，必須有明確 Champion Configuration 核准。

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
3. Historical filing timestamp backfill 與 coverage audit
4. Broader / point-in-time universe 的完整歷史覆蓋，持續降低 survivorship bias
5. 尚存 Candidate 的正式 Walk-forward + OOS + regime 分層完整驗證
6. Candidate cost/slippage stress matrix 與 capacity stress
7. Portfolio concentration / correlation / capacity validation
8. 真實 Shadow / Paper Trading 樣本達到 Sufficiency Gate
9. Ranking / ML Promotion Scorecard 全 Gate 通過
10. Alert delivery monitoring / retry / dedup production 化
11. Dashboard / Mobile API
12. Production Champion promotion / rollback SOP 完整演練

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


## Revenue Point-in-Time 進度（2026-10-25）

- MOPS Revenue PIT forward collector：**IMPLEMENTED / LIVE API VERIFIED**
- 官方來源：`/mops/api/home_page/t51sb10`
- 已驗證市場別：`sii` / `otc` / `rotc` / `pub`
- 公司級 `filing_published_at` 僅在可同時辨識公司代號、營收月份與官方發布時間時才寫入。
- API 無新公告（`data=[]`）屬正常狀態，不得視為資料失敗。
- Forward ledger：排程累積未來正式公告時間。
- **Historical filing timestamp backfill：NOT COMPLETE。**
- Revenue MoM 5D / YoY Acceleration 5D 在歷史 PIT backfill 與 coverage audit 完成前仍維持 `PRE_PIT_CANDIDATE`，不得 Promotion。
