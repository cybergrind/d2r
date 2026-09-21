#!/usr/bin/env python3
"""pricecheck.py — one-shot Traderie ask band for a catalog item (appraise skill step 6).

  pricecheck.py NAME [NAME...]     search catalog, pull live, recompute the band
  pricecheck.py --id ITEM_ID       skip catalog search
  pricecheck.py --cache            read pricing/raw/traderie/<slug>.json instead of pulling
  pricecheck.py --save             write the pull to pricing/raw/traderie/<slug>.json
  pricecheck.py --pages N          listings pages to pull (default 3 = 150)

Scope filter (client-side, per AGENTS.md): 799 softcore, 800 not-Ladder, 798 PC,
1854 not lord-of-destruction/classic. Effective ask = cheapest OR-group of prices[]
(same group summed). One vote per seller_id (its cheapest). Stackable items
(runes/gems) report per-unit = ask / amount.

Prices are converted with pricing/data/wp-f-ladder.json. Sub-Lem runes, perfect
gems, keys and tokens use the §0/§6.2 approximations and are flagged '~'.
Listings priced in anything else are listed under 'unconverted' and excluded.

Reuses traderie.py's get()/props() — do NOT re-parse properties by hand:
string props live in ['string'], bools in ['bool'], numbers in ['number'];
listing['prices'] and price['group'] can be None.
"""
import json, os, re, statistics, sys
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from traderie import get, props, API

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pricing/
CACHE = os.path.join(ROOT, 'raw', 'traderie')
LADDER = {k.lower(): v['ist'] for k, v in
          json.load(open(os.path.join(ROOT, 'data', 'wp-f-ladder.json'))).items()
          if not k.startswith('_') and isinstance(v, dict) and 'ist' in v}
# §0 currency card / §6.2 per-unit approximations (2026-09-18)
FALLBACK = {'perfect amethyst': 0.10, 'perfect skull': 0.12,
            'key of terror': 0.45, 'key of hate': 0.51, 'key of destruction': 0.49,
            'token of absolution': 0.80}
FALLBACK.update({r: 0.05 for r in
                 ('el', 'eld', 'tir', 'nef', 'eth', 'ith', 'tal', 'ral', 'ort', 'thul',
                  'amn', 'sol', 'shael', 'dol', 'hel', 'io', 'lum', 'ko', 'fal')})
# MS-* misc rows from wp-i (keys, essences, token, shards) at their dated medians; single
# Colossal statues = statue-set median / 5 (they circulate as currency, primer §6.2)
try:
    _wpi = json.load(open(os.path.join(ROOT, 'data', 'wp-i-uniques-misc.json')))
    for _k, _v in _wpi.items():
        if _k.startswith('MS-') and isinstance(_v, dict) and _v.get('median_ist') and _v.get('name'):
            FALLBACK[_v['name'].lower()] = _v['median_ist']
    _ss = _wpi.get('MS-statue-set', {}).get('median_ist')
    if _ss:
        FALLBACK.update({s: round(_ss / 5, 2) for s in
                         ("worusk's end", "madawc's ire", "korlic's pain",
                          "bul-kathos' nightmare", "talic's anguish")})
except Exception:
    pass

def cache_paths(name):
    base = name.lower()
    flat = re.sub(r'-+', '-', re.sub(r"[^a-z0-9]+", '-', base.replace("'", ''))).strip('-')
    hyph = re.sub(r'-+', '-', re.sub(r"[^a-z0-9]+", '-', base)).strip('-')
    return [os.path.join(CACHE, f'{p}{s}.json')
            for s in dict.fromkeys((flat, hyph)) for p in ('', 'wpi-', 'wph-', 'wpg-', 'wpb-')]

def price_ist(pr):
    """-> (ist_value, approx?) or None if not convertible."""
    nm = re.sub(r'\s+rune$', '', pr['name'].lower()).strip()
    q = pr.get('quantity') or 1
    if nm in LADDER: return LADDER[nm] * q, False
    if pr['name'].lower() in FALLBACK: return FALLBACK[pr['name'].lower()] * q, True
    if nm in FALLBACK: return FALLBACK[nm] * q, True
    m = re.match(r'perfect (\w+) gem', pr['name'].lower())
    if m: return FALLBACK.get(f'perfect {m.group(1)}', 0.06) * q, True
    return None

