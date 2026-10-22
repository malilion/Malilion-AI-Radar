#!/usr/bin/env python3
"""追蹤 Tibo（@thsottiaux，OpenAI Codex 負責人）在 X 的貼文，判斷 Codex 用量額度是不是要重置了，輸出 site/tibo.json。

來源依序如下，抓到的合併（同一則只留一份）：
- tibo-raw/posts.json：獨立 job 用 TweeterPy 抓的時間軸（scripts/fetch_tibo_x.py），這裡只取檢查過的欄位
- X 官方嵌入用的 syndication 時間軸（從 GitHub Actions 常被 429 擋下）
- 環境變數 TIBO_FEEDS 以逗號分隔的 RSS（例如自架的 RSSHub）
全部失敗時不輸出檔案，由 archive.py 沿用存檔。

每則貼文標記 signal：
- reset：提到 reset 且提到額度／用量／Codex／everyone 等（已重置）
- soon：同上，但語氣是未來式（will、tomorrow、soon…）
- limits：只提到額度／用量，沒提到 reset
last_reset、last_soon 會從之前的存檔接續，貼文被擠出時間軸後仍記得最近一次重置。
"""
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from fetch_unwind import add_translations, text_of

USER = "thsottiaux"
OUT = "site/tibo.json"
CACHE = "cache/tibo_zh.json"
ARCHIVE = "archive"
TZ = timezone(timedelta(hours=8))
MAX_ITEMS = 30
DAYS = 14
MAX_BYTES = 5 * 1024 * 1024
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SYNDICATION = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{USER}"
RAW = "tibo-raw/posts.json"

