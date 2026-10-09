// Shared driver for the Traderie tools: one new tab in the player's browser, driven over the
// Chrome DevTools port. Every helper acts on that tab only; the player's other tabs are never read.
export const sleep = ms => new Promise(r => setTimeout(r, ms));
export const quote = JSON.stringify;
export const fail = message => {
  console.error('STOPPED: ' + message);
  process.exit(1);
};
// A react-select control is found by the text it currently shows (its placeholder or value).
export const control = text =>
  `[...document.querySelectorAll('div[class*="-control"]')].find(c => c.innerText.trim() === ${quote(text)})`;
// A select is also found by the label printed above it.
export const labelled = label =>
  `[...document.querySelectorAll('div[class*="-control"]')].find(c => (c.parentElement.parentElement.innerText || '').startsWith(${quote(label + '\n')}))`;
export const button = text =>
  `[...document.querySelectorAll('button')].filter(b => b.innerText.trim() === ${quote(text)}).pop()`;

export async function openTab(url, port = '8333') {
  const tab = await (await fetch(`http://127.0.0.1:${port}/json/new?${url}`, { method: 'PUT' })).json();
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve);
    ws.addEventListener('error', reject);
  });
  let nextId = 0;
  const pending = new Map();
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    pending.get(message.id)?.(message);
    pending.delete(message.id);
  });
  const send = (method, params = {}) =>
    new Promise(resolve => {
      pending.set(++nextId, resolve);
      ws.send(JSON.stringify({ id: nextId, method, params }));
    });
  const js = async expression => {
    const reply = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (reply.result?.exceptionDetails) fail('page script error: ' + reply.result.result.description);
    return reply.result?.result?.value;
  };
  // Scroll the element into view and click its centre with real mouse events.
  const click = async (finder, what) => {
    const point = await js(`(() => { const e = ${finder}; if (!e) return null; e.scrollIntoView({block: 'center'});
       const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
    if (!point) fail(`cannot find ${what}`);
    for (const type of ['mousePressed', 'mouseReleased'])
      await send('Input.dispatchMouseEvent', { type, x: point[0], y: point[1], button: 'left', clickCount: 1 });
    await sleep(400);
  };
  const type = text => send('Input.insertText', { text: String(text) });
  const key = async name => {
    const code = { Enter: 13, Escape: 27 }[name];
    for (const type of ['keyDown', 'keyUp'])
      await send('Input.dispatchKeyEvent', { type, key: name, code: name, windowsVirtualKeyCode: code });
  };
  // Type into a select and take the option whose text matches exactly.
  const choose = async (finder, what, search, optionText) => {
    await click(finder, what);
    await type(search);
    let options = [];
    for (let attempt = 0; attempt < 20 && !options.includes(optionText); attempt++) {
      await sleep(300);
      options = await js(`[...document.querySelectorAll('[id*="-option-"]')].map(e => e.innerText.trim())`);
    }
    if (!options.includes(optionText))
      fail(`${what}: no option "${optionText}" for "${search}" (saw ${quote(options)})`);
    await click(
      `[...document.querySelectorAll('[id*="-option-"]')].find(e => e.innerText.trim() === ${quote(optionText)})`,
      `option ${optionText}`,
    );
    await sleep(800);
  };
  const setNumber = async (finder, what, value) => {
    await click(finder, what);
    if (!(await js(`(() => { const e = ${finder}; e.focus(); e.select(); return document.activeElement === e; })()`)))
      fail(`cannot focus ${what}`);
    await type(value);
    await sleep(300);
  };
  const waitFor = async (expression, what, tries = 40) => {
    for (let attempt = 0; attempt < tries; attempt++) {
      if (await js(expression)) return;
      await sleep(500);
    }
    fail(`${what} (logged out, or a captcha?)`);
  };
  // The rune rows of the price table, as [[rune, amount], ...].
  const priceRows = () =>
    js(`[...document.querySelectorAll('input.offer-amount-input')].map(i => [
         i.closest('.row').querySelector('.offer-table-label').innerText.trim(), Number(i.value)])`);
  const addPrice = async price => {
    await choose(control('Search Runes...'), 'rune search', price.rune.replace(/ Rune$/, ''), price.rune);
    if ((price.amount ?? 1) !== 1)
      await setNumber(
        `[...document.querySelectorAll('input.offer-amount-input')].find(i => i.closest('.row').querySelector('.offer-table-label').innerText.trim() === ${quote(price.rune)})`,
        `${price.rune} amount`,
        price.amount,
      );
  };
  const close = () => ws.close();
  const closeTab = () => fetch(`http://127.0.0.1:${port}/json/close/${tab.id}`);
  return { id: tab.id, js, click, type, key, choose, setNumber, waitFor, priceRows, addPrice, close, closeTab };
}

// "Mal Rune:1" or "Ist Rune:6" -> {rune, amount}
export const parsePrice = text => {
  const [rune, amount = '1'] = text.split(':');
  return { rune: rune.trim().replace(/( Rune)?$/, ' Rune'), amount: Number(amount) };
};
