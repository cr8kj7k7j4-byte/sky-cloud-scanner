# Sky AI Meta-Filter V0.1｜研究入口與治理預登錄草案

**研究狀態：HOLD / INSUFFICIENT_DATA — 尚未 W0 核准開跑，不是 Production。**

## 核心結構假設

研究目標為「對 **已通過 Sky v1.4 原生 P0-C／P0-R 篩選**的做多候選訊號，額外評估是否可透過交易訊號品質分類器降低成本後虧損」，不是重新做已封存 Transparent Intraday ML Ensemble／Top100 Velocity／VNext Ranking 家族的調權重或 Top N 救援。

正式當沖是 Sky v1.4 Dynamic Capital Rotation，**不是 Sky v1.3**。此研究不能變更原始候選生成、買進觸發或停損停利，也不能替代正式策略。過往 rejected / ARCHIVED_NO_RETUNE 家族不重啟。

## 硬性前置缺口

1. `docs/W0_V14_HISTORICAL_REPLAY_GOVERNANCE_DECISION_20261026.md` 已認定 `HISTORICAL_V14_FULL_RULE_REPLAY_UNAVAILABLE`。因此**不得以歷史代理訊號冒充真正 Sky v1.4 候選交易**，也不能把十檔 2026 ML 方向預測資料重標成 v1.4 訊號。
2. 本 PR 僅建立離線研究證據契約與評估函式，**不訓練任何 Meta 模型**、不產生買賣價格／權重／機率，不接觸 Cloud Run 或正式手機、沒有自動下單或預設自動排程。
3. 只有經獨立查核的候選訊號來源（`signal_id`, `source_event_id`, `candidate_at`, `baseline_eligible=true`）和可追溯 PIT 特徵／預測時間、同一份原策略規則凍結，才可能用於真正的前瞻收集。
4. 入帳時必須同時保留原始候選與 AI `ACCEPT`／`REJECT` 決定，連 **拒絕的候選** 都必須追蹤反事實結果。缺少結果不可以刪掉樣本來提高完整率。

## 固定研究指標（未選參數）

- 固定 Top 3／Top 5 每日分數排序與同日相同候選池基準；當日不到 N 檔則不聲稱有 Top N 結果。
- 成本後淨 R 倍數（`R = entry_proxy - original_stop_proxy`，做多）；primary 0.45% 與 stress 0.65% 研究成本。
- `ACCEPT` vs `REJECT` vs 原策略全體候選的 expectancy、正報酬率；ROC-AUC、完整率、集中度、真正獨立交易日。
- 本研究不更改原正式成本 Profile。0.45%／0.65% 只是符合治理審查的高成本壓力，成交滑價、價差、實際手續費／稅與沖銷位置皆仍待獨立驗證。
- AUC 使用成本後淨收益是否大於 0 作為二元標籤，非交易成交機率；無正負樣本同時存在時返回無結果。
- 嚴禁回溯決策、回看 outcome 才重調分數門檻／Top N、把所有同一天多次掃描當作多交易日。

## 未來正式前瞻驗證要求

- W0/P0-G 審查後固定新模型版本、所有特徵可得時間、候選事件基準、模型入場門檻與市場環境規則，才能啟用真正不可篡改的 shadow 日誌。
- 需可評估樣本 ≥200、真正未來交易日 ≥20、環境 ≥2、結果完整率 ≥95%、單檔集中度 ≤20%；同時核查成本後期望值／PF／最大回撤／容量／多單風控。
- 研究輸出只能是 `HOLD_INSUFFICIENT_DATA` 與 `production_eligible=false`、`order_authorized=false`；沒有 W0/P0-G Promotion 不可改稱正式。
- 現有三模型方向歷史試跑十檔報告證明其方向分類準確率與全猜跌基準同值，不能聲稱已驗證 Meta 過濾。Meta 是**新研究假設**而非歷史正期望結論。

## 本階段工程驗收

- 確定候選進場前才可有模型分數；無時區／未來分數／缺成本基準／非法風控／冒充正式成交一律 fail closed。
- 每個訊號 ID 唯一，保留拒絕者與 pending，區分 proxy counterfactual 與真實損益。
- `python -m unittest -v tests.test_sky_meta_filter_v0_1` 只使用假資料 fixture，**成功不代表真實原生候選或模型效果驗證**。

參考正規治理：`SKY_SYSTEM_REGISTRY_V2_1.md`、`research/RESEARCH_FREEZE_REGISTRY.md`、`docs/SKY_VALIDATION_PROTOCOL_V1_0.md`。
