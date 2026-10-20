#!/usr/bin/env python3
"""抓取 Unwind AI（beehiiv）RSS 並輸出成 site/unwind.json。失敗時不輸出檔案、不中斷流程。"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

FEED_URL = "https://rss.beehiiv.com/feeds/fMHDv0Uk41.xml"
OUT = "site/unwind.json"
TZ = timezone(timedelta(hours=8))
MAX_ITEMS = 30
NS = {"content": "http://purl.org/rss/1.0/modules/content/", "media": "http://search.yahoo.com/mrss/"}


def text_of(raw):
    raw = re.sub(r"<(script|style).*?</\1>", "", raw or "", flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def main():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        print(f"抓取 Unwind AI 失敗：{e}", file=sys.stderr)
        return

    items = []
    for it in root.iter("item"):
        body = it.findtext("content:encoded", namespaces=NS) or ""
        summary = text_of(it.findtext("description") or body)
        image = ""
        enc = it.find("enclosure")
        media = it.find("media:content", NS)
        if enc is not None and "image" in (enc.get("type") or "image"):
            image = enc.get("url", "")
        elif media is not None:
            image = media.get("url", "")
        else:
            m = re.search(r'<img[^>]+src="([^"]+)"', body)
            image = m.group(1) if m else ""
        pub = it.findtext("pubDate")
        try:
            pub = parsedate_to_datetime(pub).astimezone(TZ).isoformat()
        except Exception:
            pass
        items.append({
            "title": text_of(it.findtext("title")),
            "link": (it.findtext("link") or "").strip(),
            "pubDate": pub,
            "summary": summary[:220] + ("…" if len(summary) > 220 else ""),
            "image": image,
        })
    items = [i for i in items if i["title"] and i["link"]][:MAX_ITEMS]
    if not items:
        print("Unwind AI RSS 沒有項目", file=sys.stderr)
        return

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(TZ).isoformat(timespec="seconds"), "items": items}, f, ensure_ascii=False, indent=1)
    print(f"寫入 {len(items)} 則 Unwind AI")


if __name__ == "__main__":
    main()
