#!/usr/bin/env node
// Print the player's active Traderie listings as JSON: id, item lines and asking price.
//
//   node pricing/tools/traderie_listings.mjs <profile id> [--port 8333]
import { openTab, sleep } from './traderie_browser.mjs';

const args = process.argv.slice(2);
const profile = args.find(a => /^\d+$/.test(a));
if (!profile) {
  console.error('usage: traderie_listings.mjs <profile id> [--port 8333]');
  process.exit(2);
}
const port = args.includes('--port') ? args[args.indexOf('--port') + 1] : '8333';
const tab = await openTab(`https://traderie.com/diablo2resurrected/profile/${profile}/listings`, port);
await tab.waitFor(`document.querySelectorAll('a[href*="/listing/"]').length > 0`, 'no listings appeared');
for (let pass = 0; pass < 6; pass++) {
  await tab.js('window.scrollTo(0, document.body.scrollHeight)');
  await sleep(1200);
}
const listings = await tab.js(`(() => { const out = {};
  for (const a of document.querySelectorAll('a[href*="/listing/"]')) {
    let card = a;
    for (let i = 0; i < 8 && card && !(card.innerText.includes('Trading For') && card.innerText.includes('Mark Sold')); i++) card = card.parentElement;
    if (!card) continue;
    const lines = card.innerText.split('\\n').map(s => s.replace(/•/g, '').trim()).filter(Boolean);
    const at = lines.indexOf('Trading For'), end = lines.findIndex(l => l.startsWith('High Rune Value'));
    out[a.href.split('/').pop().split('?')[0]] = { item: lines.slice(lines.findIndex(l => /^\\d+ X /.test(l)), at), price: lines.slice(at + 1, end) };
  }
  return Object.entries(out).map(([id, v]) => ({ id, ...v })); })()`);
console.log(JSON.stringify(listings, null, 1));
await tab.closeTab();
tab.close();
