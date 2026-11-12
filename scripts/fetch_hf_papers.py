#!/usr/bin/env python3
"""Hugging Face Papers 日／週／月 trending 榜；只用標準函式庫。"""
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OUT = Path('site/hf-papers.json')
PERIODS = ('daily', 'weekly', 'monthly')
MAX_BYTES = 8 * 1024 * 1024


def period_queries(now):
    # HF 的日榜預設為最近有投稿的一日，週／月使用 UTC 日曆。
    return {'daily': {}, 'weekly': {'week': now.strftime('%G-W%V')},
            'monthly': {'month': now.strftime('%Y-%m')}}


def fetch(params):
    url = 'https://huggingface.co/api/daily_papers?' + urllib.parse.urlencode(
        dict(params, sort='trending', limit=30))
    req = urllib.request.Request(url, headers={'User-Agent': 'Malilion-AI-Radar/1.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('回應過大')
    rows = json.loads(raw)
    if not isinstance(rows, list):
        raise ValueError('預期為論文陣列')
    return rows


def normalize(rows, period):
    items, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('paper'), dict):
            continue
        paper = row['paper']
        pid, title = paper.get('id'), row.get('title') or paper.get('title')
        if not isinstance(pid, str) or not re.fullmatch(r'\d{4}\.\d{4,5}(?:v\d+)?', pid):
            continue
        if pid in seen or not isinstance(title, str) or not title.strip():
            continue
        seen.add(pid)
        votes = paper.get('upvotes', 0)
        items.append({'id': pid, 'title': title[:500], 'link': f'https://huggingface.co/papers/{pid}',
                      'summary': str(paper.get('summary') or '')[:1600],
                      'pubDate': paper.get('publishedAt') or row.get('publishedAt') or '',
                      'source': 'Hugging Face', 'type': period, 'rank': len(items) + 1,
                      'upvotes': votes if type(votes) is int and votes >= 0 else 0})
        if len(items) == 30:
            break
    if rows and not items:
        raise ValueError('沒有符合預期格式的論文')
    return items


def load_previous():
    # 本機／CI 每次重新 checkout 時，仍可從最近的永久存檔恢復。
    candidates = [OUT, *sorted(Path('archive').glob('*/hf-papers.json'), reverse=True)]
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, dict) and isinstance(data.get('items'), list) and isinstance(data.get('periods'), dict):
                return data
        except (OSError, ValueError):
            pass
    return {'items': [], 'periods': {}}


def collect(previous, now):
    stamp = now.isoformat(timespec='seconds')
    items, periods, errors = [], {}, []
    for period, params in period_queries(now).items():
        key = next(iter(params.values()), 'latest')
        source = 'https://huggingface.co/papers' + (
            '/week/' + params['week'] if 'week' in params else
            '/month/' + params['month'] if 'month' in params else '')
        try:
            got = normalize(fetch(params), period)
            periods[period] = {'period': key, 'updated': stamp, 'stale': False, 'sourceUrl': source}
            items.extend(got)
            print(f'HF {period}: {len(got)} 篇')
        except Exception as exc:
            error = f'{period}: {exc}'
            errors.append(error)
            print(error, file=sys.stderr)
            periods[period] = {**previous.get('periods', {}).get(period, {}), 'stale': True, 'error': error}
            items.extend(i for i in previous.get('items', []) if i.get('type') == period)
    return {'updated': stamp, 'items': items, 'periods': periods, 'errors': errors}


def main():
    data = collect(load_previous(), datetime.now(timezone.utc))
    # 即使三榜全失敗，也輸出明確的失敗狀態與可用備援；用非零狀態通知 CI。
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    temp.replace(OUT)
    return 1 if len(data['errors']) == len(PERIODS) else 0


if __name__ == '__main__':
    sys.exit(main())
