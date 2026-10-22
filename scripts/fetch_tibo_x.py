#!/usr/bin/env python3
"""用 TweeterPy 抓 Tibo（@thsottiaux）的 X 時間軸，輸出精簡後的貼文清單。

這支程式會執行第三方套件，所以在 update-news.yml 獨立的 job 裡跑（沒有部署權限），
輸出的 JSON 由 fetch_tibo.py 再檢查一次才使用。
預設用訪客模式；設定 X_AUTH_TOKEN（X 帳號 cookie 的 auth_token）時改用登入模式。
用法：fetch_tibo_x.py 輸出檔
"""
import json
import os
import sys

from tweeterpy import TweeterPy

USER = "thsottiaux"
TOTAL = 40


def tweet_of(result):
    if (result or {}).get("__typename") == "TweetWithVisibilityResults":
        result = result.get("tweet")
    return result or {}


def screen_name(t):
    u = (((t.get("core") or {}).get("user_results") or {}).get("result")) or {}
    return (u.get("core") or {}).get("screen_name") or (u.get("legacy") or {}).get("screen_name") or ""


def normalize(t):
    t = tweet_of(t)
    leg = t.get("legacy") or {}
    kind = "post"
    rt = tweet_of((leg.get("retweeted_status_result") or {}).get("result"))
    if rt:
        t, leg, kind = rt, rt.get("legacy") or {}, "repost"
    elif leg.get("in_reply_to_status_id_str"):
        kind = "reply"
    # 長文的全文在 note_tweet
    text = ((((t.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}).get("text")
            or leg.get("full_text") or "")
    ents = leg.get("entities") or {}
    for u in ents.get("urls") or []:
        text = text.replace(u.get("url") or "\0", u.get("expanded_url") or "")
    for u in ents.get("media") or []:
        text = text.replace(u.get("url") or "\0", "")
    return {"id": t.get("rest_id") or leg.get("id_str"), "author": screen_name(t) or USER, "text": " ".join(text.split()),
            "created_at": leg.get("created_at"), "kind": kind,
            "stats": {"likes": leg.get("favorite_count"), "replies": leg.get("reply_count"), "reposts": leg.get("retweet_count")}}


def main():
    out = sys.argv[1]
    x = TweeterPy(log_level="WARNING")
    token = os.environ.get("X_AUTH_TOKEN", "").strip()
    if token:
        x.generate_session(auth_token=token)
    res = x.get_user_tweets(USER, with_replies=bool(token), total=TOTAL)
    posts = []
    for e in res.get("data") or []:
        content = e.get("content") or {}
        # 一般貼文在 itemContent；自己串的討論串在 items 裡
        results = [content.get("itemContent")] + [(i.get("item") or {}).get("itemContent") for i in content.get("items") or []]
        for ic in results:
            r = ((ic or {}).get("tweet_results") or {}).get("result")
            if r:
                posts.append(normalize(r))
    print(f"{'登入' if token else '訪客'}模式：{len(posts)} 則")
    if not posts:
        sys.exit("沒有抓到貼文")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
