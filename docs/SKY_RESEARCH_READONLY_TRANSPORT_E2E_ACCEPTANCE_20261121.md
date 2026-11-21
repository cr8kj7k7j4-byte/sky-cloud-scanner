# Sky 研究級唯讀掃描通道｜端到端驗收紀錄（2026-11-21）

狀態：**READ_ONLY_RESEARCH_TRANSPORT_ACCEPTED**；整體研究系統正式全功能上線：**HOLD / INSUFFICIENT_DATA**。  
自動下單：**禁止**。研究策略升級 Production：**禁止**。模擬交易帳本：**已永久移除，不得恢復為交付門檻**。

## 來源與同次證據

- Repository: `cr8kj7k7j4-byte/sky-cloud-scanner`
- `main` scan SHA: `a810d7ca56ff759e8b4d708174d534fc5f91b86d`
- 唯讀 Request ID: `research-go-live-20261121-gate-b2`
- 正式主分支 GitHub Actions Run: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44897085604
- Run conclusion: **SUCCESS**（最終 fail-closed research-readback gate PASS）
- 富果預約 Artifact: `sky-fugle-reservation-83429406ed604ce6-5984196`，預約上傳與 ZIP 內容驗證 PASS。
- 研究掃描報告 Artifact: `sky-chat-44897085604`（Artifact ID `14704457603`）。
- 同次獨立讀回 Artifact: `sky-chat-external-readback-44897085604`（Artifact ID `14704372818`）。
- 獨立讀回 receipt: `PASS_RESEARCH_ONLY`，`production_eligible=false`、`automatic_order=false`、`trade_action=禁止交易`。
- Workflow final evidence: `RESEARCH_READBACK_VERIFIED_NO_ORDERS`。

## 行情品質與適用界線

- 資料擷取：**2026-11-21 19:01:42 台灣時間**（非正常交易時段）。
- 來源標記：`FUGLE_PAID_SNAPSHOT`。
- Universe / report rows：**1,986 / 1,986**。
- 有參考價：**1,942**，約 **97.78%**；剩餘 44 檔不可解讀為有效成交或即時完整行情。
- TWSE 有參考價：**1,059 / 1,091**；TPEx：**883 / 895**。
- 可認證的新鮮成交時間：**0**；Stage 2 成交驗證：**0**。
- Stage 1 候選股：**0**；五分鐘 K API requests：**0**；未形成合格進場訊號。
- 本次 **只驗證唯讀行情傳輸、預約、報告產出及同次 Artifact 可讀回**，不證明盤中新鮮成交覆蓋率、五分鐘 K 訊號、可買進標的、成本後 RR 或實際成交能力。

## 分項驗收判定

| 工作項目 | 結果 |
| --- | --- |
| 模擬帳本移除與防回歸 | 已合併，防回歸 CI PASS |
| 手機讀回契約 / SHA / request ID | 已合併，CI PASS |
| 主分支單次富果共用預約、上傳與獨立驗證 | **PASS（本 Run）** |
| 富果唯讀報告與同次獨立 Artifact 讀回 | **PASS（本 Run）** |
| 不得下單、不符合研究條件即 fail closed | **PASS（本 Run）** |
| 跨所有付費 Workflow 同範圍並行只呼叫一次 | **待驗證；#536 / #543** |
| 盤中新鮮成交時間及資料品質 | **待交易時段驗證** |
| 五分鐘 K / VWAP / 成本後 RR / A+ 訊號 | **本 Run 無證據；不得認證** |
| 整體研究系統正式全功能上線 | **HOLD** |

## W0 / P0-G 治理界線

本文件僅確認「**研究級唯讀手機掃描通道技術可用**」，不改變原本 Production 版本，不宣告交易能力或策略有正期望。研究級全功能結案要依證據另行審查，不得用單次非交易時段成功取代盤中驗證。研究狀態維持 `HOLD / INSUFFICIENT_DATA`。不為加速上線降低資料與風控門檻。