RESET = re.compile(r"\breset(?:s|ting)?\b|\brefresh(?:ed)?\b|重置|重設", re.I)
LIMITS = re.compile(r"\b(?:rate[- ]?limits?|usage|limits?|quotas?|credits?|weekly|5[- ]?h(?:ours?)?)\b|額度|用量", re.I)
# 「reset Codex for everyone」這類沒寫到 limit 的也算
SCOPE = re.compile(r"\b(?:codex|everyone|all users|plus|pro|business|enterprise)\b", re.I)
FUTURE = re.compile(r"\b(?:will|going to|gonna|tomorrow|tonight|soon|shortly|later today|about to|plan(?:ning)? to|in the next|upcoming|next week)\b", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.5"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("檔案過大")
    return data


def post(pid, author, text, date, kind, stats=None):
    return {"id": pid, "author": author, "link": f"https://x.com/{author}/status/{pid}", "text": text[:1000],
            "date": date, "kind": kind, "stats": stats or {}}


def from_raw():
    """讀 fetch_tibo_x.py 的輸出。它來自第三方套件，每個欄位都重新檢查型別與格式。"""
    with open(RAW, "rb") as f:
        data = f.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("檔案過大")
    num = lambda v: v if isinstance(v, int) and not isinstance(v, bool) and 0 <= v < 1e10 else 0  # noqa: E731
    out = []
    for p in json.loads(data)[:200]:
        pid, author, text = str(p.get("id") or ""), p.get("author"), p.get("text")
        if not pid.isdigit() or not isinstance(author, str) or not re.fullmatch(r"\w{1,15}", author) or not isinstance(text, str):
            continue
        try:
            date = datetime.strptime(p.get("created_at") or "", "%a %b %d %H:%M:%S %z %Y")
        except (TypeError, ValueError):
            continue
        kind = p.get("kind") if p.get("kind") in ("post", "repost", "reply") else "post"
        stats = p.get("stats") if isinstance(p.get("stats"), dict) else {}
        out.append(post(pid, author, " ".join(text.split()), date, kind, {k: num(stats.get(k)) for k in ("likes", "replies", "reposts")}))
    return out


def from_syndication():
    page = get(SYNDICATION).decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page, re.S)
    if not m:
        raise ValueError("找不到時間軸資料")
    entries = json.loads(m.group(1))["props"]["pageProps"]["timeline"]["entries"]
    out = []
    for e in entries:
        t = (e.get("content") or {}).get("tweet") or {}
        kind = "post"
        if t.get("retweeted_status"):
            t, kind = t["retweeted_status"], "repost"
        pid, author = str(t.get("id_str") or ""), ((t.get("user") or {}).get("screen_name") or USER)
        if not pid.isdigit() or not re.fullmatch(r"\w{1,15}", author):
            continue
        if t.get("in_reply_to_status_id_str"):
            kind = "reply"
        text = t.get("full_text") or t.get("text") or ""
        ents = t.get("entities") or {}
        for u in ents.get("urls") or []:
            text = text.replace(u.get("url", "\0"), u.get("expanded_url") or "")
        for u in ents.get("media") or []:
            text = text.replace(u.get("url", "\0"), "")
        try:
            date = datetime.strptime(t.get("created_at", ""), "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            continue
        stats = {"likes": t.get("favorite_count") or 0, "replies": t.get("reply_count") or 0, "reposts": t.get("retweet_count") or 0}
        out.append(post(pid, author, " ".join(text.split()), date, kind, stats))
    return out


def from_rss(url):
    root = ET.fromstring(get(url).lstrip(b"\xef\xbb\xbf \t\r\n"))
    out = []
    for it in root.iter("item"):
        m = re.search(r"/(\w{1,15})/status/(\d+)", it.findtext("link") or "")
        if not m:
            continue
        title = text_of(it.findtext("title"))
        kind = "repost" if title.startswith("RT by") else "reply" if title.startswith("R to") else "post"
        text = text_of(it.findtext("description")) or re.sub(r"^(RT by @\w+|R to @\w+):\s*", "", title)
        try:
            date = parsedate_to_datetime(it.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        out.append(post(m.group(2), m.group(1), text, date, kind))
    return out


def signal(text):
    if RESET.search(text) and (LIMITS.search(text) or SCOPE.search(text)):
        return "soon" if FUTURE.search(text) else "reset"
    return "limits" if LIMITS.search(text) else ""


def previous(field):
    """最近一份存檔裡的 last_reset／last_soon。"""
    for d in sorted(os.listdir(ARCHIVE), reverse=True) if os.path.isdir(ARCHIVE) else []:
        try:
            with open(os.path.join(ARCHIVE, d, "tibo.json"), encoding="utf-8") as f:
                v = json.load(f).get(field)
        except (OSError, ValueError):
            continue
        if v:
            return v
    return None


def main():
    sources = [("TweeterPy", from_raw)] if os.path.exists(RAW) else []
    sources += [("X syndication", from_syndication)]
    sources += [(u.strip(), lambda u=u.strip(): from_rss(u)) for u in os.environ.get("TIBO_FEEDS", "").split(",") if u.strip()]
    posts, errors, ok = {}, [], []
    for name, fn in sources:
        try:
            got = fn()
        except Exception as e:
            print(f"{name}: 失敗 {e}", file=sys.stderr)
            errors.append(f"{name}: {e}")
            continue
        print(f"{name}: {len(got)} 則")
        if got:
            ok.append(name)
        for p in got:
            posts.setdefault(p["id"], p)
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
    items = sorted((p for p in posts.values() if p["date"] >= cutoff), key=lambda p: p["date"], reverse=True)[:MAX_ITEMS]
    if not items:
        sys.exit("所有來源都沒有抓到貼文：" + "; ".join(errors))

    marks = {}
    for p in items:
        p["pubDate"] = p.pop("date").astimezone(TZ).isoformat()
        p["signal"] = signal(p["text"])
        # 給翻譯共用的欄位：title 是貼文全文
        p["title"], p["summary"] = p["text"], ""
        if p["signal"] in ("reset", "soon"):
            k = "last_" + p["signal"]
            if k not in marks:
                marks[k] = {f: p[f] for f in ("link", "text", "pubDate")}
    for k in ("last_reset", "last_soon"):
        old = previous(k)
        if old and (k not in marks or old["pubDate"] > marks[k]["pubDate"]):
            marks[k] = old

    add_translations(items, CACHE)
    for p in items:
        p.pop("title")
        p.pop("summary")
        if "title_zh" in p:
            p["text_zh"] = p.pop("title_zh")
            p.pop("summary_zh", None)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(TZ).isoformat(timespec="seconds"), "user": USER, "sources": ok,
                   **marks, "items": items, "errors": errors}, f, ensure_ascii=False, indent=1)
    print(f"寫入 {len(items)} 則，重置訊號 {sum(p['signal'] in ('reset', 'soon') for p in items)} 則")


if __name__ == "__main__":
    main()
