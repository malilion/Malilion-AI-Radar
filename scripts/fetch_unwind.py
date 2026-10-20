#!/usr/bin/env python3
"""抓取 Unwind AI（beehiiv）RSS 並輸出成 site/unwind.json。失敗時不輸出檔案、不中斷流程。"""
import html
import json
import os
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
CACHE = "cache/unwind_zh.json"  # 已翻譯的結果（以文章連結為鍵），由 Actions cache 跨次保存
MODEL = "claude-haiku-5-5"
NS = {"content": "http://purl.org/rss/1.0/modules/content/", "media": "http://search.yahoo.com/mrss/"}


def text_of(raw):
    raw = re.sub(r"<(script|style).*?</\1>", "", raw or "", flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def translate(batch):
    """把 [{title, summary}] 翻成繁體中文，回傳等長的 list；沒有金鑰或失敗時回傳 None。"""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not batch:
        return None
    prompt = (
        "把下列 JSON 陣列中每個物件的 title 和 summary 翻譯成台灣用語的繁體中文。"
        "保留產品名、公司名與人名的原文（例如 Claude、OpenAI），語氣精簡自然。"
        "只輸出一個 JSON 陣列，長度與順序必須和輸入完全相同，每個物件只含 title 與 summary。\n\n"
        + json.dumps(batch, ensure_ascii=False)
    )
    body = json.dumps({"model": MODEL, "max_tokens": 8000,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            text = json.load(r)["content"][0]["text"]
        out = json.loads(text[text.index("["): text.rindex("]") + 1])
        if len(out) != len(batch):
            raise ValueError("翻譯結果數量不符")
        return [{"title": str(o.get("title", "")), "summary": str(o.get("summary", ""))} for o in out]
    except Exception as e:
        print(f"翻譯失敗（保留原文）：{e}", file=sys.stderr)
        return None


def add_translations(items, cache_path=CACHE):
    try:
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        cache = {}
    # 已經是中文的（如 iThome）不需要翻譯
    todo = [i for i in items if i["link"] not in cache and len(re.findall(r"[\u3400-\u9fff]", i["title"])) < len(i["title"]) * 0.3]
    added = 0
    for k in range(0, len(todo), 15):  # 分批翻譯，避免單次輸出過長
        chunk = todo[k:k + 15]
        done = translate([{"title": i["title"], "summary": i["summary"]} for i in chunk])
        if done:
            for i, z in zip(chunk, done):
                cache[i["link"]] = z
            added += len(done)
    for i in items:
        z = cache.get(i["link"])
        if z:
            i["title_zh"], i["summary_zh"] = z["title"], z["summary"]
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({i["link"]: cache[i["link"]] for i in items if i["link"] in cache}, f, ensure_ascii=False)
    print(f"翻譯：新增 {added} 則，共 {sum('title_zh' in i for i in items)} 則有中文")


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
    for i in items:
        if not i["image"].startswith("https://"):
            i["image"] = ""
    items = [i for i in items if i["title"] and i["link"].startswith("https://")][:MAX_ITEMS]
    if not items:
        print("Unwind AI RSS 沒有項目", file=sys.stderr)
        return

    add_translations(items)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(TZ).isoformat(timespec="seconds"), "items": items}, f, ensure_ascii=False, indent=1)
    print(f"寫入 {len(items)} 則 Unwind AI")


if __name__ == "__main__":
    main()
