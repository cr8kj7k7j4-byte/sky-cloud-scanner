# P0-LAB Candidate Registry｜Weak-Regime Mean-Reversion 15D

## 狀態
**REJECTED / 淘汰**

## 候選策略
Sky Swing Candidate｜Weak-Regime Mean-Reversion 5–20D

## 核心假設
在 Non-Bull / Weak-Regime 下，使用 MA20、MA60 與市場廣度形成的均值回歸訊號，可能在 5–20 個交易日產生正期望。

## 支持證據
訊號層曾出現：
- 5D、10D、15D、20D 在 0.45% 成本後的部分 Train / Validation / Research Test 結果為正。
- 15D 全部合格訊號在 Train / 2025 / 2026 三段曾同時維持正期望。

## 反證與淘汰原因
### Portfolio Decomposition
- Train 全部合格訊號：+0.947%，PF 1.338
- 2025 Validation：+2.448%，PF 1.939
- 2026 Research Test：+1.371%，PF 1.440

但加入 Top-N / 容量限制後失效：
- Train Top3：-1.225%，PF 0.726
- 2026 Top3：-0.331%，PF 0.928

### Portfolio Breadth / Capacity Frontier
Best worst-case config：M5_D2_TOP
- Train：-0.401%，PF 0.899
- 2025 Validation：+4.029%，PF 2.288
- 2026 Research Test：-0.016%，PF 0.997

### Calendar-Rebalanced Broad Basket
Best worst-case config：R5_H10_C0.45
- Train：-0.602%，PF 0.695
- 2025 Validation：-0.185%，PF 0.898
- 2026 Research Test：-0.717%，PF 0.605

## 結論
此策略的「訊號級正期望」無法穩定轉換為有限資金下可執行的 Portfolio Edge。
問題不是單一 Top-N、持倉數或再平衡頻率，而是訊號在組合層缺乏穩定可投資性。

## Governance Decision
- 不升級 Sky Swing 正式版。
- 不再對同一家族做參數微調。
- 不再使用 2026 當作 fresh untouched OOS。
- 保留研究結果作為負面證據與模型治理紀錄。
- 進入下一個結構性研究方向，而不是繼續優化同一訊號家族。

## 下一個正式研究方向
**Residual / Market-Neutral Target Engineering**
1. 改用個股未來報酬減去市場／產業基準報酬的殘差報酬作為 label。
2. 測試 3D / 5D / 10D residual return。
3. 以 cross-sectional ranking 為主，而非絕對報酬預測。
4. 使用 Train / Validation 分離特徵與模型選擇。
5. 2026 僅作研究參考，不再宣稱 untouched OOS。
6. 若未來取得新期間資料，再建立真正 fresh OOS。

## 正式版影響
- Sky 當沖 v0.4：不變
- Sky Swing 正式規則：不變
- 本候選：P0-LAB 淘汰
