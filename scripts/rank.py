"""不用 AI 的排序與去重：網址正規化、標題相似度去重、依權重／互動／時間衰減計分。"""
import math
import re
import urllib.parse
from datetime import datetime, timezone
from difflib import SequenceMatcher

# 這些類型的標題天生相似（版本號、repo 名），不做標題去重
NO_TITLE_DEDUP = {"releases", "github"}


def norm_link(url):
    """小寫網域、去掉 www／追蹤參數／錨點／結尾斜線，讓同一篇文章的不同網址視為相同。"""
    p = urllib.parse.urlsplit(url.strip())
    host = p.netloc.lower().removeprefix("www.")
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query)
         if not k.lower().startswith("utm_") and k.lower() not in ("ref", "ref_src", "fbclid", "gclid")]
    return urllib.parse.urlunsplit(("https", host, p.path.rstrip("/"), urllib.parse.urlencode(q), ""))


def _tokens(title):
    return re.findall(r"[0-9a-z]+|[一-鿿]", title.lower())


def similar(a, b, threshold=0.85, cjk_threshold=0.6):
    """兩個標題是否是同一件事。數字不同（版本號、期數）一律視為不同。"""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    if {t for t in ta if t.isdigit()} != {t for t in tb if t.isdigit()}:
        return False
    # 中文標題沒有空格，用字的雙連詞（bigram）比對
    ca, cb = [t for t in ta if "\u4e00" <= t <= "\u9fff"], [t for t in tb if "\u4e00" <= t <= "\u9fff"]
    if len(ca) >= 10 and len(cb) >= 10:
        ba, bb = set(zip(ca, ca[1:])), set(zip(cb, cb[1:]))
        if len(ba & bb) / len(ba | bb) >= cjk_threshold:
            return True
    sa, sb = set(ta), set(tb)
    if len(sa) >= 4 and len(sa & sb) / len(sa | sb) >= 0.75:
        return True
    return SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio() >= threshold


def strip_source(title, source=""):
    """去掉標題結尾的「 - 媒體名」（Google 新聞格式），比對時才不會被媒體名影響。"""
    suffix = " - " + source
    return title[: -len(suffix)] if source and title.endswith(suffix) else title


def dedup(items):
    """依目前順序保留第一則，丟掉後面網址相同或標題相似的。回傳 (保留清單, 丟掉的數量)。"""
    kept, links = [], set()
    for it in items:
        k = norm_link(it["link"])
        if k in links:
            continue
        check = it.get("type") not in NO_TITLE_DEDUP
        if check and any(o.get("type") not in NO_TITLE_DEDUP and similar(strip_source(it["title"], it.get("source", "")), strip_source(o["title"], o.get("source", ""))) for o in kept):
            continue
        links.add(k)
        kept.append(it)
    return kept, len(items) - len(kept)


def parse_engagement(raw):
    """hnrss.org 的描述含「Points: N」「# Comments: M」，取出來當互動訊號。"""
    pts = re.search(r"Points:\s*(\d+)", raw or "")
    com = re.search(r"Comments:\s*(\d+)", raw or "")
    return int(pts.group(1)) if pts else 0, int(com.group(1)) if com else 0


def score(item, now, half_life_h=24.0):
    """分數 = 來源權重 × (1 + log(1 + 讚 + 2×留言)) × 時間衰減（每過半衰期減半）。"""
    age_h = max((now - item["date"]).total_seconds() / 3600, 0)
    engagement = 1 + math.log1p(item.get("points", 0) + 2 * item.get("comments", 0))
    return item.get("weight", 1.0) * engagement * 0.5 ** (age_h / half_life_h)
