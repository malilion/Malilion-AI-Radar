#!/usr/bin/env python3
"""抓取 Google News 台灣 RSS 並輸出成 site/news.json"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

RSS_URL = "https://news.google.com/rss?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
OUT = "site/news.json"
TZ = timezone(timedelta(hours=8))


def main():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())

    items = []
    for it in root.iter("item"):
        pub = it.findtext("pubDate")
        try:
            pub = parsedate_to_datetime(pub).astimezone(TZ).isoformat()
        except Exception:
            pass
        src = it.find("source")
        items.append({
            "title": it.findtext("title", ""),
            "link": it.findtext("link", ""),
            "pubDate": pub,
            "source": src.text if src is not None else "",
        })
    if not items:
        sys.exit("RSS 沒有任何項目")

    data = {"updated": datetime.now(TZ).isoformat(timespec="seconds"), "items": items}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"寫入 {len(items)} 則新聞")


if __name__ == "__main__":
    main()
