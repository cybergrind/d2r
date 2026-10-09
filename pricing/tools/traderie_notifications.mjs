#!/usr/bin/env node
// Print the player's Traderie notifications as JSON lines, read through their own browser.
//
//   node pricing/tools/traderie_notifications.mjs [--watch] [--interval 60] [--port 8333]
//
// It opens one hidden tab (not in the tab strip, closed by the browser when this process exits),
// loads Traderie there and reads the answer to the site's own notifications request. The login
// token is never read: the site sends the request itself. In that tab everything outside Traderie
// (ads, trackers) and all images are blocked. Each line is
//   {"notifications": [{id, type, title, message, created_at, read, listing_id}]}   or   {"error": "..."}
// Without --watch it prints one line and exits; with it, one line per reload and per refresh the
// site makes by itself, until killed. `serve` runs it for the HUD (inventory_tracking/hud/traderie.py).
const args = process.argv.slice(2);
const option = (name, fallback) => (args.includes(name) ? args[args.indexOf(name) + 1] : fallback);
const port = option('--port', '8333');
const interval = Number(option('--interval', '60')) * 1000;
const watch = args.includes('--watch');
const SITE = 'https://traderie.com/diablo2resurrected';
const OWN_HOSTS = /(^|\.)(traderie\.com|nookazon\.com|nookazon-socket\.herokuapp\.com)$/;
const NOTIFICATIONS = /\/api\/diablo2resurrected\/notifications(\?|$)/;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const emit = line => console.log(JSON.stringify(line));

async function session() {
  const version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  const ws = new WebSocket(version.webSocketDebuggerUrl);
  const closed = new Promise(resolve => {
    ws.addEventListener('close', resolve);
    ws.addEventListener('error', resolve);
  });
  await Promise.race([new Promise(resolve => ws.addEventListener('open', resolve)), closed]);
  if (ws.readyState !== WebSocket.OPEN) throw new Error('the DevTools socket did not open');
  let nextId = 0;
  const pending = new Map();
  const send = (method, params = {}, sessionId) =>
    new Promise(resolve => {
      pending.set(++nextId, resolve);
      ws.send(JSON.stringify({ id: nextId, method, params, sessionId }));
    });
  const wanted = new Map(); // request id -> HTTP status of a notifications answer
  let answered = null;
  let tab = null;
  ws.addEventListener('message', async event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      pending.get(message.id)?.(message);
      pending.delete(message.id);
    } else if (message.method === 'Fetch.requestPaused') {
      const { requestId, request, resourceType } = message.params;
      const own = OWN_HOSTS.test(new URL(request.url).hostname) && resourceType !== 'Image' && resourceType !== 'Media';
      if (own) send('Fetch.continueRequest', { requestId }, tab);
      else send('Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' }, tab);
    } else if (message.method === 'Network.responseReceived' && NOTIFICATIONS.test(message.params.response.url)) {
      wanted.set(message.params.requestId, message.params.response.status);
    } else if (message.method === 'Network.loadingFinished' && wanted.has(message.params.requestId)) {
      const status = wanted.get(message.params.requestId);
      wanted.delete(message.params.requestId);
      const body = await send('Network.getResponseBody', { requestId: message.params.requestId }, tab);
      try {
        if (status === 401) throw new Error('logged out of Traderie in this browser');
        if (status !== 200) throw new Error(`Traderie answered ${status}`);
        const list = JSON.parse(body.result.body).notifications;
        emit({
          notifications: list.map(n => ({
            id: n.id,
            type: n.type,
            title: n.title,
            message: n.message,
            created_at: n.created_at,
            read: n.read === true,
            listing_id: n.data?.listing_id ?? null,
          })),
        });
      } catch (error) {
        emit({ error: error.message });
      }
      answered?.();
    }
  });
  const created = await send('Target.createTarget', { url: 'about:blank', hidden: true, background: true });
  if (!created.result) throw new Error('no hidden tab: ' + (created.error?.message ?? 'unknown'));
  const attached = await send('Target.attachToTarget', { targetId: created.result.targetId, flatten: true });
  tab = attached.result.sessionId;
  await send('Network.enable', {}, tab);
  await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] }, tab);
  await send('Page.enable', {}, tab);
  // One load of the site, and whether its notifications request was answered within 30 s.
  const load = async () => {
    const got = new Promise(resolve => (answered = () => resolve(true)));
    await send('Page.navigate', { url: SITE }, tab);
    if (!(await Promise.race([got, sleep(30000).then(() => false), closed.then(() => false)])))
      emit({ error: 'Traderie did not ask for notifications (logged out, or a captcha?)' });
  };
  return { load, closed, close: () => ws.close() };
}

for (;;) {
  let tab = null;
  try {
    tab = await session();
    for (;;) {
      await tab.load();
      if (!watch) break;
      if (await Promise.race([sleep(interval).then(() => false), tab.closed.then(() => true)]))
        throw new Error('the browser closed the DevTools socket');
    }
  } catch (error) {
    emit({ error: `browser on port ${port}: ${error.cause?.code ?? error.message}` });
  }
  tab?.close();
  if (!watch) break;
  await sleep(interval);
}
