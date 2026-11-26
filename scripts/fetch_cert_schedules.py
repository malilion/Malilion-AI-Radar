#!/usr/bin/env python3
"""從 iPAS 官網抓 AI 應用規劃師（初級／中級）的考試日期與報名起訖，輸出 site/schedules.auto.json。

來源（伺服器端渲染的 HTML，不需登入）：
  考試資訊 https://ipd.nat.gov.tw/ipas/certification/AIAP/exam-info
  考試報名 https://ipd.nat.gov.tw/ipas/certification/AIAP/exam-registration
解析失敗或抓不到任何梯次時不寫檔、以非 0 結束，build_certs.py 會當作沒有自動資料。
手動維護的梯次放 data/schedules.json；兩邊 schedule_id 相同時以手動為準。"""
import html
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://ipd.nat.gov.tw/ipas/certification/AIAP/"
UA = "Mozilla/5.0 (compatible; malilion-ai-radar/1.0; +https://malilion.github.io/Malilion-AI-Radar/)"
NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
LEVELS = {"初級": "basic", "中級": "mid"}


def page_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read(5_000_000).decode("utf-8", "replace")
    raw = re.sub(r"<(script|style).*?</\1>", "", raw, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", raw))
    return re.sub(r"\n\s*\n+", "\n", text)


def roc(s):
    """115/03/21 → date(2026, 3, 21)"""
    y, m, d = (int(x) for x in s.split("/"))
    return date(y + 1911, m, d)


def split_levels(text):
    """把文字依「初級／中級」切段，回傳 {basic: str, mid: str}。
    報名頁用《初級》標題；考試資訊頁用單獨一行「初級」。"""
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"《(初級|中級)》", text)] \
        or [(m.start(), m.group(1)) for m in re.finditer(r"^(初級|中級)\s*$", text, re.M)]
    out = {}
    for k, (i, name) in enumerate(marks):
        j = marks[k + 1][0] if k + 1 < len(marks) else len(text)
        out.setdefault(LEVELS[name], text[i:j])
    return out


def parse_exam_dates(text):
    res = {}
    for lv, seg in split_levels(text).items():
        res[lv] = {NUM[m.group(1)]: roc(m.group(2)) for m in re.finditer(r"第([一二三四五六])次：\s*(\d{2,3}/\d{1,2}/\d{1,2})", seg)}
    return res


def parse_registration(text):
    res = {}
    for lv, seg in split_levels(text).items():
        batches = {}
        for m in re.finditer(r"第([一二三四五六])次考試：\s*個人報名：\s*(\d{2,3}/\d{1,2}/\d{1,2})\s*~\s*(\d{2,3}/\d{1,2}/\d{1,2})(?:中午12點止)?"
                             r"(?:\s*團體報名：\s*(\d{2,3}/\d{1,2}/\d{1,2})\s*~\s*(\d{2,3}/\d{1,2}/\d{1,2}))?", seg):
            batches[NUM[m.group(1)]] = (roc(m.group(2)), roc(m.group(3)), roc(m.group(5)) if m.group(5) else None)
        res[lv] = batches
    return res


def build(exam, reg, today):
    out = []
    for lv, exams in exam.items():
        for n, ed in sorted(exams.items()):
            r = reg.get(lv, {}).get(n)
            name = "初級" if lv == "basic" else "中級"
            s = {"schedule_id": f"ipas-ai-planner-{lv}-{ed.year}-{n}", "cert_id": "ipas-ai-planner",
                 "batch_name": f"{ed.year - 1911} 年第 {n} 次{name}", "exam_date": ed.isoformat(),
                 "source_url": BASE + "exam-registration", "last_verified": today.isoformat(), "auto": True}
            if r:
                s["reg_start"], s["reg_end"] = r[0].isoformat(), r[1].isoformat()
                if r[2]:
                    s["promo_detail"] = f"團體報名（40 人以上同單位）{r[2]:%m/%d} 中午 12 點截止；報名時間皆至截止日中午 12 點"
            out.append(s)
    return out


def main():
    exam = parse_exam_dates(page_text(BASE + "exam-info"))
    reg = parse_registration(page_text(BASE + "exam-registration"))
    today = datetime.now(timezone.utc).date()
    items = build(exam, reg, today)
    if not items:
        sys.exit("iPAS：解析不到任何梯次（頁面改版？），略過")
    out = ROOT / "site" / "schedules.auto.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"schedules": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"iPAS：{len(items)} 個梯次，其中 {sum(1 for s in items if 'reg_end' in s)} 個有報名期間")


if __name__ == "__main__":
    main()
