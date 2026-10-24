#!/usr/bin/env node
// Traderie "Recent Trades" of a base or named item (offers that were accepted AND completed), read through
// the player's own logged-in browser. This is the only trade record Traderie has: listing asks and the
// `completed` listing flag are not sales (completed listings include ones that expired, 2026-10-09 check).
//
//   node pricing/tools/traderie_trades.mjs <product slug or catalog id>... [--port 8333] [--out DIR] [--wait 15] [--skip-existing]
//
// Each slug (Traderie product URL name: kris, legend-spike, bone-wand, harlequin-crest…) loads
//   https://traderie.com/diablo2resurrected/product/<slug>/recent?prop_Mode=softcore&prop_Ladder=false&prop_Game version=reign of the warlock
// in a hidden background target: no tab in the tab strip, no focus change, closed afterwards. Only the
// offers and price-history answers the page requests are saved, as DIR/<slug>.json; the page's other
// requests (account, notifications) are discarded. Slugs are loaded --wait seconds apart (default 15);
// --skip-existing leaves products whose DIR/<slug>.json already exists alone (resume a long run); with --pages, it
// skips the pages already saved instead.
// The site returns the 20 newest trades per page. Summarise with pricing/tools/traderie_trades.py.
//
// --pages N (2026-10-24): also page back through the trades, pages 0..N-1 (the site's own request on a reload, its
// page number and the scope filters rewritten: `pageBack`), --gap seconds apart (default 3; run one pull at a time), each saved as DIR/<slug>-p<page>.json in the
// shape of the 2026-10-23 base-price pull ({offers, nextPage, …, _pulled_at, _url, _via}). Stops at the first empty
// page, or at the first page whose newest trade is older than --since YYYY-MM-DD. The site serves 31 pages at most
// (620 trades, 2026-10-24): --filter adds query terms to narrow it server-side (prop_441Min=3: all res 3+), and
// --name names the files instead of the slug.
import { writeFileSync, mkdirSync, existsSync, readFileSync } from 'node:fs';
const args = process.argv.slice(2);
const option = (name, fallback) => (args.includes(name) ? args[args.indexOf(name) + 1] : fallback);
const port = option('--port', '8333');
const outDir = option('--out', `pricing/raw/traderie/recent-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`);
const wait = Number(option('--wait', '15')) * 1000;
const skipExisting = args.includes('--skip-existing');
const pages = Number(option('--pages', '0'));
const since = option('--since', null);
const gap = Number(option('--gap', '3')) * 1000; // between pages; more parallel pulls than one drew Cloudflare's challenge (2026-10-24)
const filter = option('--filter', ''); // extra query terms for the offers request, e.g. prop_441Min=3
const VALUED = ['--port', '--out', '--wait', '--pages', '--since', '--filter', '--name', '--gap'];
const tag = option('--name', null); // the files' name instead of the slug (a filtered pull of the same item)
const slugs = args.filter((a, i) => !a.startsWith('--') && !VALUED.includes(args[i - 1]));
if (!slugs.length) { console.error('usage: traderie_trades.mjs <slug>... [--port 8333] [--out DIR] [--wait 15] [--pages N [--since YYYY-MM-DD]]'); process.exit(2); }
const KEEP = /\/api\/diablo2resurrected\/(offers\?|items\/prices\?)/;
const sleep = ms => new Promise(r => setTimeout(r, ms));
mkdirSync(outDir, { recursive: true });
const version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
const ws = new WebSocket(version.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { ws.addEventListener('open', resolve); ws.addEventListener('error', reject); });
let nextId = 0; const pending = new Map(); let bodies = []; const wanted = new Map(); let tab = null;
const send = (method, params = {}, sessionId) => new Promise(resolve => { pending.set(++nextId, resolve); ws.send(JSON.stringify({ id: nextId, method, params, sessionId })); });
ws.addEventListener('message', async event => {
  const m = JSON.parse(event.data);
  if (m.id) { pending.get(m.id)?.(m); pending.delete(m.id); return; }
  if (m.method === 'Network.responseReceived' && KEEP.test(m.params.response.url)) wanted.set(m.params.requestId, m.params.response.url);
  if (m.method === 'Network.loadingFinished' && wanted.has(m.params.requestId)) {
    const url = wanted.get(m.params.requestId); wanted.delete(m.params.requestId);
    const body = await send('Network.getResponseBody', { requestId: m.params.requestId }, tab);
    bodies.push({ url, body: body.result?.body ?? null });
  }
});
// Page back: the page is reloaded once a page, and the site's own offers request is paused (Fetch) and continued
// with page=N and the scope filters added. The site sends it with its own login; the token is never read here
// (as traderie_notifications.mjs). One file a page.
const SCOPE = 'prop_Mode=softcore&prop_Ladder=false&prop_Game%20version=reign%20of%20the%20warlock';
let rewrite = null; // the page number the next paused offers request asks for, null: let it through
let sent = null; // the address the last rewritten offers request went to (the Network events show the original)
ws.addEventListener('message', event => {
  const m = JSON.parse(event.data);
  if (m.method !== 'Fetch.requestPaused') return;
  const { requestId, request } = m.params;
  if (rewrite === null || !request.url.includes('/offers?')) { send('Fetch.continueRequest', { requestId }, tab); return; }
  const base = request.url.replace(/&page=\d+/, '');
  const url = `${base}${base.includes('prop_Mode=') ? '' : '&' + SCOPE}${filter ? '&' + filter : ''}&page=${rewrite}`;
  sent = url;
  send('Fetch.continueRequest', { requestId, url }, tab);
});
async function pageBack(slug) {
  await send('Fetch.enable', { patterns: [{ urlPattern: '*/api/diablo2resurrected/offers?*', requestStage: 'Request' }] }, tab);
  for (let page = 0; page < pages; page++) {
    const file = `${outDir}/${tag ?? slug}-p${page}.json`;
    if (skipExisting && existsSync(file)) {
      const kept = JSON.parse(readFileSync(file, 'utf8'));
      const newest = kept.offers.map(o => o.created_at).sort().pop();
      if (!kept.offers.length || kept.nextPage == null || (since && newest && newest.slice(0, 10) < since)) return;
      continue;
    }
    bodies = []; sent = null; rewrite = page;
    await send('Page.reload', { ignoreCache: true }, tab);
    let found = null;
    for (let t = 0; t < 40 && !found; t++) { await sleep(500); found = sent && bodies.findLast(b => b.url.includes('/offers?')); }
    await sleep(500);
    found = bodies.findLast(b => b.url.includes('/offers?')) ?? found;
    rewrite = null;
    let doc = null;
    try { doc = JSON.parse(found?.body ?? 'null'); } catch { doc = null; }
    if (!doc || !Array.isArray(doc.offers)) { console.log(`${slug} page ${page}: no offers answer (${found?.body?.slice(0, 80) ?? 'none'}), stopped`); return; }
    doc._pulled_at = new Date().toISOString(); doc._url = sent; doc._via = 'player browser session (hidden target)';
    writeFileSync(file, JSON.stringify(doc));
    const newest = doc.offers.map(o => o.created_at).sort().pop();
    console.log(`${slug} page ${page}: ${doc.offers.length} trades, newest ${newest ?? '-'}`);
    if (!doc.offers.length || doc.nextPage == null || (since && newest && newest.slice(0, 10) < since)) return;
    await sleep(gap);
  }
}

