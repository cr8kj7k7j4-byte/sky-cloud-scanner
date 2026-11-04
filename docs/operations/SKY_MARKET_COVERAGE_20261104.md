# Sky 全市場行情覆蓋率修復驗證（2026-11-04）

## 結論
- **盤中全市場最新成交價覆蓋率仍不合格**，不可視為全市場交易訊號來源，狀態 `BLOCKED_EXTERNAL_DATA`。
- 最後一輪實跑 2026-11-04 09:25～09:27 Asia/Taipei：官方母池 1,985，當日可解析最新成交價 90，覆蓋率 **4.53%**（TWSE 48 / OTC-MIS 備援 42）。
- 11/03 盤後研究掃描曾達 **88.87%（1,764/1,985）**，不得視為盤中覆蓋率驗證。

## 根因與實際證據
1. TWSE MIS 回傳 1,985 檔代碼，但多數最新成交欄位 `z='-'`，即使有當日 O/H/L/V。不能把昨收、委買、委賣、最高、最低視為最新成交價。
2. 2026-11-04 初次小批次重查共 1,914 個 symbol requests，新增有效報價 37 檔，遇到 84 次請求失敗（502／連線拒絕／連線中斷），耗時約六分鐘，不可繼續無界重試。
3. 改成最多80檔分散抽樣的受控重查後，實際補查79檔，**新增0檔有效最新成交價**，顯示不能透過批次大小解決來源缺值。
4. Fugle `/snapshot/quotes/TSE`、`/snapshot/quotes/OTC` 均回傳 HTTP 403，現有 GitHub API 金鑰無整批快照權限。
5. TPEx/OTC 的 MIS 報價屬於 operational fallback，不能宣稱為 TPEx 官方完整即時行情。

## 已完成程式作業
- 修正 `src/official.py` 針對 MIS 缺漏與 `z='-'` 進行分散且有上限的診斷補查；增加連續失敗保護與診斷欄位。
- `src/swing_live_scanner.py` 優先嘗試 Fugle 整批快照，失敗才使用 MIS 備援，來源與覆蓋率分列。
- `tests/test_official_mis_coverage.py` 七項測試全部通過。
- `.github/workflows/swing-live-scan.yml` 對不完整覆蓋率 fail closed，並保留產物，不能用成功上傳報告當作全市場資料通過。
- 不修改 Production 策略、停損及選股門檻，不自動下單。

## 證據連結
- 2026-11-04 第一輪深入補查: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41752878285
- 2026-11-04 受控補查最終實跑: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41753909941
- 2026-11-03 盤後研究掃描: https://github.com/cr8kj7k7j4-byte/sky-cloud-scanner/actions/runs/41605448978

## 未完成／解除阻擋條件
1. 必須取得一個**獲合法授權、提供交易日時間戳及已成交最新價**的上市+上櫃盤中整批來源，或另行研究前日官方收盤橫斷面 + 少數候選 Fugle 即時深查的分層設計（須明確標註為不同資料範圍）。
2. 在至少一個交易日重新實測：母池／上市與上櫃各自有效筆數、來源、時間戳、過期率、回傳錯誤與80%覆蓋門檻、完成耗時。多日穩定性另驗證。
3. 正式 Sky Swing V1.0 exact executable rule spec 仍需 W0 獨立治理審查；資料改善不能等同 Production 訊號通過。
