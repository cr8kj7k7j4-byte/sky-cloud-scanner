# Sky 100 Phase 7｜Walk-forward Ablation + Regime Stability Matrix

## 目的

Phase 7 檢查每一條當沖 Rule 的貢獻是否具有時間穩定性與市場環境穩定性。

Production Baseline 不因本研究自動變更。

## 核心矩陣

`Rule × Walk-forward Fold × Market Regime × Cost Scenario`

V2 固定 Rules：

1. Market Gate
2. Sector / Relative Strength
3. Multi-timeframe Confirmation
4. Phase
5. Setup
6. Trigger
7. Anti-Chase
8. RR Gate
9. Opportunity Ranking
10. Execution Adjustments

固定 Cost Scenarios：

- Primary: 0.45% round-trip
- Stress: 0.65% round-trip

## 每個 Fold / Regime 固定比較

Full Rules vs Remove-One Rule，並記錄：

- n
- Win Rate
- Avg Win
- Avg Loss
- Expectancy
- PF
- Max DD
- MAE
- MFE
- R Multiple
- Expectancy Contribution
- PF Contribution
- Drawdown Protection
- Sample Reduction
- Trigger frequency
- False breakout rate
- Slippage sensitivity
- Cost-adjusted return

## Walk-forward 最低要求

- 至少 3 個有效 test folds。
- Fold 的切割必須依時間排序，不得 random shuffle。
- 已用於研究調整的期間不得重新聲稱為 fresh OOS。
- 每個 fold 必須保留相同 frozen rule definition 與 cost model。
- Fold 正貢獻比例 >= 67% 才能稱作時間方向一致。

## Regime 最低要求

至少檢查：

- Bull
- Neutral
- Bear

至少 2 個具足夠樣本的 Regime 才能判定 Regime Stability。

Regime 正貢獻比例 >= 67% 才能稱作方向一致。

不得使用未在 decision timestamp 可得的 hindsight regime label。

## 固定切面

除 Fold / Regime 外，必須產生以下 slice stability：

- Time-of-day
- Liquidity
- Spread
- Slippage
- Trigger Quality
- False Breakout
- Missed Entry
- Execution-adjusted RR bucket
- Ranking decile
- Capacity
- Sector concentration
- Single-symbol concentration

切面用途是發現脆弱性，不得用來事後 cherry-pick 最佳 subgroup。

## Rule Stability 狀態

- `STABLE`
  - >=3 folds
  - Fold positive share >=67%
  - >=2 sufficient regimes
  - Regime positive share >=67%
  - primary / stress cost 方向不反轉
  - mandatory PIT coverage pass

- `MIXED`
  - 樣本足夠，但 fold / regime / cost 方向不一致。

- `NEGATIVE`
  - Full Model 保留該 Rule 後，after-cost 結果跨 fold / regime 持續較差，且 DD Protection 無獨立價值。

- `INSUFFICIENT_SAMPLE`
  - 樣本不足。

- `DATA_BLOCKED`
  - PIT / execution / sector / timestamp / cost reconstruction 無法達 gate。

## Governance

- STABLE 只代表研究證據較一致，不代表未來獲利保證。
- W2 僅可輸出 `PROMOTE_CANDIDATE / HOLD / REJECT / ARCHIVE`。
- `PROMOTE_CANDIDATE` 只送 W0 審查，不等於 Production promotion。
- Production 升版權限只屬於 W0 + P0-G。
