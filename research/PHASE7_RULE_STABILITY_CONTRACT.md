# Sky 100 Phase 7｜Walk-forward Ablation + Regime Stability Matrix

## 目的

Phase 7 檢查每一條 Gate 的貢獻是否具有時間穩定性與市場環境穩定性。

## 核心矩陣

Rule × Walk-forward Fold × Market Regime

V1 Rules：
- Market Gate
- Sector / Relative Strength Gate
- Anti-Chase Gate
- Phase Gate
- Setup Gate
- Trigger Gate
- RR Gate

## 評估方法

每個 Fold 與每個 Regime 都比較：

Full Rules vs Remove One Rule

並記錄：
- Expectancy Contribution
- Profit Factor Contribution
- Drawdown Protection
- Sample Count

## 穩定度門檻（研究初版）

- 至少 3 個 Walk-forward fold
- Fold 正貢獻比例 >= 67%
- 至少 2 個具足夠樣本的 Regime
- Regime 正貢獻比例 >= 67%
- 樣本量達最低門檻

## 狀態

- STABLE：時間與 Regime 都一致
- MIXED：樣本足夠但證據不一致
- INSUFFICIENT_SAMPLE：樣本不足

STABLE 只代表研究證據較一致，不代表未來獲利保證，也不授權直接修改正式策略。
