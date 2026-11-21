# Sky 研究級唯讀系統｜2026-11-21 上線與驗收紀錄

**範圍結論：RESEARCH_READ_ONLY_OPERATIONAL（唯讀研究操作鏈可用），正式交易策略／新進場訊號：HOLD / INSUFFICIENT_DATA。**

本紀錄僅對 GitHub Actions 研究級行情觀察、風控限制、Artifact 上傳及同次讀回作成操作性驗收；**不等於**行情「即時成交認證」、正式交易系統上線、策略正期望成立、Production 升版或自動下單核准。

## 已取得且可核對的實際證據

- 正式 `main` GitHub Workflow `Sky Chat On-Demand Scan Bridge`：[Run 44897085604](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44897085604) 在 SHA `a810d7ca56ff759e8b4d708174d534fc5f91b86d` 成功；預約 ZIP 驗證、富果 Snapshot、13 欄報告上傳、獨立下載同次 Artifact 及 `RESEARCH_READBACK_VERIFIED_NO_ORDERS` 全通過。報告 Artifact `14704457603`；獨立讀回 `14704372818`。該舊版母體含已排除的 31 檔，總計 1,986 檔，屬前版來源證據。
- 研究分支 SHA `41b924519ac4a20e51c56a6ddd160ffea8c9dae8`：[Run 44897472102](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44897472102) 成功；`PASS_RESEARCH_ONLY`。2026-11-21 台灣時間約 19:07 擷取、前一交易日 2026-11-20 富果 Snapshot：研究母體 **1,955** 檔，參考價 **1,942** 檔（99.34%），上市 1,060、上櫃 895。報告 Artifact `14704523244`、讀回收據 `14704856275`，同一 Run／SHA／Request ID 核對通過。可認證實際成交時間 **0** 檔，Stage2 及完成五分鐘 K 棒證據 **0**，`禁止交易`。
- 排除 31 檔創新板／研究指定代碼：合併 [PR #558](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/558)，main merge SHA `cafd44cc82cb16b0ab6ce5bd22dc8d55c043f60f`；CI **21/21 PASS**。保留官方母體來源，研究掃描排除代碼、排除前母體數均以報告欄位記錄。**上項 1,955 實跑來自研究分支，非該 main merge SHA 的獨立再掃**。
- 完整 GitHub 讀回驗證含 exact SHA：合併 [PR #552](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/pull/552)，CI **20/20 PASS**。
- 同一真實富果唯讀端點受控跨 Workflow A／B：[Run A #44895886977](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44895886977)、[Run B #44895886923](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44895886923)。同 SHA、同請求鎖，一方 `DUPLICATE_BLOCKED`（0 HTTP），另一方 `ATOMIC_WINNER`（1 real HTTP 200）；此項仍只是受控端點，**不證明全 Repository 的 #536／#543 已整合**。
- 舊模擬帳本 #508／#544 已關閉；#547／#548 已合併；不得恢復專用委託／成交／持倉／損益／重播、測試或交付依賴。


## 2026-11-21 main 最新受控運行（Run #58；驗證於同日）

- **直接查核 GitHub Job 全部步驟及日誌**：[Run 44899169535](https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/44899169535)、`main` SHA `381c705218da4af092bbb6f0c7fcd048e194ff4a`、request ID `research-go-live-20261121-gate-c3`：Workflow **success**，獨立讀回與最後 fail-closed 驗證均 success。
- 富果付費請求保留共享預約及獨立 ZIP 驗證：Artifact `14704804938`；13 欄研究報告及狀態 Artifact `14704864249`；同次 SHA/Run ID/Request ID 的外部獨立讀回收據 Artifact `14705496228`，收據狀態 `PASS_RESEARCH_ONLY`，最後印出 `RESEARCH_READBACK_VERIFIED_NO_ORDERS`。
- 母體 **1,955** 檔（TWSE **1,060**、TPEx **895**；已按研究範圍排除指定創新板 31 檔）。觀察到參考價 **1,942** 檔（**99.34%**；TWSE **1,059**、TPEx **883**）。快照擷取時間台灣時間 **2026-11-21 19:27**，為非交易日；參考價不代表當日有效成交價。
- **可認證實際成交時間 0、Stage1 候選 0、Stage2 試請求 0、Stage2 認證成交 0、五分鐘 K 棒 API 試請求 0、五分鐘 K 棒觀測 0、VWAP 認證 0**。Stage1 排除原因 `NON_CURRENT_SNAPSHOT_DATE: 1955`，是週末資料新鮮度防護，不應放寬或繞過。
- **正式判定**：`RESEARCH_READ_ONLY_OPERATIONAL = PASS`（完整唯讀研究執行／同次 Artifact 讀回），`LIVE_INTRADAY_STRATEGY = HOLD / INSUFFICIENT_DATA`、`NO_TRADE`、`production_eligible = false`、`automatic_order = false`。跨 Workflow 全入口付費去重仍需獨立真實實跑，不能以預約步驟成功取代完整證據。
- `#561`～`#568` 修復與掃描驗收請求已合併至 `main`。未恢復已停用的 #508 模擬帳本，不新增專用模擬交易流程。上述證據是 **單次** 完成後的不可變驗收紀錄，不宣稱後續交易日的行情或策略結果。

## 持續性的安全邊界

1. 唯讀研究服務由既有 GitHub Actions `sky-chat-bridge.yml` 提供；不新增重複執行器、排程、雲端部署或券商下單。
2. 所有資料時間、來源、涵蓋率、實際成交時間、K 棒、風控及成本後 RR 分別核對。參考價 ≠ 已認證成交價；週末盤後舊快照不可宣稱盤中即時。
3. 付費 API 預約、外部讀回、新鮮度與 SHA 檢查應 fail closed；`DUPLICATE_BLOCKED`、`RECENT_RESERVATION`、取消或讀回失敗須紀錄，不得重標為 `PASS`。#44897574479 主分支失敗及 #44897562567 取消是保留的未通過紀錄，不得隱藏。
4. 整體未驗收：#511 雙市場正式整合、#536／#543 跨 Workflow 全入口整合、完整五分鐘 K／VWAP／交易日因果性、合格交易訊號，及由 ChatGPT 對話直接 dispatch 的端到端證據。沒有 A+ 時禁止新進場。
5. 正式研究模型升版及 Production 仍須 W0／P0-G 依治理協議獨立審查，無論研究服務運行是否成功。

## 驗收分層

| 驗收層 | 判定 |
| --- | --- |
| 研究級唯讀掃描／同次 Artifact 讀回操作鏈 | **PASS（有實跑證據）** |
| 31 檔正式排除程式及主分支 CI | **PASS（#558 已合併）** |
| 完整即時成交資料與五分鐘 K 棒交易策略 | **INSUFFICIENT_DATA** |
| 全付費入口原子去重之正式主分支整合 | **HOLD** |
| 自動交易、正式 Production 策略 | **禁止／未核准** |

此檔案為一次性已核對的上線驗收快照，**不是**自動更新行情的即時狀態檔。任何未來執行的成功或失敗，須依其獨立 Run ID、SHA 和 Artifact 重新判定。
