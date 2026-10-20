#!/usr/bin/env python3
"""抓社群活動，輸出 site/events.json。目前來源：GDG Taipei（community.dev 公開 API）。"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

OUT = "site/events.json"
TZ = timezone(timedelta(hours=8))
CHAPTERS = [
    # (顯示名稱, community.dev chapter id)
    ("GDG Taipei", 748),
]
API = ("https://gdg.community.dev/api/event_slim/for_chapter/{id}/?page_size=12&status=Live"
       "&include_cohosted_events=true&visible_on_parent_chapter_only=true&order=start_date"
       "&fields=title,start_date,event_type_title,cropped_picture_url,url,description_short")


def main():
    items, errors = [], []
    for name, cid in CHAPTERS:
        req = urllib.request.Request(API.format(id=cid), headers={"User-Agent": "Mozilla/5.0 (compatible; daily-paper/1.0)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                results = json.load(r).get("results", [])
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue
        for e in results:
            url, start = e.get("url") or "", e.get("start_date") or ""
            if not url.startswith("https://") or not start:
                continue
            img = e.get("cropped_picture_url") or ""
            items.append({
                "source": name,
                "title": (e.get("title") or "").strip()[:200],
                "link": url,
                "start": datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(TZ).isoformat(),
                "kind": (e.get("event_type_title") or "")[:40],
                "summary": " ".join((e.get("description_short") or "").split())[:200],
                "image": img if img.startswith("https://") else "",
            })
    if not items and errors:
        sys.exit("; ".join(errors))
    items.sort(key=lambda i: i["start"])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(TZ).isoformat(timespec="seconds"), "items": items, "errors": errors},
                  f, ensure_ascii=False, indent=1)
    print(f"寫入 {len(items)} 場活動")


if __name__ == "__main__":
    main()
