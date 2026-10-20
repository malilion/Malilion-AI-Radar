#!/usr/bin/env python3
"""檢查並清理 threads.json：它由第三方程式（threads-toolkit 及其 npm 依賴）產生，
部署前只保留預期的欄位與型別、限制長度，連結只允許 https://www.threads.com。"""
import json
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
MAX_BYTES = 5 * 1024 * 1024


def s(v, n):
    return v[:n] if isinstance(v, str) else ""


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 1e10 else 0


def url(v):
    return v if isinstance(v, str) and v.startswith("https://www.threads.com/") and len(v) < 500 else ""


def main():
    with open(SRC, "rb") as f:
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        sys.exit("threads.json 過大，略過")
    d = json.loads(raw)
    groups = []
    for g in (d.get("groups") or [])[:50]:
        posts = []
        for p in (g.get("posts") or [])[:100]:
            u = url(p.get("url"))
            if not u:
                continue
            st = p.get("stats") if isinstance(p.get("stats"), dict) else {}
            posts.append({
                "id": s(p.get("id"), 100) or u,
                "url": u,
                "username": s(p.get("username"), 60),
                "displayName": s(p.get("displayName"), 100),
                "content": s(p.get("content"), 3000),
                "timestamp": s(p.get("timestamp"), 40),
                "stats": {k: num(st.get(k)) for k in ("likes", "replies", "reposts", "shares")},
                "score": num(p.get("score")),
            })
        groups.append({"keyword": s(g.get("keyword"), 60), "posts": posts})
    out = {
        "updated": s(d.get("updated"), 40),
        "sort": "latest" if d.get("sort") == "latest" else "hot",
        "note": s(d.get("note"), 200),
        "groups": groups,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"threads.json 檢查通過：{sum(len(g['posts']) for g in groups)} 則")


if __name__ == "__main__":
    main()
