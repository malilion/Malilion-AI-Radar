// 在 threads-toolkit 目錄內執行：用它的 search action 抓各關鍵字的「熱門」貼文，
// 輸出到 THREADS_OUT（預設 ../site/threads.json）。單一關鍵字失敗不會中斷整個流程。
import { readFileSync, writeFileSync } from 'node:fs';

import { Actor } from 'apify';
import { Dataset, Log } from 'crawlee';

import { searchAction } from '../src/actions/index.ts';

const configPath = process.env.THREADS_CONFIG || '../threads-keywords.json';
const outPath = process.env.THREADS_OUT || '../site/threads.json';
const { keywords, maxItemsPerKeyword = 20 } = JSON.parse(readFileSync(configPath, 'utf8'));

const log = new Log({ prefix: 'Threads' });
let current = [];
Dataset.pushData = async (item) => { current.push(item); };
Actor.createProxyConfiguration = async () => undefined;

const score = (s = {}) => (s.likes || 0) + 2 * (s.replies || 0) + 3 * (s.reposts || 0);

const groups = [];
const errors = [];
for (const keyword of keywords) {
    current = [];
    try {
        await searchAction({ action: 'search', keyword, filter: 'top', maxItems: maxItemsPerKeyword }, log);
    } catch (err) {
        errors.push({ keyword, error: err instanceof Error ? err.message : String(err) });
    }
    const posts = current
        .map((p) => ({
            id: p.id,
            url: p.url,
            username: p.author?.username || '',
            displayName: p.author?.displayName || '',
            content: p.content || '',
            timestamp: p.timestamp || '',
            stats: p.stats || {},
            score: score(p.stats),
        }))
        .sort((a, b) => b.score - a.score);
    console.log(`${keyword}: ${posts.length} 則`);
    groups.push({ keyword, posts });
}

const total = groups.reduce((n, g) => n + g.posts.length, 0);
writeFileSync(outPath, JSON.stringify({
    updated: new Date().toISOString(),
    scoreFormula: '讚 + 回覆×2 + 轉發×3',
    groups,
    errors,
}, null, 1));
console.log(`共 ${total} 則，${errors.length} 個關鍵字失敗`);
process.exit(0);
