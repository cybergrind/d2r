#!/usr/bin/env node
// Change the asking price of one of the player's own Traderie listings.
//
//   node pricing/tools/traderie_edit.mjs <listing id> --price "Ist Rune:6" [--price "Ohm Rune:1"] [--submit]
//
// Traderie's edit form changes pricing only; the item and its rolls stay as listed. Several --price
// entries are asked together (rune AND rune). An "Or" alternative on the listing makes the tool stop:
// those are edited by hand. Without --submit the form is filled, read back and left open.
import { button, fail, openTab, parsePrice, quote, sleep } from './traderie_browser.mjs';

const args = process.argv.slice(2);
const values = name => args.flatMap((a, i) => (a === name ? [args[i + 1]] : []));
const listing = args.find(a => /^\d+$/.test(a));
const prices = values('--price').map(parsePrice);
if (!listing || !prices.length) {
  console.error('usage: traderie_edit.mjs <listing id> --price "Ist Rune:6" [--submit] [--port 8333]');
  process.exit(2);
}
const tab = await openTab(`https://traderie.com/diablo2resurrected/listing/${listing}`, values('--port')[0] ?? '8333');
const { js, click } = tab;
await tab.waitFor(`!!document.querySelector('.listing-edit-icon')`, 'no edit icon: not your listing, or it did not load');
const before = await js(`(() => { const t = document.body.innerText, a = t.indexOf('I Have This'), b = t.indexOf('Listed ');
  return t.slice(a + 11, b).split('\\n').map(s => s.trim()).filter(Boolean); })()`);
// The icon is drawn before the page wires it up, so an early click can be lost: retry.
for (let attempt = 0; attempt < 5 && !(await js(`!!${button('Edit Listing')}`)); attempt++) {
  await click(`document.querySelector('.listing-edit-icon')`, 'edit icon');
  await sleep(1500);
}
await tab.waitFor(`!!${button('Edit Listing')}`, 'the edit form did not open', 6);
if ((await js(`document.querySelectorAll('.offer-table-items').length`)) > 1)
  fail('this listing has an "Or" price alternative; edit it by hand in the open tab');
for (let rows = await tab.priceRows(); rows.length; rows = await tab.priceRows()) {
  await click(`document.querySelector('.offer-table-items button[aria-label="Remove item"]')`, 'remove price row');
  if ((await tab.priceRows()).length >= rows.length) fail('could not remove the old price');
}
for (const price of prices) await tab.addPrice(price);
const now = await tab.priceRows();
const wanted = prices.map(p => [p.rune, p.amount]);
console.log(quote({ listing, item: before.slice(0, 8), price: now }));
if (quote(now) !== quote(wanted)) fail(`the form reads ${quote(now)}, wanted ${quote(wanted)}; the tab is left open`);
if (args.includes('--submit')) {
  await click(button('Edit Listing'), 'Edit Listing');
  await tab.waitFor(`!${button('Edit Listing')} || /updated|edited|success/i.test(document.body.innerText)`, 'no confirmation after Edit Listing', 20);
  console.log('Saved.');
  await tab.closeTab();
} else {
  console.log('Price filled and verified; not saved. Press "Edit Listing" in the new tab, or rerun with --submit.');
}
tab.close();
