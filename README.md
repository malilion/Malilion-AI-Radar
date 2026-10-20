# 每日晨報

每小時自動更新的新聞彙整網站，部署在 GitHub Pages：<https://malilion.github.io/google-news/>

## 版面

編輯感報刊設計（米白紙＋墨黑＋印章朱紅，自動深色模式；標題思源宋體、內文思源黑體），單頁由上而下：

- **報頭**：國曆／民國／農曆日期、期號（2026/10/20 創刊第 1 期）、最後更新時間；捲動後收成頂部導覽列
- **A1 頭版**：頭條、兩則次要新聞、三則短訊
- **A2 要聞**：多欄列表，可搜尋（按 `/`）、依媒體篩選、只看未讀
- **B1 社群版**：Threads 引述卡，可依帳號篩選
- **C1 科技副刊**：Unwind AI 橫向捲動封面卡
- **C2 AI 業界動態**：官方部落格／科技媒體兩個分頁，可依來源篩選
- **C3 開發者雷達**：GitHub 趨勢／Hacker News／論文／部落格／Reddit／版本更新六個分頁，排行榜類顯示名次
- **C4 社群與活動**：近期社群活動與加入社群連結
- **往期**：每天的版面都存檔，按「往期」（或 `p`）選日期回看，網址為 `?d=YYYY-MM-DD`
- **已讀與收藏**：點過的文章變淡；☆ 收藏後按 `s` 開啟收藏夾。兩者都只存在瀏覽器（localStorage）

前端檔案：`site/index.html`、`site/styles.css`、`site/app.js`（無框架、無建置步驟）。

## 內容

