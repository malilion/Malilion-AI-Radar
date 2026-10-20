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
})();
