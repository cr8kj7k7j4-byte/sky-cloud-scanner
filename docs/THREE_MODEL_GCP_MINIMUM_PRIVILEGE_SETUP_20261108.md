# 三模型富果研究｜Google Cloud 最小權限設定與驗收（2026-11-08）

狀態：**待雲端資源擁有人執行**；本文件不是部署成功證明。

## 已由截圖與 GitHub Actions 確認

- Google Cloud 專案名稱 `My First Project`；專案編號 `816937852055`，專案 ID 為 `project-4f906c69-fa2b-456f-bab`。
- 既有 WIF 集區 `sky-github-evidence` / OIDC 提供者 `github-actions` 已啟用。
- 提供者 CEL 限制 **repository** `cr8kj7k7j4-byte/sky-cloud-scanner`、**ref** `refs/heads/main`、**event_name** `workflow_dispatch`，**不可放寬**。
- 已設定 GitHub `FUGLE_API_KEY` 和 `GCP_WIF_PROVIDER`（但不代表付費歷史端點已驗收）。
- GitHub `GCP_WIF_PROVIDER` 值應是
  `projects/816937852055/locations/global/workloadIdentityPools/sky-github-evidence/providers/github-actions`。
- `sky-disclosure-evidence-20261108` 非公開、位於 `asia-east1`，專供官方公告原始證據；**禁止**用作三模型付費行情資料存放（程式亦設硬性拒絕）。
- `sky-disclosure-evidence-writer@project-4f906c69-fa2b-456f-bab.iam.gserviceaccount.com` 已有 GitHub repo 的 WIF User 主體綁定，但服務帳戶目的專屬公告資料；請**不要**改動或複用至模型。

## 僅需一次的 Google Cloud 人工設定（不建立 JSON 金鑰）

1. 在專案 `project-4f906c69-fa2b-456f-bab` 的 **Cloud Storage > Buckets > Create** 建立 *獨立* 私有研究 bucket（建議名稱 `sky-three-model-research-816937852055`，名稱全球唯一，若已被佔用須另取）。Location type = Region、region = `asia-east1`、storage class = Standard；維持 Public Access Prevention 與 Uniform Bucket-Level Access。建立後記下**實際** bucket 名稱；費用與保留政策需依實際使用量確認。**勿改動公告 bucket。**
2. 在 **IAM & Admin > Service Accounts** 建立專用服務帳戶，建議 ID `sky-three-model-ledger`，預期 email `sky-three-model-ledger@project-4f906c69-fa2b-456f-bab.iam.gserviceaccount.com`（*只有真正建立成功才可使用*）。不要給 Project Owner、Editor、Storage Admin、Cloud Run Admin 等廣泛角色，不要建立服務帳戶金鑰。
3. 在新服務帳戶「具有存取權的主體」授予 **Workload Identity User**（`roles/iam.workloadIdentityUser`），主體設定為
   `principalSet://iam.googleapis.com/projects/816937852055/locations/global/workloadIdentityPools/sky-github-evidence/attribute.repository/cr8kj7k7j4-byte/sky-cloud-scanner`。
   若主體未被接受，先核對 WIF Provider 中 `attribute.repository = assertion.repository` 與實際 WIF IAM 主體格式。提供者本身已有 main + 手動條件，不新增不明 repo。
4. **只在新研究 bucket** 的「權限」頁面，將新服務帳戶加入以下最小預定義權限：`roles/storage.objectCreator`（寫入新物件）和 `roles/storage.objectViewer`（讀回及比對）。不授予物件刪除/修改權限；保留不可公開存取。Cloud Run 讀取端日後應使用不同的只讀身分。
5. 在 GitHub [Repository secrets](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/settings/secrets/actions) 新增 `GCP_SERVICE_ACCOUNT`，內容為**實際建立**的新服務帳戶 email；不要貼在聊天或 PR。
6. 在 GitHub [Actions variables](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/settings/variables/actions) 新增 `SKY_RESEARCH_GCS_BUCKET`，內容為**實際建立**的研究 bucket 名稱。保留已存在的 `GCP_WIF_PROVIDER` 和 `FUGLE_API_KEY`，不重設。
7. PR #324 **必須先通過研究/治理審查再合併**，因 WIF provider 限制只接受 `main` + `workflow_dispatch`，不應為測試 PR 而放寬。合併後先用手動 Research workflow 做少量股票歷史取數驗收，再核對 GCS 逐筆寫入、雜湊讀回、重跑去重；**不新增 cron、不自動下單**。

## 完成判定不可混淆

- 程式／mock CI 成功：僅表示契約測試通過。
- WIF 登入成功：不表示 GCS 真實寫入成功。
- GCS 寫入+讀回成功：不表示三模型權重訓練成功、實盤可交易或 Cloud Run 已部署。
- 既有手機站 Cloud Run 必須取得**其實際服務來源、版本、部署 IAM**及手機端 E2E 結果，才能稱為部署驗收通過。
- 不論研究訊號如何，`production_signal=false`、`order_authorized=false`，正式交易資格仍需 P0-G/W0 審核。

官方參考：
- https://cloud.google.com/iam/docs/workload-identity-federation
- https://cloud.google.com/storage/docs/access-control/iam-roles
