// 電子報閱讀頁：切換期數、複製與下載
(() => {
  'use strict';
  const day = document.body.dataset.day;
  const hint = document.getElementById('hint');
  const say = (msg, ok = true) => { hint.textContent = msg; hint.classList.toggle('is-ok', ok); };
  const text = async (url) => (await fetch(url, { cache: 'no-cache' })).text();

  document.getElementById('pick').addEventListener('change', (e) => { location.href = `${e.target.value}.html`; });

  // 複製成「格式化內容」：貼到 Gmail／Outlook／電子報編輯器會保留排版
  document.getElementById('copyRich').addEventListener('click', async () => {
    const email = document.getElementById('email');
    try {
      const md = await text(`${day}.md`);
      await navigator.clipboard.write([new ClipboardItem({
        'text/html': new Blob([email.innerHTML], { type: 'text/html' }),
        'text/plain': new Blob([md], { type: 'text/plain' }),
      })]);
      say('已複製郵件內容，直接貼到郵件編輯器即可。');
    } catch {
      // 不支援 ClipboardItem 的瀏覽器：選取後用舊方法複製
      const range = document.createRange();
      range.selectNodeContents(email);
      const sel = getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      const ok = document.execCommand('copy');
      sel.removeAllRanges();
      say(ok ? '已複製郵件內容。' : '複製失敗，請改用「下載 HTML」。', ok);
    }
  });

  document.getElementById('copyHtml').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(await text(`${day}.email.html`));
      say('已複製 HTML 原始碼，可貼到電子報平台的「HTML 編輯」模式。');
    } catch {
      say('複製失敗，請改用「下載 HTML」。', false);
    }
  });

  // 左右翻頁
  const email = document.getElementById('email');
  const sheets = [...email.children];
  if (sheets.length > 1) {
    const mk = (label, cls) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = label; b.className = cls; return b; };
    const prev = mk('← 上一頁', 'prev');
    const next = mk('下一頁 →', 'next');
    const pos = document.createElement('span');
    const bar = document.createElement('div');
    bar.className = 'nl-pager';
    bar.append(prev, pos, next);
    email.before(bar);
    const cur = () => Math.round(email.scrollLeft / email.clientWidth);
    const go = (i) => email.scrollTo({ left: Math.max(0, Math.min(sheets.length - 1, i)) * email.clientWidth });
    const sync = () => {
      const i = cur();
      pos.textContent = `第 ${i + 1} 頁 / 共 ${sheets.length} 頁`;
      prev.disabled = i <= 0;
      next.disabled = i >= sheets.length - 1;
    };
    prev.addEventListener('click', () => go(cur() - 1));
    next.addEventListener('click', () => go(cur() + 1));
    email.addEventListener('scroll', sync, { passive: true });
    addEventListener('keydown', (e) => {
      if (e.target.closest('select, input, textarea')) return;
      if (e.key === 'ArrowLeft') go(cur() - 1);
      if (e.key === 'ArrowRight') go(cur() + 1);
    });
    sync();
  }
})();
