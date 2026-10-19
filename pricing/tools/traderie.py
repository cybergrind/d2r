#!/usr/bin/env python3
"""traderie.py — thin client for the public (no-auth) Traderie D2R JSON API. Verified 2026-09-18.

  traderie.py items TYPE [PAGE]        list catalog items (TYPE: base|runes|runewords|uniques|sets|gems|misc);
                                       24/page, page is 0-based, stops when empty
  traderie.py search TEXT              search catalog by name
  traderie.py props [FILTER]           list property ids (e.g. props Socket)
  traderie.py listings ITEM_ID [N]     fetch up to N pages (50/page) of active sell listings, print one line each
        --scope                        keep only in-scope listings: SC / Non-Ladder / PC / Reign of the Warlock, the
                                       KB's predicate (pricing.knowledge.scope.in_scope; no game version = unknown =
                                       left out). Client-side: the server ignores bool/string prop filters. --sc, --nl
                                       and --pc are the old spelling: any of them = --scope.
        --sockets-min K                server-side numeric filter (prop_402Min)
        --rarity R                     keep only rarity R (unique|set|rare|magic|superior|normal|low quality|crafted)
                                       — property 797, client-side
        --eth / --noeth                keep only ethereal / non-ethereal (property 738)
        --props                        append every non-meta property (affix=value) to each line — needed for jewels,
                                       charms, uniques' rolls
        --json                         dump raw listings JSON instead of lines
  traderie.py runes RUNE [RUNE...]     rune-for-rune asks (in scope only, as --scope): what sellers of e.g. "Ist" ask,
                                       when the ask is paid purely in runes. Use it to build the empirical NL rune
                                       ladder (WP-F) instead of trusting any static table.

Facts verified against the live API on 2026-09-18:
  * GET https://traderie.com/api/diablo2resurrected/items?type=base&page=N
    → {"items":[...24],"version"}; 516 bases total (22 pages), description holds "Max sockets: X"
  * GET https://traderie.com/api/diablo2resurrected/listings?item=ID&page=N
    → {"listings":[...50],"nextPage":N+1}; page is 0-based
  * numeric filters work server-side: prop_402Min=3 (Socketed ≥3). bool/string filters (prop_738=true,
    prop_800=false, prop_799=softcore) are IGNORED → filter client-side.
  * Each listing carries properties[] with property_id: 402 Socketed(n), 738 Ethereal(bool), 797 Rarity(string),
    799 Mode(softcore|hardcore), 800 Ladder(bool: true=Ladder, false=Non Ladder), 798 Platform, 1854 Game version
    ("reign of the warlock" | "lord of destruction" | "classic (base game)"), 425 +x% Enhanced Defense,
    399 +x Defense, 1855 Defense(total), 796 Required Level, 937 % Increase Maximum Durability.
  * Price = listing.prices[]: [{name:"Jah Rune", quantity:18, type:"runes"}, ...]; amount = how many of the item
    the seller has. prices[].group: entries with the SAME group are summed; entries with DIFFERENT groups are
    OR-alternatives (verified WP-F 2026-09-18 on ~1,200 multi-group listings, e.g. [Small Charm g0, 18x Jah g1] =
    "a Small Charm OR 18 Jah"). The effective ask = cheapest alternative.
    For stackable items (runes, gems) the ask appears to be for the WHOLE stack: "Ist x10 | 1x Jah",
    "Ist x2 | 1x Vex" (2026-09-18) match the NL ladder (Jah ≈ 10-12 Ist, Vex ≈ 2.5-3 Ist) only if read per stack.
    Treat as per-stack, divide by amount, and say so in the deliverable.
  * /api/diablo2resurrected/items/ID and any price-history/stats endpoint → 401 "Unauthorized jwt" (needs login)
    — do not rely on them.
  * Catalog types: base (516), runes, runewords, uniques, sets, gems, misc (Jewel id 2732223103, Ring 2390453209,
    Amulet 3209126938, keys/essences/shards), charms (Small 3551993524 / Large 4152254204 / Grand 3779798752),
    crafted (Blood/Caster/Hit Power/Safety x slot). Sunder charms are under uniques (e.g. "The Cold Rupture",
    "Latent Cold Rupture", "Renewed Cold Rupture"). No catalog hit for "Colossal Ancient" jewels (2026-09-18).
  * Magic/rare rolls are numeric properties on the listing (jewel: 510 +ED%, 457 IAS, 441 all res, 437 str,
    416/448 min/max dmg; grand charm: 418 life, class-tree ids e.g. 443 Pala Combat, 516 Sorc Lightning, 408 Traps,
    1547/1548 Warlock Eldritch/Chaos; unique rolls e.g. 1855 Defense, 727 all attributes).
    Jewel has ~31 pages (~1,500 listings) — sample 4-6 pages sorted by updated_at, do not pull everything.
  * prop_1076 is "+x to Dragon Flight (Assassin Only)" — the filter in the user's original URL; it returns
    0 listings for bases. Almost certainly a mis-copied id; intended filter is probably Ethereal (738).
"""

import json
import sys
from pathlib import Path
from urllib.parse import quote


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for runs by path
# The one Traderie HTTP client: retries, and stops on a rate limit, challenge or rejection. It stays in
# pricing/knowledge/refresh.py, whose edits re-validate the published runtime (published_runtime.VALIDATION_CODE).
from pricing.knowledge.refresh import API, fetch_json
from pricing.knowledge.scope import in_scope  # the one scope predicate: 799 softcore, 800 NL, 798 PC, 1854 RotW


