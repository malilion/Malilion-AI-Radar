# 台灣新聞速報

每小時自動更新的新聞彙整網站，部署在 GitHub Pages：<https://malilion.github.io/google-news/>

## 內容

| 分頁 | 來源 | 說明 |
|------|------|------|
| 新聞 | [Google 新聞 RSS（台灣）](https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant) | 最上方顯示「最熱門 Top 3」（取 RSS 前三則），可搜尋、依媒體篩選 |
| Threads 熱門 | [threads-toolkit](https://github.com/Chuanyin1202/threads-toolkit) | 抓追蹤帳號清單的近期貼文，依互動分數排出熱門（也支援關鍵字搜尋模式） |
| Unwind AI | [Unwind AI 電子報 RSS](https://rss.beehiiv.com/feeds/fMHDv0Uk41.xml) | 最新 30 篇文章，標題與摘要自動翻譯成繁體中文 |

## 運作方式

GitHub Actions（`.github/workflows/update-news.yml`）每小時整點執行一次，也可手動執行，每次會：

1. `scripts/fetch_news.py`：抓 Google 新聞，輸出 `site/news.json`
2. `scripts/fetch_unwind.py`：抓 Unwind AI RSS 並翻譯，輸出 `site/unwind.json`
3. `scripts/fetch_threads.mjs`：用 threads-toolkit（固定版本）依關鍵字抓 Threads，輸出 `site/threads.json`
4. 把 `site/` 部署到 GitHub Pages

資料檔不放進版本庫（見 `.gitignore`），每次都是現抓現部署。Unwind AI 與 Threads 兩步失敗時不影響其他部分，該分頁會顯示「尚無資料」。

## 設定

- **Threads 帳號與關鍵字**：編輯 `threads-keywords.json`。`accounts` 是要追蹤的帳號（不含 @），有填就以帳號模式依互動分數排序；`keywords` 是搜尋模式（未登入時對中文關鍵字常抓不到結果）。
- **翻譯**：到 Settings → Secrets and variables → Actions 新增 `ANTHROPIC_API_KEY`。沒有設定時 Unwind AI 會顯示英文原文。翻譯結果以文章連結為鍵快取，只有新文章才會呼叫 API。
- **更新頻率**：修改 workflow 裡的 `cron`（UTC 時間）。
- **首次啟用**：Settings → Pages → Source 選 **GitHub Actions**，再到 Actions 手動執行一次 "Update news"。

## 注意事項

- Threads 抓取是用瀏覽器自動化讀取公開頁面，可能被登入牆或機房 IP 限制擋下，且可能不符合 Threads 使用條款，請自行評估。
- Google 新聞的「最熱門」依 RSS 排序，不是實際閱讀數。

## 本機測試

```bash
python3 scripts/fetch_news.py
python3 scripts/fetch_unwind.py
cd site && python3 -m http.server 8000   # 開啟 http://localhost:8000
```
