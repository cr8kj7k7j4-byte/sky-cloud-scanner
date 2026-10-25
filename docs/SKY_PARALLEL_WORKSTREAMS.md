# Sky Parallel Workstreams — Multi-Window Operating Model

> 對話視窗只是工作介面；GitHub Registry 才是唯一正式狀態。任何視窗完成研究後，必須回寫 Registry / Evidence / Freeze 狀態。

## W0｜Sky 總控與版本治理
Owner namespace：P0-G  
目的：維持單一真實來源，禁止不同視窗各自演化成不同 Sky。

只處理：
- Baseline / Champion / Challenger
- Strategy Registry
- Research Freeze
- Promotion / Rejection
- Cross-workstream priority

不處理：大量回測與臨時調參。

## W1｜Sky Swing 驗證
Owner namespaces：P0-S / P0-D / P0-R  
目的：驗證 3–20D 波段策略是否有 after-cost、跨期、跨 Regime 穩定 Edge。

優先序：
1. 現有 Swing V1.0 / candidate stability 結果盤點。
2. Walk-forward / OOS。
3. Bull / Neutral / Bear。
4. Cost 0.45 / 0.65%。
5. Exit / Rule ablation。
6. Portfolio / concentration / capacity。
7. 合格才進 Shadow/Paper。

## W2｜Sky 當沖驗證
Owner namespaces：P0-S / P0-C / P0-O / P0-D  
目的：驗證 Intraday Trigger / Ranking，而非追求更多 indicator。

規則：
- 已 REJECTED_OOS 的 5m Breakout、fixed-time ranking、event stack 等保持凍結。
- 新 Candidate 必須是結構性新假設，不得只是 threshold retuning。
- 必須檢查 Execution-adjusted RR、Anti-Chase、成本、流動性與時間因果。

## W3｜資料與系統工程
Owner namespaces：P0-DATA / P0-F / P0-K / P0-EVT / P0-X / P0-A  
目的：確保研究與實盤用的是可追溯資料與可運行基礎設施。

優先：
- TPEx 嚴格官方盤中全市場鏈。
- Feature schema/versioning + DQ。
- Revenue PIT forward collector 與歷史 coverage 誠實治理。
- Alert retry/dedup。
- Mobile / Dashboard API。
- Cloud runtime / CI / E2E。

## W4｜Shadow / Paper / Live Evidence
Owner namespaces：PMS / P0-L / P0-R / P0-G  
目的：累積真實執行環境證據。

追蹤：
- Observation → Trigger → Risk Gate → Counterfactual Outcome
- MFE / MAE / R
- Cost / slippage
- Ranking forward return
- Sample Sufficiency
- Live drift

達 Sufficiency Gate 前不得宣告實盤有效。

## W5｜Candidate Strategy Lab
Owner namespaces：P0-LAB / P0-ML  
目的：隔離新點子，防止 Feature Creep 污染 Production。

任何文章、課程、AI/ML、新指標先進此區。
流程：
Hypothesis → Pre-registration → Evidence → Validation。
未通過不得進 W0 Production Registry。

## 跨視窗規則

1. 每個視窗只做一個 Workstream。
2. 不在聊天記憶中維持「正式版本」；正式版本只認 GitHub Registry。
3. 新研究先查 Research Freeze Registry，避免重複。
4. 每次結論必須標記：FACT / INFERENCE / UNKNOWN。
5. 每次研究只能得到：PROMOTE_CANDIDATE / HOLD / REJECT / ARCHIVE。
6. 所有回測結果必須附 dataset / period / cost / sample / code version。
7. 未通過 P0-G，不得改 Production。
8. 使用者不需要逐步回覆「好」；在已授權範圍內持續完成同一 Workstream，遇到真正需要外部憑證、不可逆風險或資料缺口才停下。
