#!/usr/bin/env python3
"""直接抓 GitHub Trending 頁（公開頁面、不需登入），轉成 RSS 存到 cache/，給 dev-feeds.json 的
"local:cache/..." 來源使用。解析不到任何專案或抓取失敗時不寫檔，該來源會退回 fallback（第三方 RSS）。

  daily   https://github.com/trending?since=daily
  weekly  https://github.com/trending?since=weekly
  python  https://github.com/trending/python?since=daily"""
import html
import re
import sys
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cache"
UA = "Mozilla/5.0 (compatible; malilion-ai-radar/1.0; +https://malilion.github.io/Malilion-AI-Radar/)"
PAGES = {
    "daily": ("https://github.com/trending?since=daily", "GitHub 今日趨勢"),
    "weekly": ("https://github.com/trending?since=weekly", "GitHub 本週趨勢"),
    "python": ("https://github.com/trending/python?since=daily", "GitHub Python 今日"),
}


def text(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


def parse(page):
    """回傳 [{repo, url, desc, lang, stars}]，順序即榜單名次。"""
    out = []
    for art in re.findall(r"<article\b[^>]*class=\"[^\"]*Box-row[^\"]*\"[^>]*>(.*?)</article>", page, re.S):
        m = re.search(r"<h2\b[^>]*>.*?<a\b[^>]*href=\"(/[^\"/]+/[^\"/?#]+)\"", art, re.S)
        if not m:
            continue
        path = m.group(1)
        desc = re.search(r"<p\b[^>]*>(.*?)</p>", art, re.S)
        lang = re.search(r"itemprop=\"programmingLanguage\"[^>]*>(.*?)<", art, re.S)
        stars = re.search(r"([\d,]+)\s+stars?\s+(?:today|this week|this month)", text(art))
        out.append({"repo": path.strip("/"), "url": "https://github.com" + path, "desc": text(desc.group(1)) if desc else "",
                    "lang": text(lang.group(1)) if lang else "", "stars": stars.group(1) if stars else ""})
    return out


def rss(title, link, repos, now):
    esc = html.escape
    items = []
    for r in repos:
        extra = " · ".join(x for x in (r["lang"], f"★ {r['stars']}" if r["stars"] else "") if x)
        summary = (r["desc"] + (f"（{extra}）" if extra else "")).strip()
        items.append(f"<item><title>{esc(r['repo'])}</title><link>{esc(r['url'])}</link><guid>{esc(r['url'])}</guid>"
                     f"<description>{esc(summary)}</description><pubDate>{format_datetime(now)}</pubDate></item>")
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{esc(title)}</title><link>{esc(link)}</link>'
            f"<description>{esc(title)}</description><lastBuildDate>{format_datetime(now)}</lastBuildDate>{''.join(items)}</channel></rss>")


def main():
    OUT.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    ok = 0
    for key, (url, title) in PAGES.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=30) as r:
                repos = parse(r.read(5_000_000).decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            print(f"{title}: 失敗 {e}", file=sys.stderr)
            continue
        if not repos:
            print(f"{title}: 解析不到專案（頁面改版？），略過", file=sys.stderr)
            continue
        (OUT / f"gh-trending-{key}.xml").write_text(rss(title, url, repos, now), encoding="utf-8")
        print(f"{title}: {len(repos)} 個專案")
        ok += 1
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
