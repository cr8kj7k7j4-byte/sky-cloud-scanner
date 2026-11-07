# Disclosure GCS Persistence Gate V1 — 2026-11-08

**狀態：RESEARCH_ONLY / CLOUD_CONFIG_PENDING。沒有 GCS 端到端驗收，不啟用 cron，不修改 Production。**

## 成功路徑
GitHub Actions 手動／PR研究模式取得 TWSE+TPEx 四個公開端點原始 bytes、SHA256、manifest。
GCS 正式寫入時使用 Workload Identity Federation (WIF) 短期憑證而非長期服務帳戶 JSON Key；對每個檔案使用 if_generation_match=0 的 create-only 前置條件，檔案寫入後重新下載所有 byte 並核對雜湊，最後才寫入與核對 manifest 做成功提交標記。儲存路徑使用 `disclosure-forward/v1/run-{GITHUB_RUN_ID}-attempt-{GITHUB_RUN_ATTEMPT}` 防止重複執行覆蓋。

**儲存桶層級 retention policy / object versioning / IAM least privilege 均須由 Cloud 真實設定另行查證，程式 create-only 不足以證明整個桶不可變更。** 長期保留時程、成本、對外分享權限與隱私由 W3B/W0 先審核。

## GitHub 設定要件
- Repository Vars: `DISCLOSURE_GCS_BUCKET`，應指向已建立的專用資料桶（不要寫入未經授權的持倉或富果付費行情）。
- Repository Secrets: `DISCLOSURE_GCP_WIF_PROVIDER`、`DISCLOSURE_GCP_SERVICE_ACCOUNT`（身份設定，不可將金鑰寫入 repo）。
- Google Cloud WIF IAM 必須限定此 repo、適當 workflow/ref 的 GitHub OIDC 主體；服務帳戶原則上僅授權指定 bucket 的 object create/read 與必要 metadata，嚴禁廣域 Project Owner。
- 設定與查核需 Google Cloud 擁有者授權，GitHub connector 只能檢查工作流記錄，無法自行建立或查詢 GCS IAM。
- Workflow 只在 manual dispatch 執行 GCS 真實上傳；PR 只有測試與快照（不暴露秘密給 PR 工作流），而且沒有 cron。
- 若 WIF、bucket、服務帳戶有任何缺漏，Upload Gate 必須 fail-closed；不能把單元測試 PASS 宣稱雲端已保存成功。
- Cloud 端寫入後必須從 GitHub 工作流確認 upload/readback 完成五個 objects，且保留跨日成功率、錯誤通知、重試與重複情形記錄，才能考慮未來 GitHub Actions 定時採集。

## 對策略驗證的意義
此路徑僅證明**首次觀測時間**，不能取代個別公司歷史正式公開時間；當月最新彙總與歷史 PIT、原始財報、公告更正是不同資料契約。必須再完成 issuer-level published_at 證據、富果行情加入、0.45/0.65%成本、可成交價、前瞻樣本、W0/P0-G 治理才可轉換成交易訊號。

## 目前工作
保留既有 PR #322 修復結果；本分支僅加 GCS gate，不調整已封存或正在研究的交易策略。
