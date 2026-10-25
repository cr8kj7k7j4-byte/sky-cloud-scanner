# Sky Parallel Workstreams — Multi-Window Operating Model

> 對話視窗只是工作介面；GitHub Registry 才是唯一正式狀態。任何視窗完成研究後，必須回寫 Registry / Evidence / Freeze 狀態。

## W0｜Sky 總控與版本治理
Owner namespace：P0-G

目的：維持單一真實來源，禁止不同視窗各自演化成不同 Sky。

只處理：
- Baseline / Champion / Challenger
- Strategy Registry
- Research Freeze
- Promotion / Rejection / Archive
- Cross-workstream priority
- W1–W7 成果收斂

不處理：
- 大量回測
- 臨時調參
- 直接替代各專業視窗執行長時間研究

## W1｜Sky Swing 驗證實驗室
Owner namespaces：P0-S / P0-D / P0-R

目前狀態：**HOLD**

目前任務：
1. 不再把舊 100-symbol current-universe artifact 重跑後當成新證據。
2. 準備 canonical 2023+ PIT Swing replay 的 preregistration、資料需求、exit/rule/feature ablation 規格。
3. 等共用 PIT data path 可用後，再執行 promotion-grade replay。
4. 任何合格結果只能送 W4 Shadow/Paper，不得直接改 Production。

## W2｜Sky 當沖驗證實驗室
Owner namespaces：P0-S / P0-C / P0-O / P0-D

目前狀態：**HOLD / DATA_BLOCKED**

PR #79 已由 W0/P0-G merge，正式納入研究基礎設施：
- Intraday PIT Replay Contract
- Fail-closed Validator
- Canonical 10-Rule Remove-One Ablation
- Walk-forward / Regime Stability
- 0.45% / 0.65% Cost Stress
- W2 Validation Runner
- CI / unit tests

目前任務：
1. 不新增 Production Rule。
2. 不重開 ARCHIVED_NO_RETUNE 家族。
3. 維持 validator / ablation / stability runner 與 W3A dataset contract 相容。
4. 在 W3A dataset 未通過 fail-closed gate 前，不產生 Rule efficacy 結論。
5. Dataset 通過後才執行 canonical 10-rule validation。

## W3A｜Sky Data & Feature Engineering
Owner namespaces：P0-DATA / P0-F
Collaborating namespaces：P0-K / P0-M / P0-EVT

目前狀態：**P0 / HIGHEST PRIORITY**

目前唯一最高優先任務：
**Intraday PIT Historical Replay Dataset**

正式依據：
- docs/W3_INTRADAY_PIT_REPLAY_DATASET_PRIORITY_20261025.md
- research/INTRADAY_PIT_REPLAY_CONTRACT_V1.md
- P0_DATA_CONTRACT.md
- P0_F_FEATURE_REGISTRY.md
- POINT_IN_TIME_UNIVERSE.md

必須直接持續完成：
1. PIT universe join
2. Market context
3. Effective-dated sector mapping
4. Sector RS
5. MTF / Phase / Anti-Chase historical states
6. Candidate-pool / ranking preservation
7. Execution-context historical fields
8. Outcome join
9. 0.45% / 0.65% cost fields
10. coverage / leakage / survivorship audit
11. versioned manifest / lineage
12. feed directly into research/w2_intraday_validation_runner.py

不得：
- 修改 Alpha 邏輯
- 用 current-only mapping 回填歷史
- 用 0 代替未知 spread/slippage
- 用 outcome/future data 生成 decision-time feature

## W3B｜Sky Cloud & Production Engineering
Owner namespaces：P0-X / P0-A
Engineering support：P0-DATA / P0-K / P0-F / P0-L / PMS

目前狀態：**ACTIVE / P1**

目前任務：
1. 支援 W3A → W2 replay pipeline 可重現執行。
2. GitHub Actions / artifact retention。
3. Docker / runtime / dependency reproducibility。
4. Logging / monitoring。
5. Retry / dedup。
6. Secrets / runtime reliability。
7. Production E2E。
8. Rollback rehearsal。
9. 不修改 Alpha 或 Production Rule semantics。

## W4｜Sky Shadow / Paper / Live Evidence
Owner namespaces：PMS / P0-L / P0-R / P0-A / P0-G

