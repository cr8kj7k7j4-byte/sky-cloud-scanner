# W2｜六模型身份與私有 GCS 研究帳本驗收證據（2026-11-08）

> **RESEARCH_ONLY / HOLD / NO_TRADE.** 本文件是截至 2026-11-08 的稽核快照。三模型規則觀察不是六套已訓練的 AI；GCS 研究觀察不是正式交易或已實現損益。

## 1. 手機端六模型身份（唯讀跨儲存庫查核）

依 `cr8kj7k7j4-byte/tw-ai-trading-system` 的 `src/model_activation.py`（main，於 2026-11-08 查閱；已合併 mobile PR #44），`verified_independent_inference_count=0`、`verified_model_weight_count=0`、`runtime_execution_verified=false`。

| model_id | 登錄版本 | 登錄入口 | 目前實際類型 | weights SHA256 | 真實獨立推論 |
|---|---|---|---|---|---|
| `sky_day_v14` | `v1.4` | `sky-cloud-scanner/src/main.py`（外部唯讀） | upstream_read_only | 無已驗證值 | 未驗證 |
| `sky_swing_v10` | `V1.0` | `sky-cloud-scanner swing research/registry`（外部唯讀） | upstream_read_only | 無已驗證值 | 未驗證 |
| `sky_mcr_v15` | `V1.5 RESEARCH` | `src/mcr_model.py:get_mcr_model`（研究 metadata） | research_metadata_only | 無已驗證值 | 未驗證 |
| `intraday` | `UNTRAINED` | `src/models.py:IntradayModel.predict` | untrained_interface | 無已驗證值 | 未驗證 |
| `overnight` | `UNTRAINED` | `src/models.py:OvernightModel.predict` | untrained_interface | 無已驗證值 | 未驗證 |
| `swing` | `UNTRAINED` | `src/models.py:SwingModel.predict` | untrained_interface | 無已驗證值 | 未驗證 |

這是六個**介面/登錄身份**，不應與下述三套規則型研究 observation 的 `model_id` 混用，更不是六個真實 AI model runner 已完成推論的證據。

## 2. 真實 paid Fugle 歷史資料 → 私有 GCS 讀回

- 來源：`Fugle historical/candles`，歷史研究日期 **2026-11-06**，cohort `1101,8088`。
- Run: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42437151436
- main Run head: `80828c4cf6efb62b419f906b87b47ca215f4f1a4`
- 稽核輸出：`output/three_model_fugle_evidence_summary.json`
- GitHub artifact: `three-model-fugle-sanitized-audit-42437151436` (ID `13599976678`；zip SHA256 `e73ecd57f5308cc818333e8f91355ab45aad246fb597fdd65e6091407a1cfec8`)
- `checked_at_tpe=2026-11-08T10:07:34.006344+08:00`。
- 真實稽核：`status=PRIVATE_LEDGER_SAVED`、`observations_total=6`、`saved_records=6`、`rejected_count=0`、`coverage_gaps=[]`、`provider_authenticated=true`。
- **六筆皆 `ALREADY_EXISTS_IDENTICAL`：代表成功依既有物件讀回相同位元雜湊，該次並非新建六筆。** `object_sha256` 是 GCS 研究物件（不是模型權重）。

| model_id (rule-based) | 股票 | signal_id = ledger_record_id | GCS status | object_sha256 |
|---|---|---|---|---|
| `bidirectional_intraday` | 1101 | `30ed67223d265d84dc0b7440` | ALREADY_EXISTS_IDENTICAL | `7c40e8521b27697a8210353c45fd9e6399671bc8e273bf10437a0c3690c14cd1` |
| `next_day` | 1101 | `32fea08fbd9c4a7546c785da` | ALREADY_EXISTS_IDENTICAL | `cb522f6e2452a25b9c97630c84608fffeac17b0ef9a7e20b1cda89b3a5db5790` |
| `swing_3_20d` | 1101 | `588833b832c84c091d56e55a` | ALREADY_EXISTS_IDENTICAL | `83a99763e90a013220c355c190eb98f0c278298b6a6887243d2fa21bd3f2beda` |
| `bidirectional_intraday` | 8088 | `542a7145da4ab4fb1e5dfe7b` | ALREADY_EXISTS_IDENTICAL | `980c423897fc5e4a92db621974a53f302e117d9cfe5e835adf3c1bae99059116` |
| `next_day` | 8088 | `2e89fcd1fee569c5130e1a23` | ALREADY_EXISTS_IDENTICAL | `d023efe3855d5f9c54b35ae39f947b15c837bed63e882a811cbdfe20401ca892` |
| `swing_3_20d` | 8088 | `f5ea5c0d8f7a9eb28d562cc7` | ALREADY_EXISTS_IDENTICAL | `cd916dedc1d1154b957758c828cd3507036b5009fb3d36359c138c4dcd5583fd` |

GCS 原始單筆內容未直接取得，公開 sanitised audit 亦未含六筆的 `direction`、`bar_time`；此二欄、逐筆 GCS generation/時間、實際 next-session follow-up **尚待授權唯讀核對**，不能憑 ID 猜測或補值。

## 3. W2 PR 與 CI

- W2 Draft PR: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/361
- 既有已驗證 W2 head `3db6a457040cd5dec84e59d593bd49230670d78d` 的 19/19 PR workflow successful。
- https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42438279330 ：24 passed，付費 Fugle / WIF / GCS 步驟在 PR 事件全跳過。
- https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42438279054 ：25 passed，僅 mock / 離線隔日追蹤。
- https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42438279136 ：研究證據閘門成功。

## 4. W0 尚需通過

1. 取得實際 GCS 六個物件 metadata、`direction`、`bar_time` 並核對 SHA256 與 provider 時間，僅能從授權環境讀取，公開報告不轉存付費原始 K 線。
2. 2026-11-06 週五之後第一個**真實完成的交易日**才可進行次交易日 markout；2026-11-08 週日沒有完成交易日，不可製造結果。需驗證 immutable followup 物件、原 `ledger_record_id` 對應與 idempotency。
3. 國定休市日、個股暫停交易及 provider HTTP404 語意須各自驗證，保持 fail-closed。
4. 六項登錄身份需逐一補足獨立實際 runner/版本/weights SHA256/執行輸出，否則只能登錄顯示而非六模型正式 AI 推論。
5. #361 仍 Draft，不合併、不升 Production、不自動下單；W0/P0-G 治理後再決定後續動作。
