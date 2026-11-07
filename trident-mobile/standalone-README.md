# TRIDENT 獨立 iPhone 工作站｜專用儲存庫部署
此套件只發布**未連接券商的研究／風控工作站**。未介接經授權即時行情，未完成樣本外策略驗證。畫面預設 NO TRADE，**不得視為可實盤交易訊號**。

## 上線步驟
1. 在 GitHub 手動建立**全新的**儲存庫，例如 `trident-iphone-workstation`。不要在既有 `sky-cloud-scanner` 啟用這套發布流程。
2. 解壓 `trident-standalone-site.zip`，將**解壓後的檔案及隱藏的 `.github` 目錄**上傳到新儲存庫的 `main` 分支。不要只上傳 ZIP 本身。
3. 新儲存庫開啟 Settings → Pages → Build and deployment → Source: **GitHub Actions**。
4. 查看 Actions → `TRIDENT Standalone Pages Deployment`，確認 workflow 全部成功，並取得 Pages 顯示的實際 HTTPS URL。
5. 使用 iPhone Safari 開啟該 URL，檢查總覽、訊號、風控、設定、資料匯入及重新整理。再選擇「分享 → 加入主畫面」。
6. 任何未取得真實部署網址、手機實測證據、授權行情或策略樣本外驗證的項目，維持**未完成**。

## 安全限制
- 部署 workflow 內建保護：在 `cr8kj7k7j4-byte/sky-cloud-scanner` 儲存庫不執行 deploy job。
- 絕對不要把 Nova API 憑證、登入密碼、憑證私鑰或 token 寫在網站程式碼或公開 GitHub 儲存庫。
- GitHub Pages 是靜態網站，不能安全地直接持有券商認證秘密或在伺服器端執行 Nova 認證。
- 做空資格、交易成本、真實行情與策略獲利均尚未驗證；不自動下單。
- 舊 Sky 正式策略與工作流程不得因本套件而修改或恢復啟動。

## 發行套件包含
- `index.html`：獨立繁體中文手機工作站。
- `manifest.webmanifest`：加入手機主畫面時使用。
- `.github/workflows/pages.yml`：專用儲存庫 HTTPS 自動部署。
- `README.md`：本說明。

如果 GitHub Pages 無法啟動，應先確認新儲存庫 Pages 權限與 GitHub 帳號／方案要求，不要把發行流程切換回 Sky 原有網站。
