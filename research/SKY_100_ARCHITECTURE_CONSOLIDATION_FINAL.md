# Sky 100 Architecture Consolidation Final

> 目的：停止繼續堆疊新模組，將目前 Sky V2.1 收斂成唯一正式架構。  
> 本文件是架構治理基準，不代表交易績效、勝率或獲利保證。

## 一、Canonical Namespace

正式命名空間固定如下：

- P0-DATA = Data Governance & Quality
- P0-K = Knowledge & Evidence Engine
- P0-M = Market Intelligence Engine
- P0-EVT = Event & Catalyst Intelligence
- P0-F = Feature Store / Feature Engine
- P0-AG = Agent Orchestration
- P0-S = Strategy Builder
- P0-C = Decision Engine
- P0-O = Opportunity Ranking Engine
- P0-R = Risk & Portfolio Management
- P0-X = Execution Engine
- P0-A = Alert & Monitoring Engine
- PMS = Position Management System
- P0-L = Trade Ledger & Outcome Engine
- P0-ML = ML Research & Model Arena
- P0-D = Learning & Validation Engine
- P0-G = Governance & Registry
- P0-LAB = Candidate Strategy Lab

## 二、54 個 src 模組處置

| 檔案 | Canonical Owner | 處置 | 說明 |
|---|---|---|---|
| __init__.py | Shared | KEEP | Python package 基礎 |
| adr_context.py | P0-M | KEEP | 海外 ADR 市場脈絡 |
| agent_orchestrator.py | P0-AG | KEEP | Agent 協作與 evidence-aware orchestration |
| bis_policy.py | P0-EVT | KEEP | 政策事件來源 |
| config.py | Shared | KEEP | 唯一環境設定入口 |
| cost_profiles.py | P0-X | KEEP | 交易成本情境設定 |
| diagnose_sources.py | P0-DATA | KEEP | 資料源健康診斷 |
| event_intelligence.py | P0-EVT | KEEP | 事件擷取與分類 |
| event_risk.py | P0-EVT / P0-R | KEEP | 事件風險轉譯 |
| event_scoring.py | P0-EVT | KEEP | 事件評分 |
| evidence_ledger.py | P0-K | COMPATIBILITY_ADAPTER | PR #43 已收斂至 knowledge_engine；此檔僅保留相容入口 |
| execution_calibration_ledger.py | P0-X / P0-L | KEEP | 實際成本校準證據 |
| execution_engine.py | P0-X | KEEP | 成本後 RR / 執行 gate |
| explainability.py | P0-K / P0-C | KEEP+EXTEND | 保留唯一 explainability 入口，不另建第二套 |
| feature_engine.py | P0-F | KEEP | 特徵計算 |
| feature_store.py | P0-F | KEEP | 特徵 schema/version/quality |
| fugle.py | P0-DATA | KEEP | Fugle 個股深查來源 |
| global_market_context.py | P0-M | KEEP | 全球市場脈絡 |
| global_sector_mapping.py | P0-M | KEEP | 全球→台股族群映射 |
| gold_context.py | P0-M | KEEP | 黃金等跨資產脈絡 |
| http_utils.py | Shared | KEEP | 共用 HTTP 工具 |
| industry_news.py | P0-K / P0-EVT | KEEP | 產業新聞來源 |
| knowledge_engine.py | P0-K | KEEP | P0-K 主入口；Evidence Ledger 應收斂至此 |
| main.py | P0-AG | KEEP | 正式 runtime entrypoint |
| market_intelligence.py | P0-M | KEEP | 市場摘要 |
| ml_layer.py | P0-ML | RENAME | 目前只是透明 baseline proxy，應改名 ml_baseline.py 避免誤認正式 ML |
| model_arena.py | P0-ML / P0-G | KEEP | Challenger/Champion 比較 |
| model_registry.py | P0-G | KEEP | Model registry |
| model_training.py | P0-ML | KEEP | RF/XGBoost/LightGBM 訓練與比較 |
| monitor_engine.py | P0-A | KEEP | 盤中狀態機 |
| news_evidence.py | P0-K | COMPATIBILITY_ADAPTER | PR #43 已收斂至 knowledge_engine；此檔僅保留相容入口 |
| notifier.py | P0-A | KEEP | 通知輸出 |
| official.py | P0-DATA | KEEP | TWSE/TPEx 官方資料鏈 |
| outcome_engine.py | P0-L | KEEP | 交易結果/MFE/MAE/R 核心計算 |
| premarket_pipeline.py | P0-AG / P0-M | KEEP | 盤前 pipeline |
| premarket_ranking.py | P0-O | KEEP | 盤前候選排序 |
| premarket_state.py | P0-A / P0-M | KEEP | 盤前狀態載入 |
| position_manager.py | PMS | KEEP_AS_CANONICAL | PR #45 建立持倉管理唯一入口；禁止虧損加碼與停損放寬 |
| ranking_engine.py | P0-O | KEEP | 正式唯一 Ranking Engine 候選；production model 尚待實證 |
| readiness.py | P0-G | KEEP | 工程成熟度，不是交易績效 |
| regime_engine.py | P0-M | KEEP | Production regime 定義 |
| relative_strength.py | P0-M | KEEP | 相對強弱 |
| research_sources.py | P0-K | KEEP | 研究來源規格化 |
| risk_engine.py | P0-R | KEEP | 核心風控 |
| sector_rs_replay.py | P0-LAB / P0-D | MOVE_TO_RESEARCH | replay/point-in-time 驗證工具，不應放 production src |
| decision_engine.py | P0-C | KEEP_AS_CANONICAL | PR #44 建立唯一 Decision Contract；不排序、不重算風控、不自動下單 |
| sky_rules.py | Shared compatibility layer | COMPATIBILITY_ADAPTER | PR #51 已完成拆分；first_gate→P0-C、enrich→P0-F、ranking→P0-O |
| state_store.py | P0-A | KEEP | 監控狀態持久化 |
| strategy_builder.py | P0-S | KEEP | Setup / Trigger / Stop / Target 建構 |
| trade_log.py | P0-L | COMPATIBILITY_ADAPTER | 舊研究相容入口；不再維護獨立 schema |
| trade_logger.py | P0-L | KEEP_AS_CANONICAL | 正式 P0-L 主入口；統一 Decision / Trade / Outcome ledger schema |
| training_dataset.py | P0-ML / P0-D | KEEP | 模型訓練資料契約 |
| validation.py | P0-D | KEEP | Validation Gate |
| vwap_entry_replay.py | P0-LAB / P0-D | MOVE_TO_RESEARCH | replay 研究工具 |
| walk_forward.py | P0-D | KEEP | 時間切分契約 |
| walk_forward_eval.py | P0-D | KEEP+MERGE_API | 保留 evaluator，但和 walk_forward 統一 public API |

