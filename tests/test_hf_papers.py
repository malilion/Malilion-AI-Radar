import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_hf_papers as hf
import archive
import build_newsletter as newsletter


def row(pid='2611.12345', title='A research paper', upvotes=12):
    return {'paper': {'id': pid, 'title': title, 'summary': 'Research summary',
                      'upvotes': upvotes, 'publishedAt': '2026-11-01T00:00:00Z'}}


class PapersTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.previous = {'items': hf.normalize([row()], 'weekly'), 'periods': {
            'weekly': {'period': '2025-W52', 'updated': '2025-12-28T00:00:00Z'}}}

    def test_iso_week_year_boundary(self):
        q = hf.period_queries(self.now)
        self.assertEqual(q['weekly'], {'week': '2026-W01'})
        self.assertEqual(q['monthly'], {'month': '2026-01'})
        self.assertEqual(q['daily'], {})
        self.assertEqual(hf.period_queries(datetime(2021, 1, 1))['weekly'], {'week': '2020-W53'})

    def test_preserves_api_rank_dedups_only_within_period(self):
        rows = [row(upvotes=1), row('2611.12346', 'Higher votes', 99), row()]
        items = hf.normalize(rows, 'daily')
        self.assertEqual([i['upvotes'] for i in items], [1, 99])
        self.assertEqual([i['rank'] for i in items], [1, 2])
        with patch.object(hf, 'fetch', return_value=[row()]):
            data = hf.collect(self.previous, self.now)
        self.assertEqual([i['type'] for i in data['items']], list(hf.PERIODS))
        self.assertFalse(data['errors'])

    def test_rejects_invalid_papers_and_limits(self):
        with self.assertRaises(ValueError):
            hf.normalize([row('../../evil')], 'daily')
        self.assertEqual(hf.normalize([], 'daily'), [])
        self.assertEqual(hf.normalize([row(upvotes=True)], 'daily')[0]['upvotes'], 0)
        self.assertEqual(len(hf.normalize([row(f'2611.{n:05d}') for n in range(40)], 'daily')), 30)

    def test_request_contract(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps([row()]).encode()
        with patch.object(hf.urllib.request, 'urlopen', return_value=response) as call:
            self.assertEqual(hf.fetch({'week': '2026-W01'}), [row()])
        url = call.call_args.args[0].full_url
        self.assertIn('week=2026-W01', url)
        self.assertIn('sort=trending', url)
        self.assertIn('limit=30', url)

    def test_partial_failure_keeps_original_period_and_freshness(self):
        with patch.object(hf, 'fetch', side_effect=[[row()], OSError('offline'), []]):
            data = hf.collect(self.previous, self.now)
        self.assertEqual(len(data['errors']), 1)
        self.assertTrue(data['periods']['weekly']['stale'])
        self.assertEqual(data['periods']['weekly']['period'], '2025-W52')
        self.assertEqual(data['periods']['weekly']['updated'], '2025-12-28T00:00:00Z')
        self.assertFalse(data['periods']['monthly']['stale'])
        self.assertEqual(sum(i['type'] == 'weekly' for i in data['items']), 1)

    def test_total_failure_is_explicit(self):
        with patch.object(hf, 'fetch', side_effect=OSError('offline')):
            data = hf.collect(self.previous, self.now)
        self.assertEqual(len(data['errors']), 3)
        self.assertEqual(data['items'], self.previous['items'])
        self.assertTrue(all(p['stale'] for p in data['periods'].values()))

    def test_archive_replaces_ranking_snapshot(self):
        new = {'items': hf.normalize([row('2611.99999')], 'daily')}
        merged = archive.merge('hf-papers', new, self.previous, 'now')
        self.assertEqual(merged, new)
        self.assertEqual(archive.count('hf-papers', merged), 1)

    def test_all_failed_cli_keeps_backup_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site/hf-papers.json'
            with patch.object(hf, 'OUT', out), patch.object(hf, 'load_previous', return_value=self.previous), \
                    patch.object(hf, 'fetch', side_effect=OSError('offline')):
                self.assertEqual(hf.main(), 1)
            data = json.loads(out.read_text())
            self.assertEqual(data['items'], self.previous['items'])
            self.assertTrue(data['periods']['weekly']['stale'])

    def test_archive_and_newsletter_pipeline(self):
        with patch.object(hf, 'fetch', return_value=[row(title='<script>Research</script>')]):
            data = hf.collect(self.previous, self.now)
        data['periods']['weekly']['stale'] = True
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                Path('site').mkdir()
                Path('archive').mkdir()
                Path('site/hf-papers.json').write_text(json.dumps(data))
                archive.main()
                index = json.loads(Path('archive/index.json').read_text())
                day = index['days'][0]['date']
                self.assertEqual(index['days'][0]['counts']['hf-papers'], 3)
                self.assertEqual(json.loads(Path(f'site/archive/{day}/hf-papers.json').read_text())['items'], data['items'])
                newsletter.main()
                html = Path(f'site/newsletter/{day}.html').read_text()
                self.assertIn('Trending Papers', html)
                self.assertIn('備援榜單', html)
                self.assertIn('&lt;script&gt;Research&lt;/script&gt;', html)
                self.assertNotIn('<script>Research</script>', html)
                self.assertTrue(Path('site/newsletter/latest.html').exists())
            finally:
                os.chdir(original)


if __name__ == '__main__':
    unittest.main()