for (const [i, slug] of slugs.entries()) {
  if (skipExisting && !pages && existsSync(`${outDir}/${slug}.json`)) continue;
  bodies = [];
  const url = `https://traderie.com/diablo2resurrected/product/${slug}/recent?prop_Mode=softcore&prop_Ladder=false&prop_Game%20version=reign%20of%20the%20warlock`;
  const created = await send('Target.createTarget', { url: 'about:blank', hidden: true, background: true });
  const attached = await send('Target.attachToTarget', { targetId: created.result.targetId, flatten: true });
  tab = attached.result.sessionId;
  await send('Network.enable', {}, tab);
  await send('Page.navigate', { url }, tab);
  for (let t = 0; t < 24 && !bodies.some(b => b.url.includes('/offers?')); t++) await sleep(500);
  await sleep(1500);
  const first = bodies.find(b => b.url.includes('/offers?'));
  if (pages && first) await pageBack(slug);
  await send('Target.closeTarget', { targetId: created.result.targetId });
  const offers = bodies.filter(b => b.url.includes('/offers?')).length;
  writeFileSync(`${outDir}/${slug}.json`, JSON.stringify({ url, pulled_at: new Date().toISOString(), api: bodies }, null, 1));
  console.log(`${slug}: ${offers ? 'saved' : 'NO offers answer (logged out? unknown slug?)'} → ${outDir}/${slug}.json`);
  if (i < slugs.length - 1) await sleep(wait);
}
ws.close();