## 三、目前真正缺的 Production 能力

1. **Production Ranking Champion**
   - PR #47 已完成 P0-O 單一 runtime Ranking Entry；目前缺的是 OOS / Walk-forward / costs / Shadow 驗證後的正式 Champion，而不是架構入口。

2. **Production ML Champion**
   - RF / XGBoost / LightGBM 訓練能力已存在，但沒有任何模型完成正式 Promotion Gate。

3. **真實 Shadow / Paper Trading Evidence**
   - Infrastructure 已完成；目前缺的是足夠真實樣本與成本後實證，而不是更多 Paper Trading 模組。

4. **Evidence / Promotion maturity**
   - PR #23～#28 已由 PR #50 完成抽取並關閉。
   - 架構缺口已不是主要瓶頸，下一階段重點是 Shadow 樣本、OOS/Walk-forward、成本、Regime、Promotion evidence。

## 三之一、已完成基線

- **P0-X runtime correctness**：PR #41 已補齊 execution profile 設定匯入並加入 runtime smoke test。
- **P0-L Canonical Trade Ledger**：PR #41 已合併；trade_logger.py 為唯一 canonical implementation，trade_log.py 僅保留 legacy adapter。
- **Paper Trading / Shadow Ledger**：PR #38 已合併；預設 Shadow，未通過 OOS Gate 不允許 Paper Simulation，更不允許真實委託。
- **P0-S OOS automation**：PR #34 / #35 已建立正式排程與自動 OOS workflow；是否 promotion 仍以實際驗證結果為準。
- **P0-K Canonical Evidence**：PR #43 已合併；knowledge_engine.py 為唯一證據核心，evidence_ledger/news_evidence 為相容 adapter。
- **P0-C Canonical Decision Contract**：PR #44 已合併；Decision 不再由 Risk/Monitor/Agent 各自代表，且 TRIGGERED 仍不是自動買進。
- **PMS Canonical Position Manager**：PR #45 已合併；P0-A 的持倉分支已委派 PMS，禁止向下攤平與停損放寬。
- **P0-O Single Runtime Ranking Entry**：PR #47 已合併；盤中廣域排序改由 ranking_engine.py 統一負責，sky_rules 僅保留相容 alias；Ranking 分數不是機率。
- **P0-D / P0-G Consolidation**：PR #50 已合併；Validation robustness、Rule Registry、Champion Config 已折回 canonical owner；#23～#28 已關閉。
- **sky_rules Decomposition**：PR #51 已合併；Production runtime 已直接使用 canonical P0-C / P0-F / P0-O。
- **Evidence & Promotion Governance**：PR #53 已合併；新增 Shadow Sample Sufficiency Gate 與 Ranking/Model Promotion Scorecard；100 分只代表證據成熟度，不是勝率。

