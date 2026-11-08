# W2｜AI 方向預測前瞻證據契約提案 V0（審查用，未核准）
日期：2026-11-09（Asia/Taipei）
狀態：**HOLD / INSUFFICIENT_DATA / PROPOSAL_ONLY / NO_TRADE**
權限：W2 只提出研究契約；W0／P0-G 決定假設、准駁、登錄及是否啟動。此文件不等同於預先登錄核准或新的研究家族。

## 1. 已有證據與不准誤述的部分
- [Research-only historical run #42530229758](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42530229758)，固定十檔 2026 歷史資料；原始指標見 PR #374 的 `research/AI_DIRECTION_2026_TEN_SYMBOL_BASELINE_RESULT_20261109.md`。
- 三種 ML（Random Forest、XGBoost、LightGBM）在當沖及隔日的 holdout **方向正確率皆等於 train-only 常數基準**。當沖 Brier 稍差；隔日 Brier 僅略優；無成本後可交易優勢。
- 固定十檔為事後選樣；2026 資料已反覆研究，不屬真正未碰觸的前瞻 OOS。
- 現有 `research/ai_direction_classifier.py` 主要輸出訓練指標；尚無從該入口證實可持久載入的 estimator + calibrator + preprocess artifacts 與綁定 SHA，也沒有 ML 專屬預測前永久入帳。
- 現有 `three-model` 規則訊號研究帳本**不得**作為三套 ML 前瞻預測的替身。

## 2. W0／P0-G 必須先處理的治理決策
1. 在正式研究前確認新結構性假設是否**實質不同於** `ARCHIVED_NO_RETUNE` 家族；若只是換模型／調門檻／Top N／既有時間窗，判 **HOLD 或 REJECT**，不予開啟新試驗。
2. 具體事前登錄：股票母體的 PIT 成分、上市／上櫃來源、是否雙向及可放空資格、價格與流動性篩選、當沖或隔日標籤、訊號產生及可成交時間、特徵清單、模型比較、訓練截止、Calibration、固定風險與退出、成本、閾值及失效條件。
3. 標籤時點需審查：盤中 `09:30 BAR_START` 最早 `09:35` 可得；隔日 D 日收盤資訊與 D+1 開盤進場的撮合／缺量條件。兩者皆不得用歷史 bar 當作真實成交品質。遇不符交易日、缺時區、未證實收盤集合競價時間時 **DATA_BLOCKED**。
4. W0 明確簽核文件版本、核准人、UTC/TPE 時間、基準 SHA、研究凍結範圍；未簽核 **禁止自動啟動新的 ML forward workflow、不可寫入正式交易帳本**。

## 3. 固定模型與來源 Manifest（提案欄位，無真實權重）
採一個 `model_bundle_id` 對應唯一不可變內容；不同 `horizon` 與 `model_family` 分別建立，不共用證據。
- `schema_version`; `study_registration_id`; `approval_ref`; `approval_utc`; `model_bundle_id`; `model_family`; `horizon`; `research_only=true`; `production_eligible=false`
- `train_end_utc`; `calibration_end_utc`; `data_asof_utc`; `feature_contract_sha256`; `label_contract_sha256`; `market_universe_pit_sha256`; `source_snapshot_sha256`
- `git_commit_sha`; `container_or_environment_digest`; `dependency_lock_sha256`; `rng_seed`; `train_input_sha256`
- `estimator_artifact_uri`, `estimator_sha256`; `calibrator_artifact_uri`, `calibrator_sha256`; `preprocessor_artifact_uri`, `preprocessor_sha256`; `bundle_manifest_sha256`
- `signal_clock_contract`, `session_calendar_version`, `training_method`, `calibration_method`, `model_frozen_at_utc`, `expiry_policy`
**驗收規則**：先在授權私有儲存持久保存、讀回、SHA256 逐項一致，再准用於獨立研究影子預測；不得把 GitHub Commit、訓練報告 ZIP、或只有 `train()` 函式誤稱為權重已固定。

## 4. 預測先於結果的不可改寫觀察列（建議 schema）
每個模型／股票／交易日／horizon／cutoff 一列，唯一主鍵：
`prediction_key = SHA256(study_registration_id | model_bundle_id | horizon | session_date | symbol | signal_cutoff_utc)`。
- 必填：`prediction_key`, `model_bundle_id`, `horizon`, `symbol`, `exchange`, `session_date`, `signal_cutoff_utc`, `created_at_utc`, `source_latest_available_at_utc`, `source_snapshot_sha256`, `features_sha256`, `p_up`, `direction`, `no_trade_reason`
- 必填安全欄位：`schema_version`, `research_only=true`, `production_signal=false`, `trading_enabled=false`, `data_coverage_status`, `production_eligible=false`, `source_data_lag_seconds`, `model_bundle_manifest_sha256`。
- 因果：`source_latest_available_at_utc <= signal_cutoff_utc <= created_at_utc < outcome_available_at_utc`；所有時間 UTC offset-aware，台灣市場日另記 TPE `session_date`。未有 outcome 時先寫 `PENDING`，不得填入市場結果。
- 寫入：授權私有 GCS **create-only**（`if_generation_match=0` 或等效 compare-and-swap），同 key 再送只准位元一致、checksum readback；非一致須 `CONFLICT` 且故障告警，不可覆寫舊觀察。預測記錄與敏感行情／權重不對外公開。
- `p_up` 需是 0～1 有效有限數；校準未驗證時明確 `probabilities_verified=false`，手機不能顯示為「已驗證上漲機率」或交易買點。缺模型 manifest、錯位時間或來源超時直接 `DATA_BLOCKED`。

## 5. 事後結果對帳（Markout）
- `outcome_key` 一對一引用 `prediction_key`；另存 `outcome_source`, `session_calendar_version`, `label_start_at_utc`, `label_end_at_utc`, `observed_at_utc`, `outcome_available_at_utc`, `outcome_sha256`, `outcome_status`, `missing_reason`。
- 僅在市場結果真實可得後另存獨立 create-only 記錄，標記 `PENDING/COMPLETE/INVALID/MISSING`；不得回填改寫原預測。
- 同一股票同日重複掃描不當作多個獨立交易；`trade_id` 與 `session_date` 必須區分。追蹤缺口率、原始資料日期、成功/失敗時間、重試次數、重複比率及 outcome completeness。

## 6. 研究充分性與升版阻擋
- 前瞻 Shadow ≥200 **可評估獨立樣本**、≥20 **真正未來交易日**、≥2 Regime、結果完整率 ≥95%、單股集中度 ≤20%。
- 另需完整成本 0.45% 主情境、0.65% 壓力情境（依正式 Protocol；與使用者實際 Profile 分開）、成交率/滑價/交易稅、PF、成本後期望、最大回撤、持倉重疊、容量及至少 3-fold walk-forward；無法計算就標示 `NOT_VERIFIED`。
- 未驗證模型在手機上只能標 `研究觀察／待確認`，絕不得產生正式 `買進`／`加碼` 指令。
- `PRODUCTION` 的 Sky 當沖 v1.4 與 Sky Swing V1.0 不變；任何策略升版須 W0／P0-G 完整審查。

## 7. W0 可審核的逐項 Acceptance Checks
| Gate | Evidence required | Current decision |
|---|---|---|
| 結構性新假設與凍結登錄 | W0／P0-G signed registration ID + SHA | **BLOCKED** |
| PIT/Label／鐘點契約 | TPE session / offset-aware timestamp fixture + real source as-of | **PARTIAL / BLOCKED** |
| 模型、校準器、預處理可重播 | 私有 artifact + SHA + readback + pinned dependencies | **NOT VERIFIED** |
| Prediction-before-outcome | 新交易日 immutable create-only + outcome delay | **NOT VERIFIED** |
| 研究本身具有方向增益 | fresh forward vs train-only no-skill comparator | **NOT VERIFIED** |
| 成本、成交、風控及足夠樣本 | Protocol Gate 0–10 | **NOT VERIFIED** |
| Production qualification | W0／P0-G formal sign-off | **NO_TRADE** |

> 此提案不執行新的 ML 訓練／前瞻自動排程；下一步是 W0 審查接受、要求修改或 HOLD。任何 PR CI 成功只能驗證此文件可讀性，不能等同模型、真實 GCS、資料或策略驗證通過。
