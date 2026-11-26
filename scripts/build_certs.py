#!/usr/bin/env python3
"""讀 data/certifications.json 與 data/schedules.json，算出每個梯次的狀態，
輸出 site/certs.json（網頁用）與 site/ai-certs.ics（行事曆訂閱）。

狀態：upcoming 即將開放、open 報名中、closing_soon 7 天內截止、closed 已截止。
每小時由 update-news workflow 執行，所以倒數天數每天都會自動更新。"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TW = timezone(timedelta(hours=8))
CLOSING_DAYS = 7
STALE_DAYS = 90  # last_verified 超過這麼久沒人確認，網頁會標示「待確認」


def d(s):
    return date.fromisoformat(s) if s else None


def status(s, today):
    start, end = d(s.get("reg_start")), d(s.get("reg_end"))
    if end and today > end:
        return "closed"
    if start and today < start:
        return "upcoming"
    if end and (end - today).days <= CLOSING_DAYS:
        return "closing_soon"
    return "open"


def enrich(sched, today):
    s = dict(sched)
    s["status"] = status(s, today)
    end = d(s.get("reg_end"))
    s["days_left"] = (end - today).days if end and s["status"] != "closed" else None
    lv = d(s.get("last_verified"))
    s["stale"] = bool(lv and (today - lv).days > STALE_DAYS)
    return s


def ics_escape(t):
    return str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_ics(certs, scheds, now):
    names = {c["cert_id"]: c["title"] for c in certs}
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Malilion AI Radar//AI Certs//ZH", "CALSCALE:GREGORIAN",
           "X-WR-CALNAME:AI 證照報名與考試", "X-WR-TIMEZONE:Asia/Taipei"]
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    for s in scheds:
        title = names.get(s["cert_id"], s["cert_id"])
        for key, label in (("reg_start", "報名開始"), ("reg_end", "報名截止"), ("exam_date", "考試／活動")):
            val = s.get(key)
            if not val:
                continue
            # exam_date 可為單日或 "YYYY-MM-DD/YYYY-MM-DD" 區間
            a, _, b = str(val).partition("/")
            start = d(a)
            end = (d(b) if b else start) + timedelta(days=1)
            out += ["BEGIN:VEVENT", f"UID:{s['schedule_id']}-{key}@malilion-ai-radar", f"DTSTAMP:{stamp}",
                    f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{end:%Y%m%d}",
                    "SUMMARY:" + ics_escape(f"【{label}】{title} {s.get('batch_name', '')}".strip()),
                    "DESCRIPTION:" + ics_escape(f"{s.get('promo_detail', '')}\n{s.get('source_url', '')}".strip()), "END:VEVENT"]
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"


def main():
    now = datetime.now(timezone.utc)
    today = now.astimezone(TW).date()
    certs = json.loads((ROOT / "data/certifications.json").read_text(encoding="utf-8"))["certifications"]
    scheds = json.loads((ROOT / "data/schedules.json").read_text(encoding="utf-8"))["schedules"]
    # 自動抓取的梯次（fetch_cert_schedules.py）；schedule_id 相同時以手動維護的為準
    auto = ROOT / "site/schedules.auto.json"
    if auto.exists():
        have = {x["schedule_id"] for x in scheds}
        try:
            scheds += [x for x in json.loads(auto.read_text(encoding="utf-8"))["schedules"] if x["schedule_id"] not in have]
        except (ValueError, KeyError) as e:
            print(f"略過自動梯次：{e}", file=sys.stderr)
    ids = {c["cert_id"] for c in certs}
    bad = [s["schedule_id"] for s in scheds if s["cert_id"] not in ids]
    if bad:
        sys.exit(f"schedules 指向不存在的 cert_id: {bad}")
    scheds = [enrich(s, today) for s in scheds]
    for c in certs:
        mine = sorted((s for s in scheds if s["cert_id"] == c["cert_id"] and s["status"] != "closed"),
                      key=lambda s: s.get("reg_end") or "9999")
        c["schedules"] = mine
        c["next"] = mine[0] if mine else None
    out = ROOT / "site"
    out.mkdir(exist_ok=True)
    (out / "certs.json").write_text(json.dumps({"updated": now.isoformat(), "items": certs}, ensure_ascii=False), encoding="utf-8")
    live = [s for s in scheds if s["status"] != "closed"]
    (out / "ai-certs.ics").write_text(build_ics(certs, live, now), encoding="utf-8")
    print(f"證照 {len(certs)} 項、進行中梯次 {len(live)} 個")


if __name__ == "__main__":
    main()
