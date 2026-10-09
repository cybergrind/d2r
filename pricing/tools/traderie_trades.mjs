#!/usr/bin/env node
// Traderie "Recent Trades" of a base or named item (offers that were accepted AND completed), read through
// the player's own logged-in browser. This is the only trade record Traderie has: listing asks and the
// `completed` listing flag are not sales (completed listings include ones that expired, 2026-10-09 check).
//
//   node pricing/tools/traderie_trades.mjs <product slug>... [--port 8333] [--out DIR] [--wait 15]
//
// Each slug (Traderie product URL name: kris, legend-spike, bone-wand, harlequin-crest…) loads
//   https://traderie.com/diablo2resurrected/product/<slug>/recent?prop_Mode=softcore&prop_Ladder=false&prop_Game version=reign of the warlock
// in a hidden background target: no tab in the tab strip, no focus change, closed afterwards. Only the
// offers and price-history answers the page requests are saved, as DIR/<slug>.json; the page's other
// requests (account, notifications) are discarded. Slugs are loaded --wait seconds apart (default 15).
// The site returns the 20 newest trades per page. Summarise with pricing/tools/traderie_trades.py.
import { writeFileSync, mkdirSync } from 'node:fs';
const args = process.argv.slice(2);
const option = (name, fallback) => (args.includes(name) ? args[args.indexOf(name) + 1] : fallback);
const port = option('--port', '8333');
const outDir = option('--out', `pricing/raw/traderie/recent-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`);
const wait = Number(option('--wait', '15')) * 1000;
const slugs = args.filter((a, i) => !a.startsWith('--') && !['--port', '--out', '--wait'].includes(args[i - 1]));
if (!slugs.length) { console.error('usage: traderie_trades.mjs <slug>... [--port 8333] [--out DIR] [--wait 15]'); process.exit(2); }
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
for (const [i, slug] of slugs.entries()) {
  bodies = [];
  const url = `https://traderie.com/diablo2resurrected/product/${slug}/recent?prop_Mode=softcore&prop_Ladder=false&prop_Game%20version=reign%20of%20the%20warlock`;
  const created = await send('Target.createTarget', { url: 'about:blank', hidden: true, background: true });
  const attached = await send('Target.attachToTarget', { targetId: created.result.targetId, flatten: true });
  tab = attached.result.sessionId;
  await send('Network.enable', {}, tab);
  await send('Page.navigate', { url }, tab);
  for (let t = 0; t < 24 && !bodies.some(b => b.url.includes('/offers?')); t++) await sleep(500);
  await sleep(1500);
  await send('Target.closeTarget', { targetId: created.result.targetId });
  const offers = bodies.filter(b => b.url.includes('/offers?')).length;
  writeFileSync(`${outDir}/${slug}.json`, JSON.stringify({ url, pulled_at: new Date().toISOString(), api: bodies }, null, 1));
  console.log(`${slug}: ${offers ? 'saved' : 'NO offers answer (logged out? unknown slug?)'} → ${outDir}/${slug}.json`);
  if (i < slugs.length - 1) await sleep(wait);
}
ws.close();
