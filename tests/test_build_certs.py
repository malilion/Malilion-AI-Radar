import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_certs as b  # noqa: E402

T = date(2026, 12, 1)


def test_status():
    s = lambda a, z: {"reg_start": a, "reg_end": z}
    assert b.status(s("2026-12-10", "2026-12-20"), T) == "upcoming"
    assert b.status(s("2026-11-20", "2026-12-20"), T) == "open"
    assert b.status(s("2026-11-20", "2026-12-05"), T) == "closing_soon"
    assert b.status(s("2026-11-01", "2026-11-30"), T) == "closed"
    assert b.status(s("2026-11-01", "2026-12-01"), T) == "closing_soon"


def test_ics_range_and_escape():
    certs = [{"cert_id": "x", "title": "A,B"}]
    sc = [{"schedule_id": "x1", "cert_id": "x", "batch_name": "n", "exam_date": "2026-12-05/2026-12-06", "source_url": "https://e"}]
    from datetime import datetime, timezone
    ics = b.build_ics(certs, sc, datetime(2026, 12, 1, tzinfo=timezone.utc))
    assert "DTSTART;VALUE=DATE:20261205" in ics and "DTEND;VALUE=DATE:20261207" in ics
    assert "A\\,B" in ics


def test_data_consistent():
    import json
    root = Path(b.ROOT)
    certs = json.loads((root / "data/certifications.json").read_text(encoding="utf-8"))["certifications"]
    ids = [c["cert_id"] for c in certs]
    assert len(ids) == len(set(ids))
    for c in certs:
        assert c["schedule_type"] in {"fixed_batch", "on_demand", "campaign"}
        assert c["cost_type"] in {"free", "freemium", "paid", "voucher_available"}
        assert c["official_url"].startswith("https://")


def test_ipas_parse():
    import fetch_cert_schedules as f
    exam = f.parse_exam_dates("初級\n考試\n考試日期\n第一次：115/03/21(六)\n第二次：115/05/16(六)\n中級\n考試\n考試日期\n第一次：115/05/23(六)\n")
    assert exam["basic"][2] == date(2026, 5, 16) and exam["mid"][1] == date(2026, 5, 23)
    reg = f.parse_registration("《初級》\n第一次考試：\n個人報名：115/01/01~115/02/10中午12點止\n團體報名：115/01/01~115/02/09中午12點止\n《中級》\n第一次考試：\n個人報名：115/01/01~115/04/10中午12點止\n")
    assert reg["basic"][1] == (date(2026, 1, 1), date(2026, 2, 10), date(2026, 2, 9))
    assert reg["mid"][1][2] is None
    out = f.build(exam, reg, date(2026, 1, 1))
    assert out[0]["reg_end"] == "2026-02-10" and out[0]["exam_date"] == "2026-03-21"


def test_ms_diff_and_report():
    import check_ms_certs as m
    cat = {"certifications": [
        {"uid": "a", "title": "Azure AI Fundamentals", "url": "https://x/a?WT=1", "levels": ["beginner"]},
        {"uid": "b", "title": "Azure Storage Admin", "url": "https://x/b", "levels": []}]}
    got = m.pick(cat)
    assert list(got) == ["a"] and got["a"]["url"] == "https://x/a"
    added, removed = m.diff({"z": {"title": "Old AI", "url": "https://x/z", "levels": []}}, got)
    assert list(added) == ["a"] and list(removed) == ["z"]
    assert "Azure AI Fundamentals" in m.report(added, removed)


def test_newsletter_cert_rows():
    import build_newsletter as n
    certs = [
        {"title": "A", "issuer": "I", "official_url": "https://a", "category": ["台灣官方"], "schedule_type": "fixed_batch", "cost_type": "paid",
         "next": {"status": "closing_soon", "batch_name": "b", "days_left": 3, "reg_end": "2026-12-04", "exam_date": "2026-12-20"}},
        {"title": "B", "issuer": "I", "official_url": "https://b", "category": [], "schedule_type": "on_demand", "cost_type": "free", "next": None, "regular_price": "Free"},
        {"title": "C", "issuer": "I", "official_url": "https://c", "category": ["台灣官方"], "schedule_type": "on_demand", "cost_type": "free", "next": None, "regular_price": "Free"},
        {"title": "D", "issuer": "I", "official_url": "https://d", "category": [], "schedule_type": "fixed_batch", "cost_type": "paid", "next": None},
    ]
    rows = n.cert_rows(certs, n=3)
    assert [r["title"] for r in rows] == ["A", "C", "B"]  # 梯次優先，其後台灣官方的常駐課程，D 是付費固定梯次不列
    assert "剩 3 天" in rows[0]["meta"] and rows[1]["group"] == "隨時可學"


GH_PAGE = """<div><article class="Box-row"><h2 class="h3 lh-condensed"><a href="/owner/repo-a" data-view-component="true">
  <span class="text-normal">owner /</span> repo-a</a></h2>
<p class="col-9 color-fg-muted my-1 pr-4">Does &amp; things</p>
<div><span itemprop="programmingLanguage">Python</span><span class="d-inline-block float-sm-right">1,234 stars today</span></div></article>
<article class="Box-row"><h2 class="h3"><a href="/o2/b">o2 / b</a></h2><span>56 stars today</span></article></div>"""


def test_github_trending_parse_and_rss():
    import fetch_github_trending as g
    from datetime import datetime, timezone
    repos = g.parse(GH_PAGE)
    assert [r["repo"] for r in repos] == ["owner/repo-a", "o2/b"]
    assert repos[0]["desc"] == "Does & things" and repos[0]["lang"] == "Python" and repos[0]["stars"] == "1,234" and repos[1]["desc"] == ""
    xml = g.rss("T", "https://github.com/trending", repos, datetime(2026, 11, 26, tzinfo=timezone.utc))
    import fetch_ai_feeds as f
    items = f.parse(xml.encode(), "S")
    assert [i["title"] for i in items] == ["owner/repo-a", "o2/b"] and items[0]["link"] == "https://github.com/owner/repo-a"


def test_local_feed_and_fallback(tmp_path, monkeypatch):
    import fetch_github_trending as g
    import fetch_ai_feeds as f
    from datetime import datetime, timezone
    monkeypatch.chdir(tmp_path)
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache/x.xml").write_text(g.rss("T", "https://github.com", g.parse(GH_PAGE), datetime.now(timezone.utc)), encoding="utf-8")
    items, err = f.fetch({"name": "t", "url": "local:cache/x.xml", "type": "github"})
    assert len(items) == 2 and err is None
    # 本機檔不存在 → 走 fallback（這裡用另一個存在的本機檔代替網路來源）
    items, err = f.fetch({"name": "t", "url": "local:cache/missing.xml", "fallback": "local:cache/x.xml", "type": "github"})
    assert len(items) == 2 and err is None
    items, err = f.fetch({"name": "t", "url": "local:cache/missing.xml", "type": "github"})
    assert items == [] and err
