#!/usr/bin/env node
// Fill Traderie's "Add Listing" form in the player's own browser over the Chrome DevTools port.
//
//   node pricing/tools/traderie_list.mjs spec.json [--submit] [--port 8333]
//
// The spec (a JSON file, or "-" for stdin):
//   {"item": "Throwing Spear", "rarity": "magic", "ethereal": false, "amount": 1,
//    "properties": [{"search": "Warcries", "option": "+X to Warcries (Barbarian Only)", "value": 3}],
//    "price": [{"rune": "Mal Rune", "amount": 1}],
//    "offers": "open"}            // "open" (default), "listing_price_only" or "ask_for_offers"
//
// It opens a new tab, fills the form, reads every field back and prints it. Without --submit the
// filled form is left for the player to post; nothing outside that one tab is touched. Ladder,
// platform, mode and game version come from the account defaults and are checked, not set.
import fs from 'node:fs';
import { button, control, fail, labelled, openTab, quote } from './traderie_browser.mjs';

const args = process.argv.slice(2);
const flag = name => args.includes(name);
const option = (name, fallback) => (args.includes(name) ? args[args.indexOf(name) + 1] : fallback);
const port = option('--port', '8333');
const specPath = args.find(a => !a.startsWith('--') && a !== option('--port'));
if (!specPath) {
  console.error('usage: traderie_list.mjs spec.json [--submit] [--port 8333]');
  process.exit(2);
}
const spec = JSON.parse(fs.readFileSync(specPath === '-' ? 0 : specPath, 'utf8'));
const SCOPE = spec.scope ?? ['Non Ladder', 'PC', 'softcore', 'reign of the warlock'];
const CREATE = 'https://traderie.com/diablo2resurrected/listings/create';

const tab = await openTab(CREATE, port);
const { js, click, key, choose, setNumber } = tab;
const numberInput = near =>
  `[...document.querySelectorAll('input[type=number]')].find(e => (e.closest('div')?.parentElement?.innerText || '').includes(${quote(near)}))`;

await tab.waitFor(
  `document.readyState === 'complete' && document.body.innerText.includes("Item you're trading")`,
  'the Add Listing form did not load',
);

await choose(control('Search Items...'), 'item search', spec.item, spec.item);
if (spec.rarity) await choose(labelled('Rarity'), 'rarity', spec.rarity, spec.rarity);
if (spec.ethereal)
  await click(
    `[...document.querySelectorAll('label')].find(l => l.innerText.trim() === 'Ethereal')`,
    'ethereal checkbox',
  );
if ((spec.amount ?? 1) !== 1) await setNumber(`document.getElementById('listing-item-amount')`, 'amount', spec.amount);
for (const property of spec.properties ?? []) {
  await choose(control('Search options...'), 'property search', property.search, property.option);
  await key('Escape');
  if (property.value !== undefined) {
    // "+X to Warcries (Barbarian Only)" is shown on the form as "+ to Warcries (Barbarian Only)".
    const shown = property.option.replace(/X/g, '').replace(/^[+\s%]+/, '').trim();
    await setNumber(numberInput(shown), property.option, property.value);
  }
}
for (const price of spec.price ?? []) await tab.addPrice(price);
const offers = { listing_price_only: 'listing-accept-listing-price', ask_for_offers: 'listing-ask-for-offers' }[spec.offers];
if (offers) await click(`document.querySelector('label[for="${offers}"]') || document.getElementById('${offers}')`, spec.offers);

const state = await js(`(() => {
  const text = document.body.innerText, start = text.indexOf("Item you're trading"), end = text.indexOf('HELP');
  return {
    form: text.slice(start, end).split('\\n').map(s => s.trim()).filter(Boolean),
    numbers: [...document.querySelectorAll('input[type=number]')].map(e => [
      (e.closest('div')?.parentElement?.innerText || '').trim().split('\\n')[0], e.value]),
    checks: Object.fromEntries([...document.querySelectorAll('input[type=checkbox]')].filter(e => e.id).map(e => [e.id, e.checked])),
    ethereal: [...document.querySelectorAll('label')].find(l => l.innerText.trim() === 'Ethereal')
      ?.parentElement.querySelector('input')?.checked ?? null,
  };
})()`);
const problems = [];
for (const expected of [spec.item, spec.rarity, ...SCOPE, ...(spec.price ?? []).map(p => p.rune)].filter(Boolean))
  if (!state.form.includes(expected)) problems.push(`"${expected}" is not on the form`);
for (const property of (spec.properties ?? []).filter(p => p.value !== undefined)) {
  const shown = property.option.replace(/X/g, '').replace(/^[+\s%]+/, '').trim();
  const found = state.numbers.find(([label]) => label.includes(shown));
  if (!found || Number(found[1]) !== Number(property.value))
    problems.push(`${property.option} reads ${found ? found[1] : 'nothing'}, wanted ${property.value}`);
}
console.log(JSON.stringify({ tab: tab.id, properties: state.numbers, checks: state.checks, ethereal: state.ethereal, problems }, null, 1));
if (problems.length) fail('the form does not match the spec; the tab is left open for inspection');

if (flag('--submit')) {
  await click(button('Add Listing'), 'Add Listing');
  await tab.waitFor(`document.body.innerText.includes('Your listing has been submitted')`, 'no confirmation appeared', 20);
  const posted = await js(`document.body.innerText.includes('Your listing has been submitted')`);
  console.log(posted ? 'Posted: Traderie confirmed the listing.' : 'Clicked Add Listing, but no confirmation appeared: check the tab.');
  if (!posted) process.exitCode = 1;
} else {
  console.log('Form filled and verified; not submitted. Press "Add Listing" in the new tab, or rerun with --submit.');
}
tab.close();
