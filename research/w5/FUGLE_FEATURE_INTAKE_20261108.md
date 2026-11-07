# 富果 Fugle 資料能力與選股策略 W5 Intake（2026-11-08）

**狀態：HOLD / INTAKE_ONLY；非預註冊、非 Production、無交易訊號。**

## 目的與來源分級
使用者已購買富果開發者方案，提出富果網站的市場排行、三多風向圖（短線起漲／長線多方／波段趨勢）、壓力參考區間、法人 OD、券商分點、營收與事件選股畫面。這些**網站功能不等於可經 API 取得其專有模型規則或輸出**；禁止逆推專有演算法或宣稱已驗證其報酬。

- A：GitHub 現有程式與測試：`src/fugle.py`、`.github/workflows/fugle-paid-api-acceptance.yml`、`src/diagnose_sources.py`、`.github/workflows/w3a-fugle-pit-coverage-probe.yml`。
- B：富果公開行情 API 文件：<https://developer.fugle.tw/docs/data/http-api/getting-started/>、<https://developer.fugle.tw/docs/pricing/>；實際 entitlement 需 GitHub runner 實測。
- C：使用者提供網站截圖：僅證明頁面顯示選股卡片與排行，不證明 API 可取用 proprietary signals。

## 避免重工：先做現有付費 API Acceptance

既有 `fugle-paid-api-acceptance.yml` 已含六項手動測試：
1. TSE common stock snapshot。
2. OTC common stock snapshot。
3. 2330 TSE quote。
4. 6488 OTC quote。
5. 2330 daily historical candles。
6. 2330 one-minute historical candles。

手動測試網址：<https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/workflows/fugle-paid-api-acceptance.yml>。
產出：`fugle-api-acceptance` artifact / `fugle_api_acceptance.json`，不印出憑證。**Workflow 存在不代表本次已成功執行**。舊版 `docs/SKY_UNIFIED_LATEST_SYSTEM_HEALTH.json`（2026-11-06 本地時間）仍記錄 TSE/OTC snapshot `plan_restricted`；應於新方案下重新取得實際測試證據，不能假定權限已更新。

Acceptance 後需另做交易時間 freshness / listing coverage / response field contract / per-symbol PIT / historical completeness / L1 spread/slippage；靜態週末資料不可當即時通過。

## 富果網站候選功能之去重與處置

| 畫面/概念 | W5 處置 | 原因與必要新證據 |
|---|---|---|
| 三多短線起漲雷達 | REJECT_DUPLICATE（作為現有突破 Alpha） | 已封存 5m breakout、Top100 velocity、opening retest/reclaim；無新 PIT 資料、label、execution architecture 不得重開 |
| 三多波段趨勢雷達 | HOLD / FEATURE_ONLY | 已有 Trend Persistence / Swing 研究；先證明不重複與 PIT 新資訊 |
| 三多長線多方雷達 | HOLD / FEATURE_ONLY | 均線趨勢概念重疊；無獨立可驗證 Edge 證據 |
| 壓力參考區間 | HOLD / DATA_FEASIBILITY | 可自行以 PIT OHLCV/分價量建候選 feature；不可宣稱還原富果 proprietary 公式；若僅重新包裝突破策略則 REJECT |
| 三多風向球日週 K | REJECT_LOW_VALUE（作為新 Alpha） | 基礎多週期技術指標變體不足以構成結構差異 |
| 券商分點集中 | HOLD / HARD_DATA_GATE | 已有 Broker Identity Flow HOLD；先證明 PIT 分點 ID、換券商、資料授權、歷史時間戳 |
| 機器學習法人 OD | HOLD / UNVERIFIED_VENDOR_LOGIC | 名稱不構成預測力；API proprietary output 未證實；不得將黑盒當可回測真值 |
| 三大法人買賣超 | FEATURE_ONLY | 使用已知資料但注意盤後發布時序，不得作同日盤中訊號 |
| 營收穩健成長 | HOLD / HISTORICAL_PIT_BLOCKED | 既有 Revenue MoM/YoY 研究缺真正歷史發布時刻；禁止以月分代替可知時間 |
| 事件型選股 | HOLD / DUPLICATE_RISK | 過去 Stage 6 催化因子家族封存；不同 target/time-causality 才能新立項 |