def band(listings, stackable=False):
    in_scope, offer_only, votes, approx_sellers, unconv = [], 0, {}, set(), {}
    for l in listings:
        p = props(l)
        if p.get(799) != 'softcore' or p.get(800) is not False or p.get(798) != 'PC':
            continue
        if str(p.get(1854)).lower() in ('lord of destruction', 'classic (base game)'):
            continue
        in_scope.append(l)
        prices = l.get('prices') or []
        if not prices:
            offer_only += 1
            continue
        groups, approx, ok = {}, False, True
        for pr in prices:
            v = price_ist(pr)
            if v is None:
                unconv[pr['name']] = unconv.get(pr['name'], 0) + 1
                ok = False
                break
            groups[pr.get('group') or 0] = groups.get(pr.get('group') or 0, 0) + v[0]
            approx = approx or v[1]
        if not ok or not groups:
            continue
        eff = min(groups.values())
        if stackable and (l.get('amount') or 1) > 1:
            eff /= l['amount']
        s = l['seller_id']
        if s not in votes or eff < votes[s]:
            votes[s] = eff
            if approx: approx_sellers.add(s)
    vals = sorted(votes.values())
    return in_scope, offer_only, vals, approx_sellers, unconv

def report(name, item_id, itype, listings, cached):
    stackable = itype in ('runes', 'gems')
    in_scope, offer_only, vals, approx, unconv = band(listings, stackable)
    print(f"== {name} (id {item_id}, {itype}) — {'cache' if cached else 'LIVE'} — "
          f"{len(in_scope)}/{len(listings)} in scope (SC/NL/PC/RotW)")
    if not in_scope:
        print('   no in-scope listings'); return
    print(f"   {len(vals)} sellers priced, {offer_only} offer-only/no-price"
          + (f", unconverted price items: {unconv}" if unconv else ''))
    if not vals:
        print('   no convertible asks'); return
    med = statistics.median(vals)
    print(f"   min {vals[0]:.2f} · median {med:.2f} · max {vals[-1]:.2f} Ist"
          + (' (per unit, stack asks ÷ amount)' if stackable else '')
          + (f" · {len(approx)} seller(s) incl. ~approx gem/low-rune prices" if approx else ''))
    print('   distribution:', ' '.join(f'{v:.2f}' for v in vals))

def main(a):
    cached = '--cache' in a; save = '--save' in a
    pages = int(a[a.index('--pages') + 1]) if '--pages' in a else 3
    names = [x for x in a if not x.startswith('--') and x != str(pages)]
    if '--id' in a:
        iid = a[a.index('--id') + 1]
        names = [x for x in names if x != iid]
        items = [(iid, names[0] if names else iid, '?')]
    else:
        if not names: sys.exit(__doc__)
        q = quote(' '.join(names))
        hits = get(f'{API}/items?search={q}').get('items', [])
        norm = lambda s: re.sub(r"[^a-z0-9]", '', s.lower())
        exact = [i for i in hits if norm(i['name']) == norm(' '.join(names))]
        if not exact:
            sys.exit(f'no exact catalog match for "{" ".join(names)}"; candidates: '
                     + ', '.join(f"{i['name']} ({i['id']})" for i in hits[:8]))
        items = [(exact[0]['id'], exact[0]['name'], exact[0]['type'])]
    for iid, name, itype in items:
        path = next((p for p in cache_paths(name) if os.path.exists(p)), cache_paths(name)[0])
        if cached and os.path.exists(path):
            d = json.load(open(path))
            listings = d if isinstance(d, list) else d.get('listings', [])
            was = True
        else:
            listings = []
            for pg in range(pages):
                ls = get(f'{API}/listings?item={iid}&page={pg}').get('listings', [])
                if not ls: break
                listings += ls
            was = False
            if save:
                os.makedirs(CACHE, exist_ok=True)
                json.dump(listings, open(path, 'w'))
                print(f'# saved {len(listings)} listings -> {path}', file=sys.stderr)
        report(name, iid, itype, listings, was)

if __name__ == '__main__':
    main(sys.argv[1:])
