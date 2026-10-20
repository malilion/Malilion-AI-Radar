# 每日晨報

每小時自動更新的新聞彙整網站，部署在 GitHub Pages：<https://malilion.github.io/google-news/>

## 版面

編輯感報刊設計（米白紙＋墨黑＋印章朱紅，自動深色模式；標題思源宋體、內文思源黑體），單頁由上而下：

- **報頭**：國曆／民國／農曆日期、期號（2026/10/20 創刊第 1 期）、最後更新時間；捲動後收成頂部導覽列
- **A1 頭版**：頭條、兩則次要新聞、三則短訊
- **A2 要聞**：多欄列表，可搜尋（按 `/`）、依媒體篩選、只看未讀
- **B1 社群版**：Threads 引述卡，可依帳號篩選
- **C1 科技副刊**：Unwind AI 橫向捲動封面卡
- **已讀與收藏**：點過的文章變淡；☆ 收藏後按 `s` 開啟收藏夾。兩者都只存在瀏覽器（localStorage）

前端檔案：`site/index.html`、`site/styles.css`、`site/app.js`（無框架、無建置步驟）。

## 內容

| 版面 | 來源 | 說明 |
|------|------|------|
| A1 頭版、A2 要聞 | [Google 新聞 RSS（台灣）](https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant) | RSS 前 6 則排進頭版，其餘進要聞 |
| B1 社群版 | [threads-toolkit](https://github.com/Chuanyin1202/threads-toolkit) | 追蹤帳號近 72 小時的貼文，依互動分數（讚 + 回覆×2 + 轉發×3）排序 |
| C1 科技副刊 | [Unwind AI 電子報 RSS](https://rss.beehiiv.com/feeds/fMHDv0Uk41.xml) | 最新 30 篇文章，標題與摘要自動翻譯成繁體中文 |

## 運作方式

GitHub Actions（`.github/workflows/update-news.yml`）每小時整點執行一次，也可手動執行，每次會：

1. `scripts/fetch_news.py`：抓 Google 新聞，輸出 `site/news.json`
2. `scripts/fetch_unwind.py`：抓 Unwind AI RSS 並翻譯，輸出 `site/unwind.json`
3. `scripts/fetch_threads.mjs`：用 threads-toolkit（固定版本）逐一抓追蹤帳號的個人頁，輸出 `site/threads.json`。帳號之間間隔 20–40 秒、抓到 0 則會重試一次，每抓完一個帳號就存檔，整步上限 40 分鐘
4. 把 `site/` 部署到 GitHub Pages

資料檔不放進版本庫（見 `.gitignore`），每次都是現抓現部署。Unwind AI 與 Threads 兩步失敗時不影響其他部分，對應版面會顯示「暫時沒有資料」。

## 設定

- **Threads 帳號與關鍵字**：編輯 `threads-keywords.json`。目前追蹤 `dcard.tw`、`ithome`、`cool3c`、`kocpc`、`ai.lanrenbao`、`darrell_tw_`、`c.yu.an_`、`kelly_guooo`、`lazyoffice2024`、`ironv.careerlife`。`accounts` 是要追蹤的帳號（不含 @），有填就以帳號模式依互動分數排序；`keywords` 是搜尋模式（未登入時對中文關鍵字常抓不到結果）。
- **翻譯**：到 Settings → Secrets and variables → Actions 新增 `ANTHROPIC_API_KEY`。沒有設定時 Unwind AI 會顯示英文原文。翻譯結果以文章連結為鍵快取，只有新文章才會呼叫 API。
- **更新頻率**：修改 workflow 裡的 `cron`（UTC 時間）。
- **首次啟用**：Settings → Pages → Source 選 **GitHub Actions**，再到 Actions 手動執行一次 "Update news"。

## 注意事項

- Threads 抓取是用瀏覽器自動化讀取公開頁面，可能被登入牆或機房 IP 限制擋下，且可能不符合 Threads 使用條款，請自行評估。
- 頭版排序沿用 Google 新聞 RSS 的順序，不是實際閱讀數。

## 資安設計

- **隔離第三方程式**：Threads 抓取會執行 threads-toolkit 與其 npm 依賴，因此放在獨立的 `threads` job，只有 `contents: read`，拿不到部署權限、OIDC 與 secrets；它產出的 JSON 交給 `deploy` job 前，先經過 `scripts/sanitize_threads.py` 檢查欄位、型別、長度，連結只留 `https://www.threads.com/`。
- **最小權限**：workflow 預設 `permissions: {}`，所有 checkout 都不保存憑證（`persist-credentials: false`）；`ANTHROPIC_API_KEY` 只給翻譯那一步。
- **前端**：所有外部內容都用 `textContent` 輸出；連結與圖片只接受 http(s)；頁面帶 Content-Security-Policy，只允許自家腳本與 Google Fonts。

## 本機測試

```bash
python3 scripts/fetch_news.py
python3 scripts/fetch_unwind.py
cd site && python3 -m http.server 8000   # 開啟 http://localhost:8000
```