## 三套新模型資料需求（不是研究升版授權）

- **雙向當沖**：市場快照用於候選；即時五檔、成交時間與分鐘 K 用於多空獨立訊號、spread、滑價與借券／先賣後買資格。舊 Top100/突破規則不得換名稱重跑。
- **隔日**：先明確定義隔日開盤/收盤/可成交價 label，使用 PIT 收盤可知特徵、隔日成交機制與成本；先 deterministic/linear baseline。
- **波段**：日週 K、交易日有效股票池、盤後實際公告時間與籌碼；3–20D、Portfolio overlap、成本／容量；不可直接複製當沖觸發。

## 必須滿足的 Gate

遵守 `SKY_SYSTEM_REGISTRY_V2_1.md`、`research/RESEARCH_FREEZE_REGISTRY.md`、`docs/SKY_VALIDATION_PROTOCOL_V1_0.md`、`docs/SKY_V2_1_BASELINE_FREEZE_20261025.md`、`docs/SKY_MASTER_CONTROL_STATUS_20261025.md`。

- No threshold/indicator/Top-N/weight retuning of `ARCHIVED_NO_RETUNE` families。
- Data/PIT → pre-registration → train/validation/OOS → walk-forward/regime → 0.45% main + 0.65% stress research round-trip costs → portfolio/short eligibility/capacity → Shadow/Paper → W0/P0-G。
- Shadow/Paper minimum 200 evaluable independent samples, 20 real future trading days, >=2 regimes, >=95% completeness, <=20% per-symbol share。
- 已有使用者成本 profile 可用來作 sensitivity，但成本完整滑價與成交品質仍未驗證。
- 不更動原有 Production、Actions schedules、API secrets、交易指令；不使用 Nova。
- 未取得新方案驗收執行紀錄前，本文件不得宣稱全市場即時行情恢復，也不得升級策略。

## 下一步完成條件

(1) 以 GitHub Actions 手動執行既有 `Fugle Paid API Acceptance (Manual)`，讀取最近一次 Run 的每項欄位與 artifact；(2) 若權限或 schema 不符，修正既有驗收程式與介接，測試後提交獨立 PR；(3) 在驗收成功前暫不擴張 Alpha；(4) 新 Alpha 僅可在 W0 核准結構性預註冊後開始。

**本次執行證據**：治理與現有程式已讀取；尚未觸發 Actions、未取得新購方案即時驗收結果，故狀態仍為 HOLD。

## 2026-11-08 03:50 TPE — Actual paid API acceptance evidence

- GitHub run: <https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/42408149213>
- Trigger: **push**, not scheduled cron. Run conclusion: **success**; job `validate` success; artifact `fugle-api-acceptance` uploaded successfully (artifact ID 13588386919).
- Runner log confirms all six HTTP 200 checks:
  - TSE snapshot: PASS / 1,060 rows; payload date 2026-11-06 14:00.
  - OTC snapshot: PASS / 892 rows; payload date 2026-11-06 14:00.
  - TSE quote 2330: PASS / one quote; payload date 2026-11-06.
  - OTC quote 6488: PASS / one quote; payload date 2026-11-06.
  - Historical 2330 daily candles: PASS / 10 rows.
  - Historical 2330 one-minute candles: PASS / 266 rows dated 2026-11-06.
- Important distinction: snapshot counts **1,952 combined records** but not yet matched to same-date canonical TSE/OTC universe; do not assert certified % coverage.
- This weekend test proves paid API entitlement and basic payload acceptance, **not** same-session executed quotes, valid fill, portfolio P&L, or positive expectancy.
- `src/main.py` currently deliberately blocks using Fugle bulk snapshot to fill executed-price holes in live scanner; `src/realtime_quote_evidence.py` requires a verifiable last-execution time. Keep the fail-closed trading gate unchanged.
- PR #303 merged (commit `37c5698`) to monitor basic six-point entitlement every 30 minutes via GitHub schedule `*/30 * * * *`, UTC and Taiwan minute :00/:30. The successful run above is push-triggered. Scheduled-trigger accuracy, notification receipt and all-market live executed-price coverage remain **UNVERIFIED**.
- No auto-remediation agent has been granted write access; do not interpret repeated monitoring as self-healing software.