def get(url):
    """The JSON answer of one Traderie API request; a failed or refused request ends the tool with the reason."""
    try:
        return fetch_json(url)
    except OSError as error:
        sys.exit(str(error))


def catalog_url(category, page):
    return f'{API}/items?type={category}&page={page}'


def search_url(text):
    return f'{API}/items?search={quote(text)}'


def listings_url(item_id, page, sockets_min=None):
    """Active sell listings, 50 a page from 0; Socketed >= sockets_min is the one filter the server applies."""
    url = f'{API}/listings?item={item_id}&page={page}'
    return url if sockets_min is None else f'{url}&prop_402Min={sockets_min}'


META = {797, 798, 799, 800, 1854, 932}
SCOPE_FLAGS = {'--scope', '--sc', '--nl', '--pc'}


def fmt_price(pr):
    # prices[].group: entries sharing a group are summed ("1 Jah + 1 Lo"); different groups are ALTERNATIVES
    # ("Small Charm OR 18x Jah")
    groups = {}
    for x in pr:
        groups.setdefault(x.get('group', 0), []).append(f'{x.get("quantity", 1)}x {x["name"]}')
    return ' OR '.join(' + '.join(v) for _, v in sorted(groups.items()))


def pv(p):
    return p['number'] if p['type'] == 'number' else (p['bool'] if p['type'] == 'bool' else p['string'])


def props(listing):
    return {p['property_id']: pv(p) for p in listing.get('properties') or []}


def main(a):
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == 'items':
        typ = a[1]
        pages = [int(a[2])] if len(a) > 2 else range(60)
        for pg in pages:
            it = get(catalog_url(typ, pg)).get('items', [])
            if not it:
                break
            for i in it:
                print(i['id'], '|', i['name'], '|', (i.get('description') or '').replace('\n', ' ')[:160])
    elif cmd == 'search':
        for i in get(search_url(' '.join(a[1:]))).get('items', []):
            print(i['id'], '|', i['type'], '|', i['name'])
    elif cmd == 'props':
        f = a[1].lower() if len(a) > 1 else ''
        for p in get(f'{API}/properties')['properties']:
            if f in p['name'].lower():
                print(p['id'], '|', p['type'], '|', p['name'], '|', p.get('options') or '')
    elif cmd == 'listings':
        iid = a[1]
        n = int(a[2]) if len(a) > 2 and a[2].isdigit() else 3
        sockets_min = a[a.index('--sockets-min') + 1] if '--sockets-min' in a else None
        out = []
        for pg in range(n):
            d = get(listings_url(iid, pg, sockets_min))
            ls = d.get('listings', [])
            if not ls:
                break
            out += ls
        if SCOPE_FLAGS & set(a):
            out = [listing for listing in out if in_scope(listing)]
        if '--rarity' in a:
            rarity = a[a.index('--rarity') + 1].lower()
            out = [listing for listing in out if (props(listing).get(797) or '').lower() == rarity]
        if '--eth' in a:
            out = [listing for listing in out if props(listing).get(738) is True]
        if '--noeth' in a:
            out = [listing for listing in out if not props(listing).get(738)]
        if '--json' in a:
            print(json.dumps(out))
            return
        for listing in out:
            p = props(listing)
            price = fmt_price(listing.get('prices') or []) or ('make offer' if listing.get('make_offer') else '?')
            scope = f'{p.get(799)}/{"L" if p.get(800) else "NL"}/{p.get(798)}'
            rolls = f'sock={p.get(402)} eth={p.get(738)} ed={p.get(425)} def={p.get(1855)}'
            line = (
                f'{listing["id"]} | {listing["updated_at"][:10]} | {scope} | {p.get(797)} | {rolls}'
                f' | x{listing["amount"]} | {price}'
            )
            if '--props' in a:
                line += ' | ' + '; '.join(
                    f'{pp["property"].replace("{{value}}", "x")}={pv(pp)}'
                    for pp in (listing.get('properties') or [])
                    if pp['property_id'] not in META
                )
            print(line)
        print(f'# {len(out)} listings', file=sys.stderr)
    elif cmd == 'runes':
        # rune-for-rune asks: prints "1 Ist asked as: 1x Gul + 1x Pul" lines, SC/NL/PC only, asks paid purely in runes
        for name in a[1:]:
            hits = [
                i
                for i in get(search_url(f'{name} rune')).get('items', [])
                if i['type'] == 'runes' and i['name'].lower() == f'{name.lower()} rune'
            ]
            if not hits:
                print(f'# no rune item for {name}')
                continue
            iid = hits[0]['id']
            out = []
            for pg in range(2):
                ls = get(listings_url(iid, pg)).get('listings', [])
                if not ls:
                    break
                out += ls
            for listing in out:
                if not in_scope(listing):
                    continue
                pr = listing.get('prices') or []
                if not pr or any(x.get('type') != 'runes' for x in pr):
                    continue
                amount = listing['amount']
                day, ask = listing['updated_at'][:10], fmt_price(pr)
                print(f'{name} x{amount} | {day} | stack ask: {ask}  (per-unit = divide by {amount})')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