目前狀態：**WAITING_FOR_SUFFICIENCY / ACTIVE ACCUMULATION**

持續追蹤：
- Observation → Trigger → Risk Gate → Outcome
- MFE / MAE / R
- Cost / slippage
- Ranking forward return
- Sample Sufficiency
- Live drift

Sufficiency gate：
- >= 200 evaluable samples
- >= 20 trading days
- >= 2 market regimes
- outcome completeness >= 95%
- single-symbol share <= 20%

達 Gate 前：
- 不宣稱實盤有效
- 不進 Small Live
- Counterfactual 不得描述為實際成交

## W5｜Sky Candidate Strategy Lab
Owner namespaces：P0-LAB / P0-ML

目前狀態：**INTAKE ONLY / LOW PRIORITY**

目前任務：
1. 新策略、新文章、新 Feature、新 ML、新 Indicator 先做 intake。
2. 先查 Freeze Registry。
3. 先做 duplicate / low-value gate。
4. 不主動製造大量新 Alpha backlog。
5. 沒有結構性差異 → REJECT_DUPLICATE / REJECT_LOW_VALUE。
6. 通過 W5 也只能送 W0 排隊。

## W6｜Sky Execution & Market Microstructure Lab
Owner focus：P0-X execution research / market microstructure evidence

目前狀態：**ACTIVE / P2**

目前任務：
1. Execution Alpha / Market Microstructure。
2. Spread / Slippage / Fill Quality。
3. Aggressive vs Passive execution。
4. Adverse Selection。
5. Intraday Liquidity。
6. Execution-adjusted RR。
7. 優先支援 W3A / W2 定義可歷史重建的 execution fields 與 calibration assumptions。

限制：
- 不開發新的方向型交易策略。
- 不直接修改 Production。
- 歷史資料不可得時標記 UNKNOWN / BLOCKED，不得用 0 或 hindsight 最佳值補齊。

## W7｜Sky Global Trading Intelligence & Vendor Lab
Owner focus：Global trading intelligence / vendor evaluation

目前狀態：**ACTIVE / LOW-INTENSITY / P4**

目前任務：
1. 全球市場策略情報。
2. Hedge Fund / Quant Fund / CTA / Market Making 方法。
3. 學術論文。
4. AI 股票工具。
5. Backtest platform。
6. Data vendor。
7. Order-flow tools。
8. 付費模型 / 課程 / 產品評估。
9. 只回答：是否有值得 Sky 驗證的獨立資訊？是否值得花錢？

新方法不得直接進 Production：
W7 → W5 intake → W0 priority → W1/W2/W6 validation。

## Legacy W3｜資料與系統工程
狀態：**DEPRECATED FOR NEW WORK**

規則：
- 保留歷史紀錄。
- 不再新增任務。
- 資料 / Feature 工作移交 W3A。
- Cloud / Deployment / Runtime 工作移交 W3B。
- 避免 W3、W3A、W3B 同時修改同一治理或工程範圍。

## Current Critical Path

**W3A → W2 → W4 → W0**

Supporting path：
- W3B supports W3A/W2 runtime
- W6 supports execution-context evidence
- W1 waits for shared PIT infrastructure
- W5/W7 remain controlled intake/research sources

## 跨視窗規則

1. 每個視窗只做一個 Workstream。
2. 正式版本只認 GitHub Registry。
3. 新研究先查 Research Freeze Registry。
4. 每次結論標記 FACT / INFERENCE / UNKNOWN。
5. 研究狀態只能是 PROMOTE_CANDIDATE / HOLD / REJECT / ARCHIVE，或各專業視窗明定的研究狀態。
6. 回測結果必須附 dataset / period / cost / sample / code version。
7. 未通過 P0-G，不得改 Production。
8. 使用者不需要逐步回覆「好」；在既有授權範圍內持續完成同一 Workstream。
9. 只有以下情況才需使用者介入：
   - 新外部帳號 / API 憑證
   - 真實資金或不可逆風險
   - 使用者 1R / max position 必須指定
   - 關鍵外部資料完全不可取得
   - ChatGPT UI 必須由使用者手動建立 / 切換視窗
