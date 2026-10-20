#!/usr/bin/env python3
"""抓取 ai-feeds.json 列出的 AI 公司部落格與科技媒體（RSS 或 Atom），合併成 site/ai.json，標題與摘要翻成繁體中文。
單一來源失敗只會略過該來源；全部失敗時不輸出檔案。"""
import gzip
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

from fetch_unwind import add_translations, text_of

# 可用參數覆寫：fetch_ai_feeds.py [設定檔] [輸出檔] [翻譯快取]
CONFIG, OUT, CACHE = (sys.argv[1:4] + ["ai-feeds.json", "site/ai.json", "cache/ai_zh.json"][len(sys.argv[1:4]):])
TZ = timezone(timedelta(hours=8))
MAX_BYTES = 10 * 1024 * 1024
ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"


def parse_date(s, naive_tz=timezone.utc):
    if not s:
        return None
    s = " ".join(s.split())
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=naive_tz)


def clean_summary(s):
    # arXiv：去掉「arXiv:xxxx Announce Type: new Abstract:」前綴
    s = re.sub(r"^arXiv:\S+\s+Announce Type:\s*\S+\s+Abstract:\s*", "", s)
    # Hacker News：摘要只有連結資訊，沒有內容
    if s == "Comments" or s.startswith("Article URL:"):
        return ""
    return s


def find_image(node, body):
    for tag in (MEDIA + "content", MEDIA + "thumbnail"):
        m = node.find(tag)
        if m is not None and m.get("url"):
            return m.get("url")
    enc = node.find("enclosure")
    if enc is not None and "image" in (enc.get("type") or ""):
        return enc.get("url", "")
    m = re.search(r'<img[^>]+src="([^"]+)"', body or "")
    return m.group(1) if m else ""


def parse(xml, source, naive_tz=timezone.utc):
    root = ET.fromstring(xml)
    pd = lambda v: parse_date(v, naive_tz)  # noqa: E731
    items = []
    if root.tag == ATOM + "feed":
        for e in root.iter(ATOM + "entry"):
            link = ""
            for l in e.findall(ATOM + "link"):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
                    break
            body = e.findtext(ATOM + "content") or ""
            items.append({
                "title": e.findtext(ATOM + "title"),
                "link": link,
                "date": pd(e.findtext(ATOM + "published") or e.findtext(ATOM + "updated")),
                "raw_summary": e.findtext(ATOM + "summary") or body,
                "image": find_image(e, body),
            })
    else:
        # 沒有逐篇日期的來源（如 GitHub Trending）沿用整個 feed 的日期
        channel_date = pd(root.findtext("channel/pubDate") or root.findtext("channel/lastBuildDate"))
        for it in root.iter("item"):
            body = it.findtext(CONTENT + "encoded") or ""
            items.append({
                "title": it.findtext("title"),
                "link": (it.findtext("link") or "").strip(),
                "date": pd(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")) or channel_date,
                "raw_summary": it.findtext("description") or body,
                "image": find_image(it, body),
            })
    out = []
    for i in items:
        title, link = text_of(i["title"]), i["link"].strip()
        if not title or not link.startswith("https://"):
            continue
        summary = clean_summary(text_of(i["raw_summary"]))
        out.append({
            "source": source,
            "title": title,
            "link": link,
            "date": i["date"],
            "summary": summary[:220] + ("…" if len(summary) > 220 else ""),
            "image": i["image"] if i["image"].startswith("https://") else "",
        })
    return out


def fetch(feed):
    req = urllib.request.Request(feed["url"], headers={
        "User-Agent": "Mozilla/5.0 (compatible; daily-paper/1.0)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("檔案過大")
        if data[:2] == b"\x1f\x8b":  # 有些伺服器不管請求一律回 gzip
            data = gzip.decompress(data)[:MAX_BYTES]
        data = data.lstrip(b"\xef\xbb\xbf \t\r\n")
        if not data.startswith(b"<"):
            raise ValueError(f"不是 XML（開頭為 {data[:16]!r}）")
        # 沒有時區的日期預設為 UTC；可用 "tz": 8 指定（如 iThome 用台灣時間）
        items = parse(data, feed["name"], timezone(timedelta(hours=feed.get("tz", 0))))
        for i in items:
            i["type"] = feed.get("type", "lab")
        print(f"{feed['name']}: {len(items)} 則")
        return items, None
    except Exception as e:
        print(f"{feed['name']}: 失敗 {e}", file=sys.stderr)
        return [], f"{feed['name']}: {e}"


def main():
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg.get("days", 14))
    per = cfg.get("maxPerSource", 6)
    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(fetch, cfg["feeds"]))

    # sort = "date"：全部依時間排序；"feed"：保留各來源原本的排名（如 GitHub Trending、HN 首頁）
    by_feed = cfg.get("sort", "date") == "feed"
    now = datetime.now(timezone.utc)
    items, errors, seen = [], [e for _, e in results if e], set()
    for feed, (got, _) in zip(cfg["feeds"], results):
        for i in got:
            i["date"] = i["date"] or now
        fresh = [i for i in got if i["date"] >= cutoff and i["link"] not in seen]
        if not by_feed:
            fresh.sort(key=lambda i: i["date"], reverse=True)
        fresh = fresh[:feed.get("max", per)]
        seen.update(i["link"] for i in fresh)
        items += fresh
    if not items:
        sys.exit("所有來源都沒有可用的文章")
    if not by_feed:
        items.sort(key=lambda i: i["date"], reverse=True)
    for i in items:
        i["pubDate"] = i.pop("date").astimezone(TZ).isoformat()

    add_translations(items, CACHE)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(TZ).isoformat(timespec="seconds"), "items": items, "errors": errors},
                  f, ensure_ascii=False, indent=1)
    print(f"寫入 {len(items)} 則到 {OUT}，{len(errors)} 個來源失敗")


if __name__ == "__main__":
    main()
