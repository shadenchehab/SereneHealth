/**
 * PoC OTP board for connectadevrev.work
 *
 * - email(): parse OTP from Auth0/DevRev mail → KV, forward to Gmail
 * - fetch(): private page + JSON API (requires ?k=ACCESS_KEY)
 *
 * Deploy: see README.md
 */

const OTP_TTL_SECONDS = 10 * 60; // 10 minutes
const MAX_ITEMS = 20;

const OTP_PATTERNS = [
  /\b(?:code|otp|passcode|verification code|one[-\s]?time(?:\s+(?:code|password|passcode))?)\s*(?:is|:)?\s*([0-9]{6,8})\b/i,
  /\b([0-9]{6,8})\s+is your (?:verification |login |security )?code\b/i,
  /(?:^|[^\d])([0-9]{6})(?:[^\d]|$)/
];

function htmlPage() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="noindex,nofollow" />
  <title>PoC OTP Board</title>
  <style>
    :root {
      --bg: #0f1419;
      --card: #1a2332;
      --text: #e7ecf3;
      --muted: #8b9bb4;
      --accent: #3d8bfd;
      --ok: #3dd68c;
      --warn: #f5a524;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: radial-gradient(1200px 600px at 20% -10%, #1b2a44, var(--bg));
      color: var(--text);
      min-height: 100vh;
    }
    main { max-width: 720px; margin: 0 auto; padding: 32px 20px 64px; }
    h1 { font-size: 1.4rem; margin: 0 0 6px; }
    .sub { color: var(--muted); font-size: 0.92rem; margin-bottom: 24px; }
    .toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
    button {
      background: var(--accent);
      color: #fff;
      border: 0;
      border-radius: 10px;
      padding: 10px 14px;
      font-weight: 600;
      cursor: pointer;
    }
    button.secondary { background: #2a3648; }
    .status { color: var(--muted); font-size: 0.85rem; }
    .card {
      background: var(--card);
      border: 1px solid #2b384c;
      border-radius: 14px;
      padding: 16px 18px;
      margin-bottom: 12px;
    }
    .row { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }
    .to { font-weight: 600; word-break: break-all; }
    .code {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 1.8rem;
      letter-spacing: 0.12em;
      color: var(--ok);
      margin: 10px 0 4px;
    }
    .meta { color: var(--muted); font-size: 0.82rem; }
    .empty { color: var(--muted); padding: 28px 8px; text-align: center; }
    .expired .code { color: var(--warn); text-decoration: line-through; }
    .err { color: #ff6b6b; margin-top: 12px; }
  </style>
</head>
<body>
  <main>
    <h1>PoC OTP Board</h1>
    <p class="sub">Latest login codes for <code>@connectadevrev.work</code>. Auto-refreshes. Codes expire quickly.</p>
    <div class="toolbar">
      <button type="button" id="refresh">Refresh</button>
      <button type="button" class="secondary" id="copyLatest">Copy latest</button>
      <span class="status" id="status">Loading…</span>
    </div>
    <div id="list"></div>
    <div class="err" id="err" hidden></div>
  </main>
  <script>
    const params = new URLSearchParams(location.search);
    const key = params.get('k') || '';
    const listEl = document.getElementById('list');
    const statusEl = document.getElementById('status');
    const errEl = document.getElementById('err');
    let latestCode = '';

    function ago(iso) {
      const s = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
      if (s < 60) return s + 's ago';
      return Math.floor(s / 60) + 'm ago';
    }

    async function load() {
      errEl.hidden = true;
      try {
        const res = await fetch('./api/otps?k=' + encodeURIComponent(key), { cache: 'no-store' });
        if (!res.ok) throw new Error('HTTP ' + res.status + ' — check your access key');
        const data = await res.json();
        const items = data.items || [];
        latestCode = items[0] && !items[0].expired ? items[0].code : '';
        if (!items.length) {
          listEl.innerHTML = '<div class="empty">No OTPs yet. Trigger a DevRev login to capture one.</div>';
        } else {
          listEl.innerHTML = items.map((it) => {
            const cls = it.expired ? 'card expired' : 'card';
            return '<div class="' + cls + '">' +
              '<div class="row"><div class="to">' + escapeHtml(it.to) + '</div>' +
              '<div class="meta">' + ago(it.receivedAt) + '</div></div>' +
              '<div class="code">' + escapeHtml(it.code) + '</div>' +
              '<div class="meta">' + escapeHtml(it.subject || '') +
              (it.expired ? ' · expired' : ' · valid ~' + Math.max(0, it.ttlLeftSec) + 's') +
              '</div></div>';
          }).join('');
        }
        statusEl.textContent = 'Updated ' + new Date().toLocaleTimeString();
      } catch (e) {
        errEl.hidden = false;
        errEl.textContent = String(e.message || e);
        statusEl.textContent = 'Error';
      }
    }

    function escapeHtml(s) {
      return String(s || '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      })[c]);
    }

    document.getElementById('refresh').onclick = load;
    document.getElementById('copyLatest').onclick = async () => {
      if (!latestCode) return;
      await navigator.clipboard.writeText(latestCode);
      statusEl.textContent = 'Copied ' + latestCode;
    };
    load();
    setInterval(load, 5000);
  </script>
</body>
</html>`;
}

async function readRawEmail(message) {
  const reader = message.raw.getReader();
  const chunks = [];
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }
  const all = new Uint8Array(chunks.reduce((n, c) => n + c.length, 0));
  let offset = 0;
  for (const c of chunks) {
    all.set(c, offset);
    offset += c.length;
  }
  return new TextDecoder('utf-8', { fatal: false }).decode(all);
}

function stripMimeNoise(raw) {
  let text = String(raw || '');
  // Prefer text/plain parts roughly
  const plain = text.match(/Content-Type:\s*text\/plain[\s\S]*?\r?\n\r?\n([\s\S]*?)(?:\r?\n--|\r?\nContent-Type:)/i);
  if (plain?.[1]) text = plain[1];
  text = text
    .replace(/=\r?\n/g, '')
    .replace(/=([0-9A-F]{2})/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ');
  return text;
}

function extractOtp(raw, subject) {
  const haystacks = [subject || '', stripMimeNoise(raw), raw].filter(Boolean);
  for (const hay of haystacks) {
    for (const re of OTP_PATTERNS) {
      const m = hay.match(re);
      if (m?.[1]) return m[1];
    }
  }
  return '';
}

function localPart(email) {
  return String(email || '').split('@')[0] || email;
}

async function loadItems(env) {
  const raw = await env.OTP_KV.get('otps:latest');
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

async function saveOtp(env, item) {
  const now = Date.now();
  let items = await loadItems(env);
  items = items.filter((it) => now - new Date(it.receivedAt).getTime() < OTP_TTL_SECONDS * 1000);
  items.unshift(item);
  items = items.slice(0, MAX_ITEMS);
  await env.OTP_KV.put('otps:latest', JSON.stringify(items), {
    expirationTtl: OTP_TTL_SECONDS * 3
  });
}

function requireKey(url, env) {
  const k = url.searchParams.get('k') || '';
  return Boolean(env.ACCESS_KEY) && k === env.ACCESS_KEY;
}

function withMeta(items) {
  const now = Date.now();
  return items.map((it) => {
    const ageSec = Math.floor((now - new Date(it.receivedAt).getTime()) / 1000);
    const ttlLeftSec = Math.max(0, OTP_TTL_SECONDS - ageSec);
    return { ...it, expired: ttlLeftSec <= 0, ttlLeftSec };
  });
}

export default {
  async email(message, env, ctx) {
    const subject = message.headers.get('subject') || '';
    let raw = '';
    try {
      raw = await readRawEmail(message);
    } catch (err) {
      console.log('raw read failed', String(err));
    }

    const code = extractOtp(raw, subject);
    if (code) {
      const item = {
        id: crypto.randomUUID(),
        to: message.to,
        from: message.from,
        subject,
        code,
        label: localPart(message.to),
        receivedAt: new Date().toISOString()
      };
      ctx.waitUntil(saveOtp(env, item));
      console.log('OTP captured for', message.to);
    } else {
      console.log('No OTP found in mail to', message.to, 'subject=', subject);
    }

    const forwardTo = env.FORWARD_TO || 'devrevpoc@gmail.com';
    await message.forward(forwardTo);
  },

  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return Response.json({ ok: true });
    }

    if (!requireKey(url, env)) {
      return new Response('Unauthorized. Open this page with ?k=YOUR_ACCESS_KEY', {
        status: 401,
        headers: { 'content-type': 'text/plain; charset=utf-8' }
      });
    }

    if (url.pathname === '/api/otps' || url.pathname.endsWith('/api/otps')) {
      const items = withMeta(await loadItems(env));
      return Response.json(
        { items },
        {
          headers: {
            'cache-control': 'no-store',
            'access-control-allow-origin': '*'
          }
        }
      );
    }

    if (url.pathname === '/' || url.pathname === '/index.html') {
      return new Response(htmlPage(), {
        headers: {
          'content-type': 'text/html; charset=utf-8',
          'cache-control': 'no-store',
          'x-robots-tag': 'noindex'
        }
      });
    }

    return new Response('Not found', { status: 404 });
  }
};
