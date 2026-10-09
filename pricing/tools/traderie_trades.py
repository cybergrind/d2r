#!/usr/bin/env python3
"""Summarise Traderie Recent Trades saved by traderie_trades.mjs: trades per day, what buyers paid (Ist via the
dated ladder pricing/data/wp-f-ladder.json), by rarity, with sockets and Warlock staff-mods.

  python3 pricing/tools/traderie_trades.py [pricing/raw/traderie/recent-<date>/<slug>.json ...]

A trade = an offer that was accepted and completed on the site. An offer without its own prices took the
listing price; one with prices was a counter-offer. "Or" price groups take the cheapest. Prices in items the
ladder lacks stay unpriced. Files that still hold the page's other API answers are stripped to the trade ones.
"""

import collections
import datetime
import glob
import json
import statistics
import sys
from pathlib import Path


KEEP = ('/offers?', '/items/prices?')
LOW_RUNES = {'Hel': 0.143, 'Sol': 0.059, 'Ko': 0.2, 'Fal': 0.247, 'Lum': 0.08, 'Io': 0.114, 'Shael': 0.016}
PERFECT_GEM = 0.061  # wp-i _meta, 2026-09-18
STAFFMOD_IDS = range(1550, 1601)
WARLOCK_SKILLS, RARITY, SOCKETS, ETHEREAL = 1862, 797, 402, 738


def load_json(path):
    with open(path) as handle:
        return json.load(handle)


LADDER = {k: v['ist'] for k, v in load_json('pricing/data/wp-f-ladder.json').items() if k != '_meta'} | LOW_RUNES
PROPERTIES = load_json('pricing/data/appraisal-properties.json')['properties']


def label(pid):
    return (PROPERTIES.get(str(pid), {}).get('labels') or [f'#{pid}'])[0].replace('{{value}}', 'x')


def ist(prices):
    """Ist value of a price list; OR-groups take the cheapest; None when empty or in items the ladder lacks."""
    groups = {}
    for p in prices or []:
        name = p.get('name') or ''
        value = LADDER.get(name.replace(' Rune', ''))
        if value is None and 'Perfect' in name:
            value = PERFECT_GEM
        if value is None:
            return None
        group = p.get('group') or 0
        groups[group] = groups.get(group, 0) + value * (p.get('quantity') or 1)
    return min(groups.values()) if groups else None


def paid_for(offer):
    """A counter-offer carries its own prices; an accepted listing price leaves them null."""
    source = offer.get('prices') or (offer.get('listing') or {}).get('prices') or []
    text = ' + '.join(f'{p.get("quantity") or 1} {p.get("name")}' for p in source) or 'make offer'
    return ist(source), text + ('' if offer.get('prices') else ' (listing price)')


def listing_props(listing):
    out = {}
    for p in listing.get('properties') or []:
        value = p.get('number')
        if value is None:
            value = p.get('string') if p.get('string') is not None else p.get('bool')
        out[p.get('property_id')] = value
    return out


def strip(path, document):
    if all(any(k in a['url'] for k in KEEP) for a in document['api']):
        return
    document['api'] = [a for a in document['api'] if any(k in a['url'] for k in KEEP)]
    document.pop('text', None)
    Path(path).write_text(json.dumps(document, indent=1))


def trades(document, now):
    offers = {}
    for answer in document['api']:
        if '/offers?' in answer['url'] and answer['body']:
            for offer in json.loads(answer['body'], strict=False).get('offers', []):
                offers[offer['id']] = offer
    rows = []
    for offer in sorted(offers.values(), key=lambda o: o['updated_at'], reverse=True):
        props = listing_props(offer.get('listing') or {})
        paid, paid_text = paid_for(offer)
        closed = datetime.datetime.fromisoformat(offer['updated_at'].replace('Z', '+00:00'))
        rows.append(
            {
                'when': offer['updated_at'][:10],
                'days_ago': (now - closed).days,
                'paid': paid,
                'paid_text': paid_text,
                'rarity': props.get(RARITY),
                'sockets': props.get(SOCKETS),
                'eth': props.get(ETHEREAL),
                'mods': {label(k): v for k, v in props.items() if k in STAFFMOD_IDS or k == WARLOCK_SKILLS},
            }
        )
    return rows


def report(name, rows):
    if not rows:
        print(f'== {name}: no trades')
        return
    span = max(rows[-1]['days_ago'], 1)
    rarities = dict(collections.Counter(r['rarity'] for r in rows))
    rate = f'~{len(rows) / span:.1f}/day'
    print(f'== {name}: {len(rows)} trades (newest page), oldest {rows[-1]["when"]} → {rate}; {rarities}')
    for rarity in ('normal', 'superior', 'magic', 'rare', 'unique', 'set'):
        sub = [r for r in rows if r['rarity'] == rarity]
        if not sub:
            continue
        paid = sorted(r['paid'] for r in sub if r['paid'] is not None)
        sockets = dict(collections.Counter(r['sockets'] for r in sub))
        top = collections.Counter(k for r in sub for k, v in r['mods'].items() if (v or 0) >= 3).most_common(2)
        band = 'none priced'
        if paid:
            band = f'min {paid[0]:.2f} median {statistics.median(paid):.2f} max {paid[-1]:.2f} ({len(paid)} priced)'
        print(f'   {rarity:9} {len(sub):2} trades, paid Ist: {band}; sockets {sockets}; +3 mods {top}')
    for r in rows[:6]:
        eth = 'eth' if r['eth'] else ''
        mods = json.dumps(r['mods'])[:90]
        print(f'      {r["when"]} {r["rarity"]!s:8} {r["paid_text"]:30} sockets {r["sockets"]} {eth} {mods}')


def main(paths):
    now = datetime.datetime.now(datetime.UTC)
    for path in paths or sorted(glob.glob('pricing/raw/traderie/recent-*/*.json')):
        document = load_json(path)
        strip(path, document)
        report(Path(path).stem, trades(document, now))


if __name__ == '__main__':
    main(sys.argv[1:])
