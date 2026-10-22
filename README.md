# Malilion AI Radar

每小時自動更新的新聞與 AI 情報網站：台灣要聞、Threads 社群、Codex 重置雷達、AI 業界動態、開發者雷達與社群活動，全部由 GitHub Actions 抓取、存檔並部署到 GitHub Pages。

**網站**：<https://malilion.github.io/Malilion-AI-Radar/>

## 版面

編輯感報刊設計：米白紙、墨黑、印章朱紅，固定淺色版面；標題用思源宋體、內文用思源黑體。單頁由上而下：

| 版 | 名稱 | 內容 |
|----|------|------|
| — | 報頭 | 國曆／民國／農曆日期、期號（2026/10/20 創刊為第 1 期）、最後更新時間；往下捲後收成頂部導覽列 |
| A1 | 頭版 | 頭條、兩則次要新聞、三則短訊 |
| A2 | 要聞 | 多欄新聞列表，可搜尋、依媒體篩選、只看未讀 |
| B1 | 社群版 | Threads 貼文引述卡，依互動分數排序，可依帳號篩選 |
| B2 | 重置雷達（**暫停中**） | X 目前從 GitHub Actions 抓不到資料，區塊已隱藏、抓取步驟已停用（`if: false`），程式碼保留。原設計：追蹤 Tibo（[@thsottiaux](https://x.com/thsottiaux)，OpenAI Codex 負責人）的 X 貼文，判斷 Codex 額度是不是要重置了：上方印章顯示「已重置／即將重置／未見重置訊號」，下方列出近期貼文，可只看重置訊號或談額度的貼文 |
| C1 | 科技副刊 | Unwind AI 電子報，橫向捲動封面卡 |
| C2 | AI 業界動態 | 「官方部落格／科技媒體」兩個分頁，可依來源篩選 |
| C3 | 開發者雷達 | 「GitHub 趨勢／Hacker News／論文／部落格／Reddit／版本更新」六個分頁，排行榜類標示名次 |
| C4 | 社群與活動 | 左為近期社群活動，右為加入社群連結目錄（第一張為本站 LINE 社群「碼力獅冒險公會」） |

其他功能：

- **電子報**：每期自動排好一份電子報（頭版與要聞、AI 業界、開發者雷達、Threads、Codex 重置雷達、社群活動），可「複製郵件內容」直接貼進 Gmail／Outlook／電子報平台，或下載 HTML、Markdown；網址為 `newsletter/YYYY-MM-DD.html`，`newsletter/latest.html` 為最新一期
- **往期**：每天的版面都存檔，按「往期」選日期回看，網址為 `?d=YYYY-MM-DD`
- **已讀**：點過的文章會變淡，可切換「只看未讀」
- **收藏**：按 ☆ 收藏，在收藏夾集中查看
- 已讀與收藏只存在瀏覽器（localStorage），不會上傳

鍵盤快捷鍵：`/` 搜尋、`s` 收藏夾、`p` 往期、`Esc` 關閉。

## 資料來源

| 版 | 來源 | 規則 |
|----|------|------|
| A1、A2 | [Google 新聞 RSS（台灣）](https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant) | RSS 前 6 則排進頭版，其餘進要聞 |
| B1 | Threads（透過 [threads-toolkit](https://github.com/Chuanyin1202/threads-toolkit)），帳號清單在 `threads-keywords.json` | 追蹤帳號近 72 小時的貼文，分數 = 讚 + 回覆×2 + 轉發×3 |
| B2 | X：[@thsottiaux](https://x.com/thsottiaux)，經 [TweeterPy](https://github.com/iSarabjitDhiman/TweeterPy)（`scripts/fetch_tibo_x.py`），備援為 X syndication 時間軸與自訂 RSS（`scripts/fetch_tibo.py`） | 近 14 天、最多 30 則；判斷規則見下方「重置雷達」 |
| C1 | [Unwind AI RSS](https://rss.beehiiv.com/feeds/fMHDv0Uk41.xml) | 最新 30 篇 |
| C2 | `ai-feeds.json` | 近 14 天、每家最多 6 則，依時間排序 |
| C3 | `dev-feeds.json` | 保留各來源原本的排名，重複連結只留一次 |
| C4 | GDG Taipei（community.dev 公開 API）＋ `site/index.html` 裡的社群目錄 | 只列尚未結束的活動 |

**C2 官方部落格**：OpenAI、Anthropic（新聞／研究／Claude）、Google DeepMind、Google AI、Google Research、Hugging Face、NVIDIA、Mistral AI、AWS Machine Learning
**C2 科技媒體**：TechCrunch、The Verge、Ars Technica、WIRED、MIT Technology Review、The Decoder、MarkTechPost、iThome

**C3 開發者雷達**：

| 分頁 | 來源 |
|------|------|
| GitHub 趨勢 | GitHub Trending 今日、本週、今日 Python |
| Hacker News | 首頁、最新 AI、Show HN |
| 論文 | arXiv cs.AI、cs.LG、cs.CL |
| 部落格 | Simon Willison、OpenAI 開發者社群 |
| Reddit | r/LocalLLaMA、r/ClaudeAI、r/AI_Agents、r/MachineLearning（當日熱門；四個版合併成一次請求再依版拆開） |
| 版本更新 | Codex、Claude Code、LangChain、Ollama、Open WebUI 的 GitHub Releases（只留正式版） |

**C4 社群目錄**：碼力獅冒險公會（LINE，本站社群）、Hugging Face Discord、LangChain 社群、OpenAI 開發者論壇、生成式 AI 年會、GDG Taipei、F2E 前端社群、四個 Reddit 版。

英文標題與摘要會翻成繁體中文（需設定 `ANTHROPIC_API_KEY`，見下方「設定」）；已是中文的內容、版本號不會送去翻譯。

**B2 重置雷達**的判斷規則（`scripts/fetch_tibo.py` 的 `signal()`）：

| 標記 | 條件 |
|------|------|
| 重置訊號 | 提到 reset／重置，且提到 limit、usage、quota、credits、weekly、5h 等額度字眼，或 Codex、everyone、Plus、Pro 等對象 |
| 預告重置 | 同上，但有 will、tomorrow、soon、shortly 等未來式 |
| 談額度 | 只提到額度字眼，沒提到 reset |

網站狀態：24 小時內有「重置訊號」顯示**已重置**；48 小時內有較新的「預告重置」顯示**即將重置**；否則顯示**未見重置訊號**與最近一次重置公告的時間。最近一次的重置／預告會從存檔接續記住。這只是關鍵字判斷，請以官方公告為準。

## 運作方式

### Update news（`.github/workflows/update-news.yml`）

觸發時機：每小時整點、push 到 main、Fetch Threads 完成後。約 1–2 分鐘。

0. `tibo` job：用 TweeterPy 抓 Tibo 的 X 時間軸（`scripts/fetch_tibo_x.py`），存成 artifact。它執行第三方套件，所以獨立成沒有寫入、部署權限的 job，只拿得到 `X_AUTH_TOKEN`
1. 抓資料，每支程式各自輸出一個 `site/*.json`；任何一個來源失敗都不影響其他部分：

   | 程式 | 輸出 |
   |------|------|
   | `scripts/fetch_news.py` | `news.json` |
   | `scripts/fetch_tibo.py` | `tibo.json`（含翻譯；先檢查 `tibo` job 的輸出） |
   | `scripts/fetch_unwind.py` | `unwind.json`（含翻譯） |
   | `scripts/fetch_ai_feeds.py` | `ai.json`（讀 `ai-feeds.json`） |
   | `scripts/fetch_ai_feeds.py dev-feeds.json site/dev.json cache/dev_zh.json` | `dev.json` |
   | `scripts/fetch_events.py` | `events.json` |

2. 取 Fetch Threads 最近一次成功的 `threads.json`，經 `scripts/sanitize_threads.py` 檢查後放進 `site/`
3. `scripts/archive.py` 把這一輪疊加進當天存檔，github-actions[bot] 把存檔 commit 回 main
4. `scripts/build_newsletter.py` 從存檔產生每一期電子報（`site/newsletter/`）
5. 把 `site/`（含存檔與電子報）部署到 GitHub Pages

### Fetch Threads（`.github/workflows/fetch-threads.yml`）

每 2 小時（半點）執行，最多 20 分鐘。`scripts/fetch_threads.mjs` 用 threads-toolkit（固定版本）逐一抓追蹤帳號的個人頁：

- 每個帳號在獨立子程序執行，避免 toolkit 共用請求佇列造成第二個之後抓不到
- 帳號之間間隔 10–20 秒，單一帳號最多 90 秒，抓到 0 則會重試一次

### 存檔（資料疊加、永久保留）

- **今天的版面整天累積**：舊的新聞不會被洗掉，同一篇只留一份，翻譯沿用不重複計費
- **每天一期**：存在 `archive/YYYY-MM-DD/`，有 `news`、`threads`、`tibo`、`unwind`、`ai`、`dev`、`events` 七個 JSON；`archive/index.json` 是往期目錄
- **失敗備援**：某來源這一輪失敗時，沿用最近一次的存檔，版面不會空白
- **排名標示**：GitHub、HN、Reddit 的名次只標在這一輪仍在榜上的項目
- `site/*.json` 是每輪的暫存檔，不進版本庫

> main 每小時會多一個 `Archive …` 的 bot commit。本機修改前請先 `git pull`。

## 設定

| 項目 | 怎麼改 |
|------|--------|
| 翻譯 | Settings → Secrets and variables → Actions 新增 `ANTHROPIC_API_KEY`。沒設定時顯示英文原文。翻譯結果以文章連結為鍵快取 |
| Threads 帳號 | `threads-keywords.json` 的 `accounts`（不含 @）；`hotWindowHours` 是時間範圍，`keywords` 是搜尋模式（未登入時中文關鍵字常抓不到） |
| 重置雷達來源 | 預設用 TweeterPy 的訪客模式。訪客模式被擋時，到 Settings → Secrets and variables → Actions 新增 secret `X_AUTH_TOKEN`（X 帳號 cookie 裡的 `auth_token`，請用小帳號，不要用個人主帳號），會改用登入模式並連回覆一起抓。另可在 Variables 新增 `TIBO_FEEDS`（逗號分隔的 RSS 網址，例如自架 RSSHub）當備援 |
| AI／開發者來源 | `ai-feeds.json`、`dev-feeds.json`（欄位見下表） |
| 社群活動 | `scripts/fetch_events.py` 的 `CHAPTERS`（community.dev 分會名稱與 ID） |
| 社群目錄 | `site/index.html` 的 `#community` 區塊 |
| 更新頻率 | 兩個 workflow 的 `cron`（UTC 時間） |

`ai-feeds.json`／`dev-feeds.json` 欄位：

| 層級 | 欄位 | 說明 |
|------|------|------|
| 檔案 | `days` | 只取幾天內的文章 |
| 檔案 | `maxPerSource` | 每個來源預設則數上限 |
| 檔案 | `sort` | `date` 全部依時間排序；`feed` 保留各來源原本的順序 |
| 來源 | `name`、`url` | 顯示名稱與 RSS／Atom 網址 |
| 來源 | `type` | 分頁：C2 用 `lab`、`media`；C3 用 `github`、`hn`、`papers`、`blogs`、`reddit`、`releases` |
| 來源 | `max`、`days` | 覆寫這個來源的則數上限與天數 |
| 來源 | `translate` | 設為 `false` 就不翻譯 |
| 來源 | `split` | 設為 `category` 時，把合併的 feed 依每篇的分類拆成多個來源（Reddit 用） |
| 來源 | `exclude` | 標題符合此正規表示式就略過（版本更新用來排除 alpha／beta／rc） |
| 來源 | `tz` | 日期沒有時區時的時差（小時），例如 iThome 用 `8` |

## 首次啟用

1. Settings → Pages → Source 選 **GitHub Actions**
2. （選用）新增 `ANTHROPIC_API_KEY` secret
3. Actions → **Update news** → Run workflow；再執行一次 **Fetch Threads**

## 本機測試

```bash
python3 scripts/fetch_news.py
pip install tweeterpy==2.0.17 && python3 scripts/fetch_tibo_x.py tibo-raw/posts.json   # 需要 Python 3.12 以下
python3 scripts/fetch_tibo.py
python3 scripts/fetch_unwind.py
python3 scripts/fetch_ai_feeds.py
python3 scripts/fetch_ai_feeds.py dev-feeds.json site/dev.json cache/dev_zh.json
python3 scripts/fetch_events.py
python3 scripts/archive.py        # 會寫入 archive/，測試完可用 git checkout archive 還原
cd site && python3 -m http.server 8000   # 開啟 http://localhost:8000
```

Threads 需要 Node 22 與 threads-toolkit，在本機較難重現，建議直接在 Actions 執行 Fetch Threads。

## 專案結構

```
.github/workflows/   update-news.yml、fetch-threads.yml
scripts/             抓取、翻譯、清理、存檔程式
site/                前端（index.html、styles.css、app.js）
archive/             每日存檔（由 bot 自動 commit）
ai-feeds.json        C2 來源
dev-feeds.json       C3 來源
threads-keywords.json  B1 帳號
```

## 注意事項

- X 沒有免登入的正式管道，重置雷達靠 TweeterPy 模擬網頁請求，X 改版或封鎖機房 IP 時會失效，用 `X_AUTH_TOKEN` 的帳號也可能被鎖，且可能不符合 X 使用條款，請自行評估；失敗時沿用最近一次存檔。
- Threads 抓取是用瀏覽器自動化讀取公開頁面，可能被登入牆或機房 IP 擋下，也可能不符合 Threads 使用條款，請自行評估。
- Reddit 未登入時每個 IP 的請求額度很小，所以四個版合併成一次請求；遇到 429 會依 Reddit 指示的秒數等待重試，仍可能偶爾失敗，失敗時沿用當天稍早的存檔。
- 頭版排序沿用 Google 新聞 RSS 的順序，不是實際閱讀數。
