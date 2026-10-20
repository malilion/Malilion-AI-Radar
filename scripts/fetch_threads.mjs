// 在 threads-toolkit 目錄內執行：用它的 search action 抓各關鍵字「最新」貼文，只保留最近 24 小時，
// 輸出到 THREADS_OUT（預設 ../site/threads.json）。單一關鍵字失敗不會中斷整個流程。
import { readFileSync, writeFileSync } from 'node:fs';

import { Actor } from 'apify';
import { Dataset, Log } from 'crawlee';

import { profileAction, searchAction } from '../src/actions/index.ts';

const configPath = process.env.THREADS_CONFIG || '../threads-keywords.json';
const outPath = process.env.THREADS_OUT || '../site/threads.json';
const { keywords = [], accounts = [], maxItemsPerKeyword = 20, maxPostsPerAccount = 20, hotWindowHours = 72, chineseOnly = false } = JSON.parse(readFileSync(configPath, 'utf8'));

const log = new Log({ prefix: 'Threads' });
let current = [];
Dataset.pushData = async (item) => { current.push(item); };
Actor.createProxyConfiguration = async () => undefined;

const DAY_MS = 24 * 60 * 60 * 1000;
const isFresh = (p) => {
    const t = Date.parse(p.timestamp);
    return Number.isNaN(t) || Date.now() - t <= DAY_MS;
};
// 內文清理與過濾：Threads 搜尋結果常夾帶截斷連結與洗版垃圾貼文
const CJK = /[\u3400-\u9fff]/g;
const cleanContent = (text = '') => text
    .split('\n')
    .filter((line) => !/^\s*(https?:\/\/)?(www\.)?threads\.(com|net)\/\S*…?\s*$/i.test(line))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
const letters = (t) => t.replace(/[^\p{L}\p{N}]/gu, '');
const isSpam = (t) => letters(t).length < 6;
const hasChinese = (t) => (t.match(CJK) || []).length >= 4;
const score = (s = {}) => (s.likes || 0) + 2 * (s.replies || 0) + 3 * (s.reposts || 0);

const groups = [];
const errors = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 每抓完一組就寫檔，這樣即使被 timeout 中斷也保有已抓到的部分
function save() {
    writeFileSync(outPath, JSON.stringify({
        updated: new Date().toISOString(),
        sort: accounts.length ? 'hot' : 'latest',
        note: accounts.length
            ? `追蹤帳號近 ${hotWindowHours} 小時貼文，依互動分數（讚 + 回覆×2 + 轉發×3）排序`
            : '最近 24 小時，依發文時間新到舊',
        groups,
        errors,
    }, null, 1));
}
for (const keyword of keywords) {
    current = [];
    try {
        await searchAction({ action: 'search', keyword, filter: 'recent', maxItems: maxItemsPerKeyword }, log);
    } catch (err) {
        errors.push({ keyword, error: err instanceof Error ? err.message : String(err) });
    }
    const stat = { raw: current.length, stale: 0, spam: 0, notChinese: 0, duplicate: 0 };
    const seen = new Set();
    const posts = current
        .map((p) => ({ ...p, content: cleanContent(p.content) }))
        .filter((p) => (isFresh(p) ? true : (stat.stale++, false)))
        .filter((p) => (isSpam(p.content) ? (stat.spam++, false) : true))
        .filter((p) => (chineseOnly && !hasChinese(p.content) ? (stat.notChinese++, false) : true))
        .filter((p) => {
            const k = p.content.slice(0, 80);
            if (seen.has(k)) { stat.duplicate++; return false; }
            seen.add(k);
            return true;
        })
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
        .sort((a, b) => (Date.parse(b.timestamp) || 0) - (Date.parse(a.timestamp) || 0));
    console.log(`${keyword}: 保留 ${posts.length} 則`, JSON.stringify(stat));
    groups.push({ keyword, posts, stat });
    save();
}

// 帳號清單模式：抓各帳號個人頁的近期貼文（不需登入），依互動分數排出熱門
const HOT_MS = hotWindowHours * 60 * 60 * 1000;
// 每個帳號最多等 PER_ACCOUNT_MS，超過就跳過，避免單一帳號拖垮整輪
const PER_ACCOUNT_MS = 90000;
const RATE = { maxRetries: 1, backoffDelay: 5000, requestDelay: 1000 };
const withTimeout = (p, ms) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`逾時 ${ms / 1000} 秒`)), ms))]);

let first = true;
for (const username of accounts) {
    // Threads 對連續請求會回空頁面，所以帳號之間要間隔；抓到 0 則時等久一點再重試一次
    if (!first) await sleep(10000 + Math.random() * 10000);
    first = false;
    let raw = [];
    for (let attempt = 1; attempt <= 2 && raw.length === 0; attempt++) {
        if (attempt > 1) { console.log(`@${username}: 0 則，30 秒後重試`); await sleep(30000); }
        current = [];
        try {
            await withTimeout(profileAction({ action: 'profile', username, includePosts: true, maxItems: maxPostsPerAccount, rateLimitConfig: RATE }, log), PER_ACCOUNT_MS);
        } catch (err) {
            errors.push({ keyword: '@' + username, error: err instanceof Error ? err.message : String(err) });
        }
        raw = current.filter((p) => p.source === 'profile_posts');
    }
    const stat = { raw: raw.length, stale: 0, spam: 0, notChinese: 0, duplicate: 0 };
    const seen = new Set();
    const posts = raw
        .map((p) => ({ ...p, content: cleanContent(p.content) }))
        .filter((p) => { const t = Date.parse(p.timestamp); return Number.isNaN(t) || Date.now() - t <= HOT_MS ? true : (stat.stale++, false); })
        .filter((p) => (isSpam(p.content) ? (stat.spam++, false) : true))
        .filter((p) => { const k = p.id; if (seen.has(k)) { stat.duplicate++; return false; } seen.add(k); return true; })
        .map((p) => ({
            id: p.id,
            url: p.url,
            username: p.author?.username || username,
            displayName: p.author?.displayName || '',
            content: p.content,
            timestamp: p.timestamp || '',
            stats: p.stats || {},
            score: score(p.stats),
        }));
    console.log(`@${username}: 保留 ${posts.length} 則`, JSON.stringify(stat));
    groups.push({ keyword: '@' + username, posts, stat });
    save();
}

save();
const total = groups.reduce((n, g) => n + g.posts.length, 0);
console.log(`共 ${total} 則，${errors.length} 個失敗`);
process.exit(0);
