# GCS 跨日事件帳本 V1 — 2026-11-08

**狀態：ENGINEERING_RESEARCH_ONLY / NO_CRON / NO_TRADES。**

## 主要工作
每次人工執行 `Disclosure GCS Durable Readback Gate`，四份 TWSE／TPEx 官方原始快照寫入 GCS 後，重新列出 `disclosure-forward/v1/` 所有已**以 manifest 完成提交**的批次，每份批次必須再次核對 5 個 GCS 物件、SHA-256、必要來源與觀測時間。任何原始檔遭修改、批次時間順序倒退或來源不完整，均停止建立帳本。

逐批使用既有 `research.forward_event_ledger.build_ledger` 合併資料，重複事件不會變成新樣本；同一 provisional ID 不同內容留存修訂歷史（非官方更正認證）。輸出以 `disclosure-forward-ledgers/v1/run-{GitHubRunId}-attempt-{GitHubAttempt}/ledger.json` **create-only** 寫入，立即下載逐 byte 核對；原始歷史快照不修改、不刪除，不建立可覆寫的 latest 指標。

## 安全／資料治理
- `issuer_original_published_at` 仍為 null；不得用 first-observed 冒充公告原始時間。
- 合格交易事件固定 0、`historical_pit_certified=false`、`production_signal=false`。
- 預先限制最多300個歷史批次；超出**明確失敗**、需另行設計持久化 checkpoint 加速，不可靜默只處理最新30筆。
- 僅人工 `workflow_dispatch` 執行真實 GCS寫入；PR 只跑本地模擬測試；不啟用cron。
- 使用現有 WIF 短期憑證及 Bucket 範圍授權；未檢查 Bucket retention lock／IAM 最小權限，不可宣稱完整合規。
- 跨日版本保存可完成資料工程閉環；**仍不會自動產生交易訊號或保證正期望**。W4研究訊號→ outcomes、富果行情、成本與 P0-R、W0/P0-G 待另一階段。
- 過去已採集、且有 manifest 的快照可成為觀察帳本中的較早批次，但不可重稱歷史 PIT 真正可觀測事件。

## 驗收分層
- 單元測試：同一批次重複合併、變更成新 revision、缺漏的manifest忽略、Hash竄改停止、觀測倒退停止、帳本 create-only + 讀回。
- 真實GCS：需人工從 main 執行完整工作流，留存 `gcs_crossday_ledger_receipt.json` 的實際 GCS path、批次數、去重及 revision，並在 Console 另核對權限及保存政策。
- 不在正式驗收前加入定時排程、通知與 Production 改動。
