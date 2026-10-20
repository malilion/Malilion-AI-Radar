#!/usr/bin/env python3
"""把這一輪抓到的資料疊加進當天的存檔，並準備部署用的檔案。

- archive/YYYY-MM-DD/<name>.json：當天（台灣時間）累積的資料，同一篇只留一份
- site/<name>.json：今天累積後的版本（網站首頁讀這份）
- archive/index.json：所有存檔日期與各版則數，供「往期」選單使用
- 這一輪某個來源失敗時，沿用最近一次存檔，網站不會空白
最後把 archive/ 複製到 site/archive/ 一起部署。
"""
import json
import os
import shutil
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
NAMES = ["news", "threads", "unwind", "ai", "dev"]
ARCHIVE = "archive"
SITE = "site"


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def merge_list(new, old, key, now, by_date=False):
    """new 是這一輪的結果（保留其順序與最新內容）；old 中已不在 new 的項目接在後面。
    latest 標記這一篇是否出現在這一輪，first_seen 記錄第一次抓到的時間。"""
    old_by_key = {o.get(key): o for o in old}
    out, keys = [], set()
    for n in new:
        k = n.get(key)
        if not k or k in keys:
            continue
        o = old_by_key.get(k, {})
        # 翻譯只在第一次抓到時產生，這一輪沒翻到就沿用舊的
        for f in ("title_zh", "summary_zh"):
            if f not in n and f in o:
                n[f] = o[f]
        n["first_seen"] = o.get("first_seen", now)
        n["latest"] = True
        out.append(n)
        keys.add(k)
    rest = [dict(o, latest=False) for o in old if o.get(key) and o.get(key) not in keys]
    rest.sort(key=lambda o: o.get("pubDate") or o.get("timestamp") or "", reverse=True)
    out += rest
    if by_date:
        out.sort(key=lambda o: o.get("pubDate") or "", reverse=True)
    return out


def merge(name, new, old, now):
    if not old:
        old = {}
    if name == "threads":
        old_groups = {g["keyword"]: g["posts"] for g in old.get("groups", [])}
        groups = [{"keyword": g["keyword"], "posts": merge_list(g["posts"], old_groups.pop(g["keyword"], []), "id", now)}
                  for g in new.get("groups", [])]
        # 這一輪沒抓到的帳號，保留今天稍早的結果
        groups += [{"keyword": k, "posts": [dict(p, latest=False) for p in v]} for k, v in old_groups.items()]
        return {**new, "groups": groups}
    return {**new, "items": merge_list(new.get("items", []), old.get("items", []), "link", now, by_date=(name == "ai"))}


def count(name, data):
    if not data:
        return 0
    if name == "threads":
        return sum(len(g["posts"]) for g in data.get("groups", []))
    return len(data.get("items", []))


def latest_archived(name):
    """最近一天有這個檔案的存檔（今天以前）。"""
    for d in sorted(os.listdir(ARCHIVE), reverse=True) if os.path.isdir(ARCHIVE) else []:
        data = load(os.path.join(ARCHIVE, d, f"{name}.json"))
        if data:
            return data
    return None


def main():
    now_dt = datetime.now(TZ)
    today = now_dt.strftime("%Y-%m-%d")
    now = now_dt.isoformat(timespec="seconds")
    for name in NAMES:
        site_path = os.path.join(SITE, f"{name}.json")
        day_path = os.path.join(ARCHIVE, today, f"{name}.json")
        new, old = load(site_path), load(day_path)
        if new:
            merged = merge(name, new, old, now)
        else:
            # 這一輪失敗：今天已有存檔就用它，否則沿用最近一天的
            merged = old or latest_archived(name)
            if not merged:
                print(f"{name}: 沒有資料")
                continue
            print(f"{name}: 這一輪沒有新資料，沿用存檔")
            if old is None:
                save(site_path, merged)
                continue
        save(day_path, merged)
        save(site_path, merged)
        print(f"{name}: 今天累積 {count(name, merged)} 則")

    days = []
    for d in sorted(os.listdir(ARCHIVE), reverse=True):
        if len(d) == 10 and os.path.isdir(os.path.join(ARCHIVE, d)):
            days.append({"date": d, "counts": {n: count(n, load(os.path.join(ARCHIVE, d, f"{n}.json"))) for n in NAMES}})
    save(os.path.join(ARCHIVE, "index.json"), {"updated": now, "days": days})

    target = os.path.join(SITE, ARCHIVE)
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(ARCHIVE, target)
    print(f"存檔共 {len(days)} 天")


if __name__ == "__main__":
    main()
