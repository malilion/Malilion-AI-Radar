#!/usr/bin/env python3
"""從每日存檔產生電子報，輸出到 site/newsletter/：

- YYYY-MM-DD.html        閱讀頁（含匯出工具列）
- YYYY-MM-DD.email.html  可直接貼進 Gmail／電子報平台的郵件 HTML（表格排版、行內樣式）
- YYYY-MM-DD.md          Markdown 版
- latest.html            導向最新一期
內容：頭版與要聞精選、AI 業界、開發者雷達、Threads、社群活動。
"""
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
ARCHIVE = "archive"
OUT = os.path.join("site", "newsletter")
SITE_URL = "https://malilion.github.io/Malilion-AI-Radar/"
FIRST_ISSUE = datetime(2026, 10, 20, tzinfo=TZ)

PAPER, CARD, INK, INK2, MUTED, RULE, ACCENT = "#f3eee4", "#fbf8f2", "#1b1814", "#463f36", "#6b6155", "#d6cbb8", "#c2381f"
SERIF = "Georgia,'Noto Serif TC','Songti TC','PMingLiU',serif"
SANS = "-apple-system,'Segoe UI','Noto Sans TC','PingFang TC','Microsoft JhengHei',sans-serif"
WEEK = "一二三四五六日"


def load(day, name):
    try:
        with open(os.path.join(ARCHIVE, day, f"{name}.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def esc(s):
    return html.escape(s or "", quote=True)


def safe(url):
    return url if isinstance(url, str) and url.startswith(("https://", "http://")) else ""


def when(iso):
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
    except (AttributeError, ValueError):
        return ""
    return f"{t.month}/{t.day} {t:%H:%M}"


def news_title(n):
    t, src = n.get("title", ""), n.get("source", "")
    if src and t.endswith(f" - {src}"):
        t = t[: -len(src) - 3]
    return re.sub(r"\s*[|｜]\s*[^|｜\s]{1,8}\s*$", "", t).strip()


def pick(items, type_=None, n=5, current=True):
    """取某分類的前 n 則；current 時只取這一輪仍在榜上的。"""
    out = [i for i in items if (type_ is None or i.get("type") == type_) and (not current or i.get("latest") is not False)]
    return out[:n]


def per_source(items, n):
    seen, out = {}, []
    for i in items:
        seen[i["source"]] = seen.get(i["source"], 0) + 1
        if seen[i["source"]] <= n:
            out.append(i)
    return out


def collect(day):
    """整理一期電子報的內容，回傳 [(版名, 英文, [條目])]，條目為 dict(title, link, meta, note, rank)。"""
    sections = []
    news = (load(day, "news") or {}).get("items", [])
    if news:
        rows = [dict(title=news_title(n), link=n["link"], meta=f"{n.get('source', '')} · {when(n.get('pubDate'))}") for n in news[:8]]
        sections.append(("頭版與要聞", "Headlines", rows))

    ai = (load(day, "ai") or {}).get("items", [])
    rows = []
    for t, label in (("lab", "官方"), ("media", "媒體")):
        for i in per_source(pick(ai, t, 200), 1)[:5]:  # 每家一則，避免單一來源洗版
            rows.append(dict(title=i.get("title_zh") or i["title"], link=i["link"], meta=f"{label} · {i['source']} · {when(i.get('pubDate'))}",
                             note=i.get("summary_zh") or i.get("summary") or ""))
    if rows:
        sections.append(("AI 業界動態", "Labs & Press", rows))

    dev = (load(day, "dev") or {}).get("items", [])
    rows = []
    groups = [("github", "GitHub 趨勢", 5, True), ("hn", "Hacker News", 5, True), ("reddit", "Reddit", 4, True),
              ("papers", "論文", 3, False), ("releases", "版本更新", 6, False)]
    for t, label, n, ranked in groups:
        items = pick(dev, t, 200)
        if t == "releases":
            items = per_source(items, 1)  # 每個專案只列最新一版
        elif t == "github":
            items = [i for i in items if i["source"] == "GitHub 今日趨勢"] or items
        elif t == "hn":
            items = [i for i in items if i["source"] == "Hacker News 首頁"] or items
        for k, i in enumerate(items[:n]):
            rows.append(dict(title=i.get("title_zh") or i["title"], link=i["link"], group=label,
                             meta=i["source"] + (f" · #{k + 1}" if ranked else ""),
                             note=(i.get("summary_zh") or i.get("summary") or "") if t in ("github", "papers") else ""))
    if rows:
        sections.append(("開發者雷達", "Dev Radar", rows))

    th = load(day, "threads") or {}
    posts = sorted({p["id"]: p for g in th.get("groups", []) for p in g.get("posts", [])}.values(), key=lambda p: -p.get("score", 0))
    rows = [dict(title=(p.get("content") or "").split("\n")[0][:80], link=p["url"],
                 meta=f"@{p.get('username', '')} · ♥ {p.get('stats', {}).get('likes', 0)} · 💬 {p.get('stats', {}).get('replies', 0)}")
            for p in posts[:5]]
    if rows:
        sections.append(("Threads 熱門", "On Threads", rows))

    ev = (load(day, "events") or {}).get("items", [])
    ref = datetime.fromisoformat(f"{day}T00:00:00+08:00")
    rows = []
    for e in ev:
        try:
            start = datetime.fromisoformat(e["start"]).astimezone(TZ)
        except (KeyError, ValueError):
            continue
        if start >= ref:
            rows.append(dict(title=e["title"], link=e["link"], meta=f"{start.month}/{start.day}（{WEEK[start.weekday()]}）{start:%H:%M} · {e.get('source', '')}"))
    if rows:
        sections.append(("社群活動", "Events", rows[:5]))
    return sections


def issue_of(day):
    d = datetime.fromisoformat(f"{day}T00:00:00+08:00")
    return max(1, (d - FIRST_ISSUE).days + 1), d


def email_html(day, sections):
    no, d = issue_of(day)
    date_text = f"{d.year} 年 {d.month} 月 {d.day} 日 星期{WEEK[d.weekday()]}"
    web = f"{SITE_URL}?d={day}"
    parts = [f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAPER};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background:{CARD};border:1px solid {RULE};">
<tr><td style="padding:28px 32px 18px;text-align:center;border-bottom:3px double {INK};">
<div style="font:500 12px/1.4 {SANS};letter-spacing:1px;color:{INK2};">第 {no} 期　·　{date_text}</div>
<div style="margin-top:10px;font:900 34px/1.1 {SERIF};color:{INK};">Malilion <span style="font-weight:500;font-style:italic;color:{ACCENT};">AI Radar</span></div>
<div style="margin-top:8px;font:500 13px/1.5 {SERIF};letter-spacing:2px;color:{INK2};">台灣要聞 · AI 業界 · 開發者雷達</div>
</td></tr>"""]
    for title, en, rows in sections:
        parts.append(f"""<tr><td style="padding:26px 32px 4px;">
<div style="border-top:3px solid {INK};padding-top:10px;font:900 20px/1.2 {SERIF};color:{INK};">{esc(title)} <span style="font:italic 500 13px/1 {SERIF};color:{MUTED};">{esc(en)}</span></div>
</td></tr>""")
        group = None
        for k, r in enumerate(rows):
            link = safe(r["link"])
            if not link:
                continue
            if r.get("group") and r["group"] != group:
                group = r["group"]
                parts.append(f"""<tr><td style="padding:14px 32px 0;font:700 11px/1 {SANS};letter-spacing:2px;color:{ACCENT};">{esc(group)}</td></tr>""")
            note = f"""<div style="margin-top:4px;font:400 13px/1.6 {SANS};color:{INK2};">{esc(r['note'][:140])}</div>""" if r.get("note") else ""
            size = "19px" if title == "頭版與要聞" and k == 0 else "16px"
            parts.append(f"""<tr><td style="padding:10px 32px;border-bottom:1px solid {RULE};">
<a href="{esc(link)}" style="font:700 {size}/1.5 {SERIF};color:{INK};text-decoration:none;">{esc(r['title'])}</a>{note}
<div style="margin-top:4px;font:500 12px/1.4 {SANS};color:{MUTED};">{esc(r['meta'])}</div>
</td></tr>""")
    parts.append(f"""<tr><td style="padding:24px 32px 28px;text-align:center;font:400 12px/1.7 {SANS};color:{MUTED};">
<a href="{esc(web)}" style="color:{ACCENT};font-weight:700;text-decoration:none;">在網站上閱讀完整版面 →</a><br>
Malilion AI Radar 由 GitHub Actions 每小時自動採編。
</td></tr>
</table>
</td></tr>
</table>""")
    return "\n".join(parts)


def markdown(day, sections):
    no, d = issue_of(day)
    lines = [f"# Malilion AI Radar · 第 {no} 期", "", f"{d.year} 年 {d.month} 月 {d.day} 日 星期{WEEK[d.weekday()]}", ""]
    for title, _, rows in sections:
        lines += [f"## {title}", ""]
        group = None
        for r in rows:
            if not safe(r["link"]):
                continue
            if r.get("group") and r["group"] != group:
                group = r["group"]
                lines += ["", f"**{group}**", ""]
            text = r["title"].replace("[", "［").replace("]", "］")
            lines.append(f"- [{text}]({r['link']}) — {r['meta']}")
        lines.append("")
    lines.append(f"[在網站上閱讀完整版面]({SITE_URL}?d={day})")
    return "\n".join(lines) + "\n"


def viewer(day, body, days):
    no, d = issue_of(day)
    opts = "".join(f'<option value="{x}"{" selected" if x == day else ""}>{x}</option>' for x in days)
    return f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https: data:; connect-src 'self'; base-uri 'none'; form-action 'none'">
<title>電子報 · 第 {no} 期 · Malilion AI Radar</title>
<link rel="stylesheet" href="newsletter.css">
</head>
<body data-day="{day}">
<header class="nl-bar">
  <a class="nl-back" href="../?d={day}">← 回到網站</a>
  <label class="nl-pick"><span>期數</span><select id="pick">{opts}</select></label>
  <div class="nl-actions">
    <button type="button" id="copyRich">複製郵件內容</button>
    <button type="button" id="copyHtml">複製 HTML</button>
    <a href="{day}.email.html" download="malilion-ai-radar-{day}.html">下載 HTML</a>
    <a href="{day}.md" download="malilion-ai-radar-{day}.md">下載 Markdown</a>
  </div>
  <p class="nl-hint" id="hint">「複製郵件內容」可直接貼到 Gmail、Outlook 或電子報平台的編輯器。</p>
</header>
<main id="email">
{body}
</main>
<script src="newsletter.js"></script>
</body>
</html>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    days = sorted((d for d in os.listdir(ARCHIVE) if len(d) == 10 and os.path.isdir(os.path.join(ARCHIVE, d))), reverse=True)
    for day in days:
        sections = collect(day)
        if not sections:
            continue
        body = email_html(day, sections)
        no, _ = issue_of(day)
        with open(os.path.join(OUT, f"{day}.email.html"), "w", encoding="utf-8") as f:
            f.write(f'<!doctype html>\n<html lang="zh-Hant-TW"><head><meta charset="utf-8"><title>Malilion AI Radar 第 {no} 期</title></head>'
                    f'<body style="margin:0;padding:0;background:{PAPER};">\n{body}\n</body></html>\n')
        with open(os.path.join(OUT, f"{day}.md"), "w", encoding="utf-8") as f:
            f.write(markdown(day, sections))
        with open(os.path.join(OUT, f"{day}.html"), "w", encoding="utf-8") as f:
            f.write(viewer(day, body, days))
    if days:
        with open(os.path.join(OUT, "latest.html"), "w", encoding="utf-8") as f:
            f.write(f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={days[0]}.html"><a href="{days[0]}.html">最新一期</a>\n')
    print(f"電子報：產生 {len(days)} 期")


if __name__ == "__main__":
    main()
