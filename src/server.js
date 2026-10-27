// HTTP entry point. Serves the landing page and the cards; starts the Telegram
// bot in the same process when a token is configured, so one systemd unit and
// one data directory cover the whole service.

import http from 'node:http';
import { config } from './config.js';
import { getCard, sweepExpired } from './store.js';
import { renderCard, renderExpired, esc, page, BASE_CSS, SKY_JS } from './card.js';
import { startBot } from './bot.js';

function landingPage() {
  const botLink = process.env.BOT_USERNAME
    ? `https://t.me/${process.env.BOT_USERNAME.replace(/^@/, '')}`
    : null;

  const body = `<canvas id="sky" aria-hidden="true"></canvas>
<main>
  <div class="eyebrow">birthdaygift</div>
  <h1>Tug‘ilgan kun uchun<br><em>shaxsiy tabrik sahifasi</em></h1>
  <article class="letter">
    <p>Telegram botga ism, yosh va bir-ikki detal aytasiz — bot sizga havola qaytaradi.
    Havolani tug‘ilgan kun egasiga yuborasiz: u shamlarni puflaydi, kuy yangraydi,
    xat ochiladi.</p>
    <p>Har bir havola <b>5 kun</b> yashaydi, keyin o‘chadi.</p>
  </article>
  <p class="note">${
    botLink
      ? `Botni ochish: <a href="${esc(botLink)}">${esc(botLink)}</a>`
      : 'Bot hozircha ulanmagan.'
  }<br>
  Kod: <a href="https://github.com/gaspiralli97/birthdaygift">github.com/gaspiralli97/birthdaygift</a></p>
</main>`;

  return page({ title: 'birthdaygift', body, script: SKY_JS, lang: 'uz' });
}

function send(res, status, body, contentType = 'text/html; charset=utf-8') {
  res.writeHead(status, {
    'content-type': contentType,
    'content-length': Buffer.byteLength(body),
    // Cards are private links; keep them out of shared caches and referrers.
    'cache-control': 'no-store',
    'referrer-policy': 'no-referrer',
    'x-content-type-options': 'nosniff',
    'content-security-policy':
      "default-src 'none'; img-src 'self' data:; media-src blob:; " +
      "style-src 'unsafe-inline' https://fonts.googleapis.com; " +
      "font-src https://fonts.gstatic.com; script-src 'unsafe-inline'; " +
      "connect-src 'none'; base-uri 'none'; form-action 'none'",
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = url.pathname.replace(/\/+$/, '') || '/';

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    return send(res, 405, 'Method not allowed', 'text/plain; charset=utf-8');
  }

  if (pathname === '/healthz') {
    return send(res, 200, 'ok', 'text/plain; charset=utf-8');
  }

  if (pathname === '/') {
    return send(res, 200, landingPage());
  }

  const match = pathname.match(/^\/c\/([A-Za-z0-9]{1,16})$/);
  if (match) {
    const card = getCard(match[1]);
    if (!card) return send(res, 404, renderExpired(url.searchParams.get('lang') || 'uz'));
    return send(res, 200, renderCard(card));
  }

  return send(res, 404, renderExpired('uz'));
});

server.listen(config.port, '127.0.0.1', () => {
  console.log(`[http] listening on 127.0.0.1:${config.port} -> ${config.publicUrl}`);
  console.log(`[http] text provider: ${config.aiProvider}`);
});

// Expired cards are also dropped lazily on read; this sweep is what keeps the
// directory from filling with cards nobody ever opened.
const removed = sweepExpired();
if (removed) console.log(`[store] removed ${removed} expired card(s) at startup`);
setInterval(() => {
  const n = sweepExpired();
  if (n) console.log(`[store] removed ${n} expired card(s)`);
}, 60 * 60 * 1000).unref();

startBot();

const shutdown = signal => () => {
  console.log(`[http] ${signal}, closing`);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 5000).unref();
};
process.on('SIGTERM', shutdown('SIGTERM'));
process.on('SIGINT', shutdown('SIGINT'));
