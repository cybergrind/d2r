#!/usr/bin/env node
// Relist expired Traderie listings in the player's browser, one "Relist" button per listing.
//
//   node pricing/tools/traderie_relist.mjs <profile id>                  # list expired listings, click nothing
//   node pricing/tools/traderie_relist.mjs <profile id> <listing id>...  # dry run: check the Relist button exists
//   node pricing/tools/traderie_relist.mjs <profile id> <listing id>... --submit   # click Relist
//   node pricing/tools/traderie_relist.mjs <profile id> --all --submit   # click every expired listing
//
// An expired listing shows "Relist" where the timer usually is. A relisted one shows a timer again
// ("20 hour(s)"), and the Relist button is gone. The tab opens in the background tools window.
import { openTab, sleep, fail, quote } from './traderie_browser.mjs';

const args = process.argv.slice(2);
const values = flag => {
  const i = args.indexOf(flag);
  return i < 0 ? [] : [args[i + 1]];
};
const submit = args.includes('--submit');
const all = args.includes('--all');
const port = values('--port')[0] ?? '8333';
const positional = args.filter((a, i) => !a.startsWith('--') && !(i > 0 && args[i - 1] === '--port'));
const [profile, ...listings] = positional;
if (!profile || !/^\d+$/.test(profile) || (!all && !listings.length && submit)) {
  console.error('usage: traderie_relist.mjs <profile id> [<listing id>...] [--all] [--submit] [--port 8333]');
  process.exit(2);
}

// The card of one listing: climb from its link to the element that holds the buttons and the timer.
const card = id => `(() => { let c = document.querySelector('a[href*="/listing/${id}"]');
  for (let i = 0; i < 8 && c && !(c.innerText.includes('Mark Sold') || c.innerText.includes('Relist')); i++) c = c.parentElement;
  return c; })()`;
const relistButton = id => `(() => { const c = ${card(id)};
  return c ? [...c.querySelectorAll('button')].find(b => b.innerText.trim() === 'Relist') ?? null : null; })()`;

const tab = await openTab(`https://traderie.com/diablo2resurrected/profile/${profile}/listings`, port);
const { js, click } = tab;
await tab.waitFor(`document.querySelectorAll('a[href*="/listing/"]').length > 0`, 'no listings appeared', 20);
await sleep(1500);

// Every listing on the page that currently offers Relist.
const ids = await js(`[...new Set([...document.querySelectorAll('a[href*="/listing/"]')].map(a => a.href.split('/').pop().split('?')[0]))]`);
const expired = [];
for (const id of ids) if (await js(`!!(${relistButton(id)})`)) expired.push(id);
const targets = all ? expired : listings;

if (!targets.length) {
  console.log(quote({ expired, results: [] }));
  await tab.closeTab();
  tab.close();
  process.exit(0);
}

const results = [];
for (const id of targets) {
  if (!(await js(`!!(${relistButton(id)})`))) {
    results.push({ id, status: 'no Relist button (active, or not this profile\'s listing)' });
    continue;
  }
  if (!submit) {
    results.push({ id, status: 'Relist button found; not clicked (rerun with --submit)' });
    continue;
  }
  await click(relistButton(id), `Relist ${id}`);
  await tab.waitFor(`!(${relistButton(id)})`, `Relist ${id}: the button stayed`, 15);
  const timer = await js(`(() => { const c = ${card(id)}; return c ? c.innerText.split('\\n').map(s => s.trim()).find(s => /hour|minute|day/.test(s)) ?? null : null; })()`);
  results.push({ id, status: timer ? 'relisted' : 'relisted, timer not found', timer });
}
console.log(quote({ expired, results }));
await tab.closeTab();
tab.close();
