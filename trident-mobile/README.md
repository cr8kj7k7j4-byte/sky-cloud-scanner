# TRIDENT iPhone 工作站｜獨立部署

## 目前可用
- iPhone Safari 繁體中文介面（無需安裝 App）
- 離線基本介面、JSON 訊號匯入、時間戳過期保護、訊號觀察列表
- 多空交易風險試算：依使用者自行輸入的進場、停損、目標、股數及來回成本估計損益／RR
- 本機交易計畫紀錄（**不是**券商持倉），僅保存在當前 Safari 的 localStorage。

## 上線限制
- 禁止自動下單、禁止未驗證的正式 LONG / SHORT 交易訊號；預設 NO TRADE。
- **未接通** Nova API、沒有行情掃描服務、沒有實盤帳戶串接、沒有推播或自動通知。
- 匯入 JSON 無法證明行情來源合法性；validated 欄位不能解除禁令。
- 風險計算為近似值，未含融券/借券成本、股息及部分保證金和撮合限制；空單交易資格須在券商確認。
- 不要將憑證、API 金鑰、私鑰、帳戶資訊放到此公開 Repo 或網頁前端。

## 上線驗收
1. 先確認 GitHub Pages/HTTPS 的部署來源與權限；**不要直接將 main 的 Sky 系統覆寫**。
2. 用 iPhone Safari 測試縱向顯示、加到主畫面、輸入表單、localStorage、重新整理與清除。
3. 僅在伺服器端使用 Nova 認證/行情來源；檢查 TWSE/TPEx 涵蓋、交易時段、新鮮度、斷線與錯誤復原。
4. 策略樣本外與成本後驗證通過前，僅可作為行情觀察／模擬結果。
5. 通過資料／交易風控、通知與故障復原驗收後，才考慮標示實盤可用。

## 部署
GitHub Actions workflow `.github/workflows/trident-iphone-pages.yml` 已準備從獨立 branch 部署 `trident-mobile/`。首次需在 Repository Settings → Pages 中選擇 **GitHub Actions**；若未啟用，workflow 會因權限或 Pages 設定而失敗。公開部署不應包含敏感資訊。

## JSON 範本
```json
{
  "as_of": "2026-11-09T09:05:00+08:00",
  "source": "示例，非真實行情",
  "coverage": "未驗證",
  "signals": [
    {"symbol":"0000","name":"範例","side":"WATCH","entry":0,"stop":0,"target":0,"validated":false}
  ]
}
```
