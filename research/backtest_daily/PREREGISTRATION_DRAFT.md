# Daily (隔日方向) backtest — Pre-registration DRAFT

Status: **DRAFT — NOT APPROVED. Do not run or interpret results until every TBD is filled and the owner approves.**

Date drafted: 2026-11-22

Gate 1 fields (docs/SKY_VALIDATION_PROTOCOL_V1_0.md):

| Field | Value |
|---|---|
| Universe | 全市場 上市櫃一般股票，價格 ≤ 200（TBD: 是否排除 ETF、處置股、注意股） |
| Horizon | 隔日（TBD: 持有上限 bars） |
| Signal | TBD（owner 決定） |
| Entry | 次日開盤，且 open ≤ max_accept（TBD: max_accept 公式） |
| Stop / Target | TBD |
| Cost model | 0.45% primary, 0.65% stress（已固定） |
| Ranking rule | TBD（每日最多 3 檔，依何者排序） |
| Market regime rule | TBD（Bull / Neutral / Bear 的定義） |
| Portfolio constraints | 1R = 5,000, 單檔名目上限 100,000, 同時持倉 ≤ 3, 組合風險 ≤ 3R, 當日 -2R 停止新進場（依 SKY_RISK_PROFILE；待治理更新） |
| Splits | train 2025H1, validation 2025H2, research_test 2026-01-01~2026-10-22（非 fresh OOS） |
| Promotion thresholds | TBD（建議：扣成本 expectancy > 0 且 validation、research_test 皆為正；樣本數下限 TBD） |

Ablation, walk-forward folds and regime checks are required by Gates 3–6 and are not yet specified.

Owner approval: ______ (date ______)
