# W5｜Sky Candidate Strategy Lab Registry

> 隔離研究區。任何新策略、新文章、新量化論文、AI 股票工具、新 ML 方法、新 Feature、新 Indicator、新 Ranking、新事件策略、新因子，均先進 W5；不得直接修改 Production。
>
> GitHub 為 Single Source of Truth。W5 只負責 Intake、去重、價值篩選、研究預註冊前治理與候選淘汰，不具 Production 升版權限。

## 0. W5 Operating Files

W5 正式操作檔案：
- `research/w5/CANDIDATE_INTAKE_TEMPLATE.md` — 新 Candidate 標準 Intake。
- `research/w5/DUPLICATE_LOW_VALUE_GATE.md` — Duplicate / Low-value Gate。
- `research/w5/PREREGISTRATION_TEMPLATE.md` — 通過 Intake 後的預註冊模板。
- `research/w5/CANDIDATE_QUEUE.md` — W5 候選佇列。
- `research/w5/HANDOFF_PROTOCOL.md` — W5 → W0 → W1/W2 交接規則。

執行順序固定：
`Intake → Duplicate/Low-value Gate → ACCEPT/HOLD/REJECT/ARCHIVE → Pre-registration（僅 ACCEPT）→ W0 Handoff`

## 1. Purpose

核心問題：

> 這個新想法是否提供目前 Sky 尚未具備的獨立資訊與可驗證 Edge？

W5 不以「新穎」、「模型複雜」、「文章績效漂亮」作為研究價值證據。

## 2. Mandatory upstream governance references

每次 Candidate 研究前至少核對：
- `SKY_SYSTEM_REGISTRY_V2_1.md`
- `research/RESEARCH_FREEZE_REGISTRY.md`
- `docs/SKY_VALIDATION_PROTOCOL_V1_0.md`
- `docs/SKY_V2_1_BASELINE_FREEZE_20261025.md`
- `docs/SKY_MASTER_CONTROL_STATUS_20261025.md`

## 3. Candidate Intake Template

每個 Candidate 必須填：
1. Candidate 名稱
2. Hypothesis
3. 解決什麼問題
4. 使用市場
5. Horizon
6. Target / Label
7. Data source
8. Feature
9. Trigger / Ranking
10. Execution assumption
11. Cost assumption
12. Risk
13. 與既有策略差異
14. 與 rejected family 差異

## 4. Low-value / Duplicate Gate

研究前先回答：
1. 現有 Sky 是否已有同類模組？
2. 是否只是換名稱？
3. 是否只是新 indicator？
4. 是否只是改 threshold？
5. 是否只是改 Top-N？
6. 是否只是改權重？
7. 是否只是想救已失敗策略？
8. 是否需要新的資料？
9. 新資料是否 Point-in-Time 可取得？
10. 是否能做真正 OOS？

若僅屬以下局部微調，原則上：
- threshold 微調
- indicator period 微調
- Top-N 微調
- weight 微調
- stop / target 微調

→ `REJECT_LOW_VALUE`

## 5. Frozen / rejected families

以下家族不得靠局部調參重新啟動：
- P0-S 5m Breakout
- Stage 6B Catalyst Score
- Stage 6C Event Interaction
- Stage 6D Reaction-first Intraday
- Stage 7A Broader Market Alpha A1–A5
- Weak-Regime Mean-Reversion 5–20D
- Fixed-time Intraday Ranking
- Event-driven Intraday Ranking / Catalyst Stack
- Transparent Intraday ML Ensemble
- Low-vol Market-residual Long-only
- VNext Residual Ranking Baseline v1

若新 Candidate 與上述高度相似，必須明確說明結構性差異；沒有結構性差異 → `REJECT_DUPLICATE`。

## 6. Research Funnel

固定順序，不得跳級：

`Idea → Evidence Review → Hypothesis → Pre-registration → Data Feasibility → PIT Audit → Baseline → Train → Validation → OOS → Walk-forward → Cost Stress → Portfolio → Capacity → Shadow Candidate → P0-G Review`

## 7. ML Rules

ML 不得直接作為「更準」的研究假設。

順序：
1. deterministic baseline
2. linear baseline
3. 只有基準有證據後，才可測 Random Forest / XGBoost / LightGBM

LSTM / Transformer / Reinforcement Learning 原則上不進入第一輪研究，除非已有明確資料量、Label、PIT 與結構性研究理由。

禁止只看 Accuracy。最低研究指標：
- after-cost expectancy
- ranking IC
- turnover
- calibration
- stability
- OOS
- cost sensitivity
- explainability

## 8. Allowed W5 Status

Candidate 只能得到：
- `ACCEPT_FOR_PREREGISTRATION`
- `HOLD`
- `REJECT_DUPLICATE`
- `REJECT_LOW_VALUE`
- `ARCHIVE`

W5 不得直接將 Candidate 標記為 Production / Champion。

## 9. Research Priority

高優先：
- 補足目前已知缺口
- PIT 可取得
- 可嚴格驗證
- 與目前 Production 有關
- 有合理經濟／市場邏輯
- 低複雜度
- 容易解釋
- 執行成本合理

低優先：
- 酷但不可驗證
- 需大量不可取得資料
- 純黑盒
- 高換手
- 成本敏感
- 只靠微調

## 10. Current W5 Initial State — 2026-10-25

### Active candidate authorization
- **No active VNext Alpha candidate is currently authorized.**

### Current blocked / hold research inherited from registry
- Revenue MoM 5D — PRE_PIT_CANDIDATE — blocked by verified historical MOPS filing timestamp coverage.
- Revenue YoY Acceleration 5D — PRE_PIT_CANDIDATE — same PIT blocker.
- Revenue YoY 5D — HOLD_CONCENTRATION_FAIL.
- Revenue YoY 20D — HOLD_CONCENTRATION_FAIL.

### Master-control priority
Current system priority remains:
1. Evidence completion
2. Shadow/Paper accumulation
3. Portfolio/risk validation
4. Production hardening
5. Only then new alpha research

Therefore W5 may intake, screen and preregister ideas, but should not create research volume merely to fill a backlog.

## 11. Standard Final Output

Candidate：
Status：
Hypothesis：
Structural Difference：
Data Feasibility：
PIT：
Expected Value：
Main Risks：
Recommendation：

## 12. Escalation

若 Candidate 通過 W5：
- 交 W0 決定是否進入正式研究隊列。
- Swing 類 → 由 W0 決定是否送 W1。
- Intraday 類 → 由 W0 決定是否送 W2。
- W5 不自行升版、不直接污染 Production。