| 版面 | 來源 | 說明 |
|------|------|------|
| A1 頭版、A2 要聞 | [Google 新聞 RSS（台灣）](https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant) | RSS 前 6 則排進頭版，其餘進要聞 |
| B1 社群版 | [threads-toolkit](https://github.com/Chuanyin1202/threads-toolkit) | 追蹤帳號近 72 小時的貼文，依互動分數（讚 + 回覆×2 + 轉發×3）排序 |
| C2 AI 業界動態 | `ai-feeds.json`：**官方部落格**（OpenAI、Anthropic（新聞／研究／Claude）、Google DeepMind、Google AI、Google Research、Hugging Face、NVIDIA、Mistral AI、AWS ML）與**科技媒體**（TechCrunch、The Verge、Ars Technica、WIRED、MIT Technology Review、The Decoder、MarkTechPost、iThome） | 兩類分頁切換；近 14 天、每家最多 6 則，依時間排序，可依來源篩選，標題與摘要翻成繁體中文 |
| C3 開發者雷達 | `dev-feeds.json`：GitHub Trending（今日／本週／Python）、Hacker News（首頁／最新 AI／Show HN）、arXiv（cs.AI／cs.LG／cs.CL）、Simon Willison、OpenAI 開發者社群、Reddit（r/LocalLLaMA、r/ClaudeAI、r/AI_Agents、r/MachineLearning 當日熱門）、GitHub Releases（Codex、Claude Code、LangChain、Ollama、Open WebUI） | 六個分頁；保留各來源原本的排名順序，重複連結只留一次 |
| C4 社群與活動 | GDG Taipei（community.dev 公開 API）＋社群目錄 | 左為近期活動；右為加入社群連結（Hugging Face Discord、LangChain、OpenAI 論壇、生成式 AI 年會、GDG Taipei、F2E 社團、四個 Reddit 版） |
| C1 科技副刊 | [Unwind AI 電子報 RSS](https://rss.beehiiv.com/feeds/fMHDv0Uk41.xml) | 最新 30 篇文章，標題與摘要自動翻譯成繁體中文 |

## 運作方式

兩個 GitHub Actions workflow：

**Update news**（`.github/workflows/update-news.yml`）：每小時整點、push 到 main、或 Fetch Threads 完成後執行，約 1 分鐘：

1. `scripts/fetch_news.py`：抓 Google 新聞，輸出 `site/news.json`
2. `scripts/fetch_unwind.py`：抓 Unwind AI RSS 並翻譯，輸出 `site/unwind.json`
   `scripts/fetch_events.py`：抓 GDG Taipei 近期活動，輸出 `site/events.json`（要加其他 community.dev 分會，改檔案裡的 `CHAPTERS`）
   `scripts/fetch_ai_feeds.py`：抓 RSS／Atom 並翻譯（同一網站依序抓、遇到 429 會重試），用 `ai-feeds.json` 輸出 `site/ai.json`、用 `dev-feeds.json` 輸出 `site/dev.json`
3. 取 Fetch Threads 最近一次成功的 `threads.json`，經 `scripts/sanitize_threads.py` 檢查後放進 `site/`
4. `scripts/archive.py`：把這一輪的資料疊加進 `archive/<今天>/`（同一篇只留一份，翻譯沿用），更新 `archive/index.json`，並由 github-actions[bot] commit 回 main；某來源這一輪失敗時沿用最近一次存檔
5. 把 `site/`（含 `archive/`）部署到 GitHub Pages

**Fetch Threads**（`.github/workflows/fetch-threads.yml`）：每 2 小時（半點）執行，最多 20 分鐘。`scripts/fetch_threads.mjs` 用 threads-toolkit（固定版本）逐一抓追蹤帳號的個人頁；帳號之間間隔 10–20 秒，單一帳號最多 90 秒，抓到 0 則會重試一次，每抓完一個就存檔。

**資料會疊加、永久保留**：今天的版面整天持續累積新文章，舊的不會被洗掉；過去每一天都存在 `archive/YYYY-MM-DD/`（news、threads、unwind、ai、dev、events 六個 JSON）。`site/*.json` 是每輪產生的暫存檔，不進版本庫。Unwind AI 與 Threads 兩步失敗時不影響其他部分，對應版面會顯示「暫時沒有資料」。

## 設定

- **Threads 帳號與關鍵字**：編輯 `threads-keywords.json`。目前追蹤 `dcard.tw`、`ithome`、`cool3c`、`kocpc`、`ai.lanrenbao`、`darrell_tw_`、`c.yu.an_`、`kelly_guooo`、`lazyoffice2024`、`ironv.careerlife`。`accounts` 是要追蹤的帳號（不含 @），有填就以帳號模式依互動分數排序；`keywords` 是搜尋模式（未登入時對中文關鍵字常抓不到結果）。
- **翻譯**：到 Settings → Secrets and variables → Actions 新增 `ANTHROPIC_API_KEY`。沒有設定時 Unwind AI 會顯示英文原文。翻譯結果以文章連結為鍵快取，只有新文章才會呼叫 API。
- **AI 與開發者來源**：編輯 `ai-feeds.json`、`dev-feeds.json`。每個來源有 `name`、`url`、`type`（分頁），可選 `max`（則數上限）、`days`（覆寫天數）、`translate: false`（不翻譯）、`exclude`（標題符合此正規表示式就略過，版本更新用來排除 alpha／beta／rc）與 `tz`（日期沒有時區時的時差，如 iThome 用 `8`）；檔案層級有 `days`、`maxPerSource`、`sort`（`date` 依時間或 `feed` 保留來源排名）。已是中文的標題不會送去翻譯。
- **更新頻率**：修改 workflow 裡的 `cron`（UTC 時間）。
- **首次啟用**：Settings → Pages → Source 選 **GitHub Actions**，再到 Actions 手動執行一次 "Update news"。

## 注意事項

- Threads 抓取是用瀏覽器自動化讀取公開頁面，可能被登入牆或機房 IP 限制擋下，且可能不符合 Threads 使用條款，請自行評估。
- 頭版排序沿用 Google 新聞 RSS 的順序，不是實際閱讀數。

## 資安設計

- **隔離第三方程式**：Threads 抓取會執行 threads-toolkit 與其 npm 依賴，因此放在獨立的 Fetch Threads workflow，只有 `contents: read`，拿不到部署權限、OIDC 與 secrets；它產出的 JSON 被部署前，先經過 `scripts/sanitize_threads.py` 檢查欄位、型別、長度，連結只留 `https://www.threads.com/`。
- **最小權限**：workflow 預設 `permissions: {}`；Fetch Threads 的 checkout 不保存憑證。Update news 需要 `contents: write` 才能 commit 存檔，所以只執行本 repo 的程式與官方 actions；`ANTHROPIC_API_KEY` 只給翻譯步驟。
- **前端**：所有外部內容都用 `textContent` 輸出；連結與圖片只接受 http(s)；頁面帶 Content-Security-Policy，只允許自家腳本與 Google Fonts。

## 本機測試

```bash
python3 scripts/fetch_news.py
python3 scripts/fetch_unwind.py
cd site && python3 -m http.server 8000   # 開啟 http://localhost:8000
```