## 四、PR #23～#33 收斂決策

| PR | 主題 | 決策 | 理由 |
|---|---|---|---|
| #23 | Validation & Robustness Gates | FOLD / CLOSE AFTER EXTRACTION | main 已有 validation.py、walk_forward.py、成本/資料稽核研究；不要再放第二個 validation_engine.py |
| #24 | Unified Model Benchmark Arena | FOLD / CLOSE AFTER EXTRACTION | model_training.py + model_arena.py 已能承接；只抽 benchmark runner/LightGBM 依賴需要部分 |
| #25 | Feature Importance & Ablation | FOLD INTO RESEARCH | 有研究價值，但不應新增 src governance；併入既有 OOS feature audit |
| #26 | Rule / Gate Ablation | FOLD INTO P0-LAB | 有價值，但屬研究工具，不應擴張 production src |
| #27 | Rule Stability Matrix | FOLD INTO P0-D | 併入 walk_forward_eval + research 報表 |
| #28 | Rule Registry / Champion Config | FOLD INTO P0-G | 有價值，但應和 model_registry 合成 Governance Registry，不另起平行 registry |
| #29 | Shadow / Paper Trading | SUPERSEDED / CLOSE | PR #38 已將 OOS-gated Shadow/Paper Ledger 合併至 main；#29 不再作為平行 Production 路線 |
| #30 | Champion vs Challenger | DEFER | 等真實 Shadow 樣本足夠再啟用；現在過早 |
| #31 | Production Readiness | FOLD INTO readiness.py | readiness 已存在；擴充而非平行新模組 |
| #32 | Incident / Rollback | DEFER-BUT-KEEP-DESIGN | 營運上有價值，但優先低於策略/資料/ledger 收斂 |
| #33 | Observability / SLO | DEFER-BUT-KEEP-DESIGN | 有價值，但等正式 deployment / runtime 穩定後再接 |

## 五、立即執行優先級

### P0 — 現在就做
1. 累積可用於 Ranking / ML Promotion 的真實 Shadow 樣本
2. 依 Shadow Sample Sufficiency Gate 檢查樣本量、交易日、Regime、Outcome 完整率與標的集中度
3. 對仍存 Candidate 執行 Walk-forward / OOS / Cost Stress / Leakage / Survivorship / Regime Stability
4. 建立 Ranking / Model Promotion Scorecard 的實際證據輸入，不以 Accuracy 或單次回測升版
5. 完成 Point-in-Time historical backfill / coverage audit 與 TPEx 嚴格官方盤中資料鏈

### P1 — 接著做
1. 以已 merge 的 P0-S 5 分 K Setup 完成正式 OOS / costs / MFE / MAE / PF / Expectancy promotion evidence
2. 用同一資料切分比較 Rule / RF / XGBoost / LightGBM
3. 累積真實 Shadow / Paper Trading 樣本
4. 建立 Champion/Challenger 的 promotion evidence，但未通過 Gate 前不得升 Production

### P2 — 樣本夠後做
1. Feature Ablation
2. Rule Ablation
3. Champion vs Challenger
4. Production Readiness / Observability / Incident drills

## 六、停止事項

- 暫停新增 Phase 15+
- 暫停 LSTM / RL
- 暫停新增第二套 Evidence / Explainability / Validation / Registry
- 暫停以 baseline proxy 名稱誤稱正式 ML 模型
- 暫停在沒有 Paper Trading 樣本前宣告 Champion

## 七、正式原則

從本文件起：
- 每個 P0 namespace 只能有一個 Canonical Owner/Entry Point。
- 新功能優先擴充既有 owner，不新增平行模組。
- Research replay / ablation 工具優先放 research/，不進 production src/。
- 任何 production promotion 都必須有版本、證據、OOS、成本、風控與可回滾依據。
