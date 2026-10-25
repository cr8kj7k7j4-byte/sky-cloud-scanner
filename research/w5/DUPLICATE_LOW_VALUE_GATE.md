# W5 Duplicate / Low-value Gate

> 目的：先淘汰「看起來新、實際只是換皮或微調」的想法，避免污染研究資源。

## 1. Immediate duplicate checks

若 Candidate 與以下家族高度相似，先假設為 Duplicate，除非能證明結構性差異：

| Frozen family | 不足以構成新研究的改法 | 可能構成結構差異的例子 |
|---|---|---|
| P0-S 5m Breakout | 5m→10m、門檻、停損、目標微調 | 新 target、不同 execution architecture、不同 PIT data family |
| Fixed-time Intraday Ranking | 換時間點、Top-N、權重 | materially new target / data architecture |
| Event-driven Intraday Ranking | 換事件分數、門檻 | slower horizon、不同 target family、可驗證 reaction architecture |
| Transparent Intraday ML | 換演算法或超參數 | 新 label、新 data contract、新 validation period |
| Weak-Regime Mean-Reversion | MA 期間、Top-N、持有期微調 | 新 target engineering |
| Low-vol Market-residual Long-only | 權重／門檻 | market-neutral / cross-sectional residual formulation |
| Stage 7A | 局部規則調整 | 新 PIT universe + materially new hypothesis family |
| VNext Residual Ranking v1 | Top-N、horizon、weight、ML rescue | 新 structural preregistration |

## 2. Low-value tests

以下任何一項若為 TRUE，原則上 `REJECT_LOW_VALUE`：
- 只是換 indicator 名稱。
- 只是改 indicator period。
- 只是改 threshold。
- 只是改 Top-N。
- 只是改 feature weight。
- 只是改 stop / target。
- 只是把 linear model 換成 nonlinear model。
- 只是把已失敗策略套上 AI / ML 名稱。
- 只有 Accuracy / win rate 改善，沒有 after-cost expectancy 證據。
- 需要不可取得或無法 PIT 重建的歷史資料。
- 無法保留 untouched OOS。

## 3. Structural novelty test

至少需有一項實質變化，且可事前定義：
- 新 Target / Label。
- 新 Horizon。
- 新 Market-neutral / residual framework。
- 新 Execution architecture。
- 新 PIT data family。
- 新 Portfolio construction。
- 新 causal / event timing architecture。
- 新 cross-sectional formulation。
- 新可驗證風險機制。

僅「模型更複雜」不算 Structural Difference。

## 4. W5 decision rule

- 無結構差異且重複 frozen family → `REJECT_DUPLICATE`
- 不重複但只是局部微調 → `REJECT_LOW_VALUE`
- 有結構差異但資料／PIT 尚未確認 → `HOLD`
- 有結構差異、PIT 可行、OOS 可行、研究問題清楚 → `ACCEPT_FOR_PREREGISTRATION`
- 已無研究價值或已被更完整證據取代 → `ARCHIVE`
