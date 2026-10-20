// 每日晨報 — 前端
(() => {
  'use strict';

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const TZ = 'Asia/Taipei';
  const FIRST_ISSUE = Date.UTC(2026, 9, 20); // 創刊日 2026-10-20（台灣時間）
  const pad = (n) => String(n).padStart(2, '0');
  // 資料來自外部來源，連結與圖片只接受 http(s)，避免 javascript: 等協定
  const safeUrl = (u) => {
    try {
      const x = new URL(u, location.href);
      return x.protocol === 'https:' || x.protocol === 'http:' ? x.href : '';
    } catch { return ''; }
  };

  // ---------- 本機儲存（已讀、收藏）：失敗時退回記憶體 ----------
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* 隱私模式 */ } },
  };
  const read = new Set(store.get('mr:read', []));
  let saved = store.get('mr:saved', []); // [{id, kind, title, link, src, date}]
  if (!Array.isArray(saved)) saved = [];
  const isSaved = (id) => saved.some((s) => s.id === id);
  const markRead = (id) => {
    if (read.has(id)) return;
    read.add(id);
    store.set('mr:read', [...read].slice(-800));
  };

  // ---------- 工具 ----------
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const svg = (paths) => {
    const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    s.setAttribute('viewBox', '0 0 24 24');
    s.setAttribute('aria-hidden', 'true');
    s.innerHTML = paths;
    return s;
  };
  const STAR = '<path d="M12 3.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z" stroke-linejoin="round"/>';

  function ago(iso) {
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return '';
    const m = Math.round((Date.now() - t) / 60000);
    if (m < 1) return '剛剛';
    if (m < 60) return `${m} 分鐘前`;
    if (m < 1440) return `${Math.floor(m / 60)} 小時前`;
    if (m < 10080) return `${Math.floor(m / 1440)} 天前`;
    return new Intl.DateTimeFormat('zh-TW', { timeZone: TZ, month: 'numeric', day: 'numeric' }).format(t);
  }
  const clock = (iso) => {
    const t = Date.parse(iso);
    return Number.isNaN(t) ? '' : new Intl.DateTimeFormat('zh-TW', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false }).format(t);
  };
  const compact = (n) => (n >= 10000 ? `${(n / 10000).toFixed(n >= 100000 ? 0 : 1)}萬` : String(n || 0));

  async function getJSON(url) {
    try {
      const r = await fetch(url, { cache: 'no-cache' });
      return r.ok ? await r.json() : null;
    } catch { return null; }
  }

  let toastTimer;
  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg;
    t.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('is-on'), 1800);
  }

  // ---------- 報頭日期 ----------
  const CN = '〇一二三四五六七八九';
  const cnDigits = (n) => String(n).split('').map((d) => CN[d]).join('');
  function lunarDay(d) {
    if (d === 10) return '初十';
    if (d === 20) return '二十';
    if (d === 30) return '三十';
    const tens = ['初', '十', '廿', '三十'][Math.floor(d / 10)];
    return tens + '一二三四五六七八九'[(d % 10) - 1];
  }
  function dateline() {
    const now = new Date();
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: TZ, year: 'numeric', month: 'numeric', day: 'numeric' })
      .formatToParts(now).map((p) => [p.type, +p.value]));
    const week = new Intl.DateTimeFormat('zh-TW', { timeZone: TZ, weekday: 'long' }).format(now);
    let lunar = '';
    try {
      const lp = new Intl.DateTimeFormat('zh-TW-u-ca-chinese', { timeZone: TZ, month: 'long', day: 'numeric' }).formatToParts(now);
      const month = lp.find((p) => p.type === 'month')?.value || '';
      const day = +(lp.find((p) => p.type === 'day')?.value || 0);
      if (month && day) lunar = `　農曆${month}${lunarDay(day)}`;
    } catch { /* 不支援農曆時略過 */ }
    $('#dateline').textContent = `${parts.year} 年 ${parts.month} 月 ${parts.day} 日　${week}　民國${cnDigits(parts.year - 1911)}年${lunar}`;
    const issue = Math.max(1, Math.floor((Date.UTC(parts.year, parts.month - 1, parts.day) - FIRST_ISSUE) / 864e5) + 1);
    $('#issue').textContent = `第 ${issue.toLocaleString('zh-TW')} 期`;
  }

  // ---------- 收藏 ----------
  function starButton(entry) {
    const b = el('button', 'star');
    b.type = 'button';
    b.append(svg(STAR));
    const sync = () => {
      const on = isSaved(entry.id);
      b.setAttribute('aria-pressed', String(on));
      b.setAttribute('aria-label', on ? `取消收藏：${entry.title}` : `收藏：${entry.title}`);
    };
    sync();
    b.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (isSaved(entry.id)) {
        saved = saved.filter((s) => s.id !== entry.id);
        toast('已取消收藏');
      } else {
        saved.unshift(entry);
        toast('已加入收藏');
        b.classList.remove('pop');
        void b.offsetWidth;
        b.classList.add('pop');
      }
      store.set('mr:saved', saved);
      updateSaved();
    });
    b._sync = sync;
    return b;
  }
  function updateSaved() {
    $$('[data-saved-count]').forEach((n) => { n.textContent = saved.length; });
    $$('.star').forEach((b) => b._sync && b._sync());
    if ($('#saved').open) renderSaved();
  }
  function renderSaved() {
    const list = $('#savedList');
    list.textContent = '';
    saved.forEach((s, i) => list.append(newsRow(s, String(i + 1).padStart(2, '0'))));
    $('#savedEmpty').hidden = saved.length > 0;
  }

  // 連結共用：點擊後標記已讀
  function articleLink(entry, child) {
    const a = el('a');
    const href = safeUrl(entry.link);
    if (href) a.href = href;
    a.target = '_blank';
    a.rel = 'noopener';
    a.append(...child);
    a.addEventListener('click', () => {
      markRead(entry.id);
      a.closest('.item')?.classList.add('is-read');
    });
    return a;
  }
  function metaLine(src, date) {
    const m = el('div', 'meta');
    if (src) m.append(el('span', 'src', src));
    if (src && date) m.append(el('span', 'dot'));
    if (date) {
      const t = el('time', null, ago(date));
      t.dateTime = date;
      m.append(t);
    }
    return m;
  }

  // ---------- 新聞 ----------
  let news = [];
  const FRONT = 6; // 頭版放前 6 則：頭條、兩則次要、三則短訊
  const newsEntry = (n) => ({ id: n.link, kind: 'news', title: n.title, link: n.link, src: n.source, date: n.pubDate });

  function newsRow(entry, no) {
    const li = el('li', 'item');
    if (read.has(entry.id)) li.classList.add('is-read');
    const row = el('div', 'row');
    const h = el('h3', 't');
    h.append(el('span', 'hl', entry.title));
    row.append(el('span', 'num', no), articleLink(entry, [h, metaLine(entry.src, entry.date)]), starButton(entry));
    li.append(row);
    return li;
  }

  function renderFront() {
    const grid = $('#frontGrid');
    grid.textContent = '';
    if (!news.length) {
      grid.append(el('p', 'empty', '新聞暫時無法載入，請稍後再試。'));
      return;
    }
    const [a, ...rest] = news.slice(0, 3).map(newsEntry);
    const briefs = el('ol', 'briefs');
    news.slice(3, FRONT).map(newsEntry).forEach((e, i) => {
      const li = el('li', 'item');
      if (read.has(e.id)) li.classList.add('is-read');
      const h = el('h3', 't');
      h.append(el('span', 'hl', e.title));
      li.append(articleLink(e, [el('span', 'num', pad(i + 4)), h, metaLine(e.src, e.date)]));
      briefs.append(li);
    });
    const lead = el('article', 'lead item reveal');
    if (read.has(a.id)) lead.classList.add('is-read');
    const h = el('h3', 'lead__title');
    h.append(el('span', 'hl', a.title));
    const row = el('div', 'lead__row');
    row.append(metaLine(a.src, a.date), starButton(a));
    lead.append(articleLink(a, [el('span', 'lead__no', '01'), h]), row, briefs);

    const side = el('div', 'second');
    rest.forEach((e, i) => {
      const art = el('article', 'item reveal');
      art.style.setProperty('--d', `${0.12 * (i + 1)}s`);
      if (read.has(e.id)) art.classList.add('is-read');
      const t = el('h3', 'second__title');
      t.append(el('span', 'hl', e.title));
      const r = el('div', 'lead__row');
      r.append(metaLine(e.src, e.date), starButton(e));
      art.append(articleLink(e, [el('span', 'second__no', pad(i + 2)), t]), r);
      side.append(art);
    });
    grid.append(lead, side);
    observe(grid);
  }

  function renderNews() {
    const q = $('#q').value.trim().toLowerCase();
    const src = $('#src').value;
    const unread = $('#unreadOnly').getAttribute('aria-pressed') === 'true';
    const filtering = q || src || unread;
    // 未篩選時，前三則已在頭版，不重複
    const pool = news.map((n, i) => ({ n, i })).slice(filtering ? 0 : FRONT);
    const shown = pool.filter(({ n }) => (!src || n.source === src)
      && (!q || n.title.toLowerCase().includes(q))
      && (!unread || !read.has(n.link)));
    const list = $('#newsList');
    list.textContent = '';
    const frag = document.createDocumentFragment();
    shown.forEach(({ n, i }, k) => {
      const li = newsRow(newsEntry(n), pad(i + 1));
      li.classList.add('reveal');
      li.style.setProperty('--d', `${Math.min(k, 12) * 0.03}s`);
      frag.append(li);
    });
    list.append(frag);
    $('#newsCount').textContent = filtering ? `符合 ${shown.length} 則` : `共 ${news.length} 則，頭版之外 ${shown.length} 則`;
    $('#newsEmpty').hidden = shown.length > 0;
    observe(list);
  }

  async function loadNews() {
    const d = await getJSON('news.json');
    news = (d?.items || []).map((n) => {
      // 標題結尾的「 - 媒體名」已在來源欄顯示
      const suffix = n.source ? ` - ${n.source}` : '';
      let title = suffix && n.title.endsWith(suffix) ? n.title.slice(0, -suffix.length) : n.title;
      // 去掉結尾的欄目標籤，如「| 國際」「｜ 生活」
      title = title.replace(/\s*[|｜]\s*[^|｜\s]{1,8}\s*$/, '').trim();
      return { ...n, title };
    });
    if (d?.updated) $('#updated').textContent = `更新 ${clock(d.updated)}`;
    const sources = [...new Set(news.map((n) => n.source).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-TW'));
    const sel = $('#src');
    const keep = sel.value;
    sel.length = 1;
    for (const s of sources) {
      const o = el('option', null, s);
      o.value = s;
      sel.append(o);
    }
    sel.value = sources.includes(keep) ? keep : '';
    renderFront();
    renderNews();
  }

  // ---------- Threads 社群版 ----------
  let threads = null;
  let account = '';
  const PAGE = window.innerWidth < 640 ? 5 : 9; // 手機一次少放幾則
  let threadsLimit = PAGE;
  const STAT_ICONS = {
    likes: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    replies: '<path d="M20 12a8 8 0 0 1-11.6 7.1L4 20l1-4.1A8 8 0 1 1 20 12z"/>',
    reposts: '<path d="M7 7h10l-3-3M17 17H7l3 3"/>',
  };

  function renderThreads() {
    const list = $('#threadsList');
    const chips = $('#accounts');
    list.textContent = '';
    chips.textContent = '';
    const groups = (threads?.groups || []).filter((g) => g.posts.length);
    if (!groups.length) {
      $('#threadsEmpty').textContent = 'Threads 暫時沒有資料，下一次整點更新會再試。';
      $('#threadsEmpty').hidden = false;
      $('#threadsMore').hidden = true;
      return;
    }
    $('#threadsEmpty').hidden = true;
    $('#threadsNote').textContent = threads.note || '';

    const chip = (label, value, count) => {
      const b = el('button', 'chip', label);
      b.type = 'button';
      if (count != null) b.append(el('small', null, count));
      b.setAttribute('aria-pressed', String(account === value));
      b.addEventListener('click', () => { account = value; threadsLimit = PAGE; renderThreads(); });
      chips.append(b);
    };
    const total = new Set(groups.flatMap((g) => g.posts.map((p) => p.id))).size;
    chip('全部', '', total);
    groups.forEach((g) => chip(g.keyword, g.keyword, g.posts.length));

    const seen = new Set();
    const posts = groups.filter((g) => !account || g.keyword === account)
      .flatMap((g) => g.posts)
      .filter((p) => !seen.has(p.id) && seen.add(p.id))
      .sort((a, b) => (threads.sort === 'latest' ? (Date.parse(b.timestamp) || 0) - (Date.parse(a.timestamp) || 0) : b.score - a.score));

    // 依欄數輪流分配，讓排名由左到右、由上到下閱讀
    const n = window.innerWidth >= 1000 ? 3 : window.innerWidth >= 640 ? 2 : 1;
    list.style.setProperty('--cols', n);
    const cols = Array.from({ length: n }, () => list.appendChild(el('div', 'quotes__col')));
    posts.slice(0, threadsLimit).forEach((p, i) => {
      const entry = { id: p.url, kind: 'threads', title: p.content.split('\n')[0].slice(0, 60), link: p.url, src: `@${p.username}`, date: p.timestamp };
      const fig = el('figure', 'quote item reveal');
      fig.style.setProperty('--d', `${(i % 3) * 0.08}s`);
      if (read.has(entry.id)) fig.classList.add('is-read');
      const who = el('div', 'quote__who');
      who.append(el('span', 'quote__rank', pad(i + 1)), el('span', 'quote__name', p.displayName || p.username), el('span', 'quote__handle', `@${p.username}`));
      const body = el('blockquote', 'quote__body t', p.content);
      const s = p.stats || {};
      const stats = el('div', 'stats');
      for (const k of ['likes', 'replies', 'reposts']) {
        const span = el('span');
        span.append(svg(STAT_ICONS[k]), compact(s[k]));
        span.setAttribute('aria-label', `${{ likes: '讚', replies: '回覆', reposts: '轉發' }[k]} ${s[k] || 0}`);
        stats.append(span);
      }
      stats.append(el('span', null, ago(p.timestamp)));
      fig.append(el('span', 'quote__mark', '“'), articleLink(entry, [who, body, stats]), starButton(entry));
      cols[i % n].append(fig);
    });
    const more = $('#threadsMore');
    more.hidden = posts.length <= threadsLimit;
    more.textContent = `顯示更多（還有 ${posts.length - threadsLimit} 則）`;
    observe(list);
  }

  // ---------- 科技副刊 ----------
  function renderTech(d) {
    const rail = $('#techRail');
    rail.textContent = '';
    const items = d?.items || [];
    $('#techEmpty').hidden = items.length > 0;
    $('#techEmpty').textContent = '科技副刊暫時沒有資料。';
    rail.hidden = !items.length;
    items.forEach((it, i) => {
      const title = it.title_zh || it.title;
      const entry = { id: it.link, kind: 'tech', title, link: it.link, src: 'Unwind AI', date: it.pubDate };
      const card = el('article', 'card item reveal');
      card.style.setProperty('--d', `${Math.min(i, 4) * 0.08}s`);
      if (read.has(entry.id)) card.classList.add('is-read');
      const fig = el('div', 'card__img');
      const imgSrc = safeUrl(it.image);
      if (imgSrc) {
        const img = el('img');
        img.src = imgSrc;
        img.alt = '';
        img.loading = 'lazy';
        img.decoding = 'async';
        img.onerror = () => img.remove();
        fig.append(img);
      }
      const h = el('h3', 'card__title t');
      h.append(el('span', 'hl', title));
      const date = Date.parse(it.pubDate);
      const issueLabel = Number.isNaN(date) ? 'UNWIND AI' : new Intl.DateTimeFormat('zh-TW', { timeZone: TZ, month: 'long', day: 'numeric', weekday: 'short' }).format(date);
      card.append(articleLink(entry, [fig, el('span', 'card__issue', issueLabel), h, el('p', 'card__sum', it.summary_zh || it.summary || '')]), starButton(entry));
      rail.append(card);
    });
    observe(rail);
    railButtons();
  }
  function railButtons() {
    const rail = $('#techRail');
    const [prev, next] = $$('[data-rail]');
    prev.disabled = rail.scrollLeft < 8;
    next.disabled = rail.scrollLeft + rail.clientWidth >= rail.scrollWidth - 8;
  }

  // ---------- AI 業界動態 ----------
  let ai = null;
  let aiSource = '';
  let aiType = 'lab';
  let aiLimit = 10;

  function renderAI() {
    const list = $('#aiList');
    const chips = $('#aiSources');
    list.textContent = '';
    chips.textContent = '';
    // 舊資料沒有 type 時視為官方部落格
    const items = (ai?.items || []).filter((it) => (it.type || 'lab') === aiType);
    if (!items.length) {
      $('#aiEmpty').textContent = `${aiType === 'lab' ? '官方部落格' : '科技媒體'}暫時沒有資料，下一次整點更新會再試。`;
      $('#aiEmpty').hidden = false;
      $('#aiMore').hidden = true;
      return;
    }
    $('#aiEmpty').hidden = true;
    const counts = {};
    items.forEach((it) => { counts[it.source] = (counts[it.source] || 0) + 1; });
    const chip = (label, value, n) => {
      const b = el('button', 'chip', label);
      b.type = 'button';
      b.append(el('small', null, n));
      b.setAttribute('aria-pressed', String(aiSource === value));
      b.addEventListener('click', () => { aiSource = value; aiLimit = 10; renderAI(); });
      chips.append(b);
    };
    chip('全部', '', items.length);
    Object.keys(counts).sort().forEach((k) => chip(k, k, counts[k]));

    const shown = items.filter((it) => !aiSource || it.source === aiSource);
    shown.slice(0, aiLimit).forEach((it, i) => {
      const title = it.title_zh || it.title;
      const entry = { id: it.link, kind: 'ai', title, link: it.link, src: it.source, date: it.pubDate };
      const li = el('li', 'dispatch item reveal');
      li.style.setProperty('--d', `${(i % 2) * 0.06}s`);
      if (read.has(entry.id)) li.classList.add('is-read');
      const text = el('div');
      const h = el('h3', 'dispatch__title t');
      h.append(el('span', 'hl', title));
      text.append(el('span', 'dispatch__src', it.source), h);
      if (it.title_zh && it.title_zh !== it.title) text.append(el('p', 'dispatch__orig', it.title));
      const sum = it.summary_zh || it.summary;
      if (sum) text.append(el('p', 'dispatch__sum', sum));
      text.append(metaLine('', it.pubDate));
      const parts = [text];
      const imgSrc = safeUrl(it.image);
      if (imgSrc) {
        const fig = el('div', 'dispatch__img');
        const img = el('img');
        img.src = imgSrc;
        img.alt = '';
        img.loading = 'lazy';
        img.decoding = 'async';
        img.onerror = () => fig.remove();
        fig.append(img);
        parts.push(fig);
      }
      li.append(articleLink(entry, parts), starButton(entry));
      list.append(li);
    });
    const more = $('#aiMore');
    more.hidden = shown.length <= aiLimit;
    more.textContent = `顯示更多（還有 ${shown.length - aiLimit} 則）`;
    observe(list);
  }

  // ---------- 進場動效 ----------
  const io = 'IntersectionObserver' in window
    ? new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
    }), { rootMargin: '0px 0px -6% 0px' })
    : null;
  function observe(root) {
    $$('.reveal:not(.is-in)', root).forEach((n) => (io ? io.observe(n) : n.classList.add('is-in')));
  }

  // ---------- 導覽列 ----------
  function setupBar() {
    const bar = $('#bar');
    const head = $('.masthead__nav');
    if (!('IntersectionObserver' in window)) return;
    new IntersectionObserver(([e]) => bar.classList.toggle('is-on', !e.isIntersecting && e.boundingClientRect.top < 0)).observe(head);
    const links = $$('.bar__links a');
    const spy = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting) return;
      links.forEach((a) => a.classList.toggle('is-active', a.getAttribute('href') === `#${e.target.id}`));
    }), { rootMargin: '-45% 0px -50% 0px' });
    $$('main .section').forEach((s) => spy.observe(s));
  }

  // ---------- 事件 ----------
  function bind() {
    let t;
    $('#q').addEventListener('input', () => { clearTimeout(t); t = setTimeout(renderNews, 120); });
    $('#src').addEventListener('change', renderNews);
    $('#unreadOnly').addEventListener('click', (e) => {
      const b = e.currentTarget;
      b.setAttribute('aria-pressed', String(b.getAttribute('aria-pressed') !== 'true'));
      renderNews();
    });
    $('#threadsMore').addEventListener('click', () => { threadsLimit += PAGE; renderThreads(); });
    $('#aiMore').addEventListener('click', () => { aiLimit += 10; renderAI(); });
    $$('[data-ai-type]').forEach((b) => b.addEventListener('click', () => {
      aiType = b.dataset.aiType;
      aiSource = '';
      aiLimit = 10;
      $$('[data-ai-type]').forEach((x) => x.setAttribute('aria-selected', String(x === b)));
      renderAI();
    }));

    const rail = $('#techRail');
    $$('[data-rail]').forEach((b) => b.addEventListener('click', () => {
      rail.scrollBy({ left: +b.dataset.rail * rail.clientWidth * 0.85, behavior: 'smooth' });
    }));
    rail.addEventListener('scroll', railButtons, { passive: true });
    let colsAt = window.innerWidth >= 1000 ? 3 : window.innerWidth >= 640 ? 2 : 1;
    window.addEventListener('resize', () => {
      railButtons();
      const now = window.innerWidth >= 1000 ? 3 : window.innerWidth >= 640 ? 2 : 1;
      if (now !== colsAt) { colsAt = now; renderThreads(); }
    }, { passive: true });

    const dlg = $('#saved');
    const open = () => { renderSaved(); dlg.showModal(); };
    $$('[data-open-saved]').forEach((b) => b.addEventListener('click', open));
    $('[data-close-saved]').addEventListener('click', () => dlg.close());
    dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close(); });

    document.addEventListener('keydown', (e) => {
      const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName);
      if (e.key === '/' && !typing) {
        e.preventDefault();
        $('#q').focus({ preventScroll: true });
        $('#news').scrollIntoView({ behavior: 'smooth' });
      } else if (e.key === 's' && !typing && !e.metaKey && !e.ctrlKey && !dlg.open) {
        open();
      } else if (e.key === 'Escape' && typing && document.activeElement === $('#q')) {
        $('#q').value = '';
        renderNews();
        $('#q').blur();
      }
    });
  }

  // ---------- 啟動 ----------
  dateline();
  bind();
  setupBar();
  updateSaved();
  observe(document);
  loadNews();
  getJSON('threads.json').then((d) => { threads = d; renderThreads(); });
  getJSON('unwind.json').then(renderTech);
  getJSON('ai.json').then((d) => { ai = d; renderAI(); });
  // 頁面放著不關時，每 10 分鐘更新相對時間與資料
  setInterval(() => { dateline(); loadNews(); }, 10 * 60 * 1000);
})();
