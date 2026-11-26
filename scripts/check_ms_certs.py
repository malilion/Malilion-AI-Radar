#!/usr/bin/env python3
"""比對 Microsoft Learn 認證目錄，找出新增或下架的 AI 相關認證。

資料來源：公開 API https://learn.microsoft.com/api/learn/catalog/?type=certifications
快照存 data/ms-ai-certs.json（uid → 名稱、網址、等級）。
有差異時：更新快照，並把 Markdown 報告寫到 --report 指定的檔案、以結束碼 0 離開；
沒差異不寫報告。第一次執行（沒有快照）只建立快照，不產生報告。"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "data" / "ms-ai-certs.json"
API = "https://learn.microsoft.com/api/learn/catalog/?type=certifications&locale=en-us"
UA = "Mozilla/5.0 (compatible; malilion-ai-radar/1.0; +https://malilion.github.io/Malilion-AI-Radar/)"
AI = re.compile(r"\bAI\b|Copilot|machine learning|generative|\bagents?\b|data scientist|OpenAI", re.I)


def fetch():
    req = urllib.request.Request(API, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read(60_000_000))


def pick(catalog):
    out = {}
    for c in catalog.get("certifications", []):
        if not AI.search(c.get("title", "")):
            continue
        out[c["uid"]] = {"title": c["title"], "url": c["url"].split("?")[0], "levels": c.get("levels", [])}
    return out


def diff(old, new):
    added = {k: v for k, v in new.items() if k not in old}
    removed = {k: v for k, v in old.items() if k not in new}
    return added, removed


def report(added, removed):
    lines = ["Microsoft Learn 的 AI 相關認證目錄有變動，請確認是否要更新 `data/certifications.json`。", ""]
    for title, items in (("新增", added), ("下架或改名", removed)):
        if items:
            lines += [f"### {title}"] + [f"- [{v['title']}]({v['url']})（{'／'.join(v['levels']) or '未標示等級'}）" for v in items.values()] + [""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="")
    args = ap.parse_args()
    new = pick(fetch())
    if len(new) < 5:  # API 異常（回傳空或改格式）時不要覆蓋快照
        sys.exit(f"只找到 {len(new)} 項 AI 認證，疑似 API 異常，略過")
    old = json.loads(SNAP.read_text(encoding="utf-8")) if SNAP.exists() else None
    SNAP.write_text(json.dumps(new, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    if old is None:
        print(f"建立快照：{len(new)} 項")
        return
    added, removed = diff(old, new)
    print(f"新增 {len(added)}、下架 {len(removed)}")
    if (added or removed) and args.report:
        Path(args.report).write_text(report(added, removed), encoding="utf-8")


if __name__ == "__main__":
    main()
