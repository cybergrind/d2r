"""Build pricing/data/charm-evidence.json (pricing/triage/charm_fills.py): what shimmering charms sold for, per facet.

A facet is a charm size, its all-res roll and its one companion affix with its value (`charm_fills.shape`):
'sc/5/418:20' is a Small Charm with 5 all res and +20 life. The trades are Traderie's Recent Trades (accepted and
completed offers) read through the player's browser by pricing/tools/traderie_trades.mjs (2026-10-24: Small Charm
pages filtered server-side to all res 5 and 3-4, Large Charm unfiltered, Grand Charm all res 1+), PC/SC/NL/RotW by
the listing's own properties, one row per offer id, since FILLS_SINCE. The paid price is the counter-offer if any,
else the listing's price, an OR-group its cheapest, in Ist by pricing/data/wp-f-ladder.json; a trade paid in anything
else (charms, gems, keys) is kept unpriced. A listing of more than one charm is left out.

The raw pulls (git-ignored) are read here only: the built file is the runtime's.

Run: uv run --offline python -m pricing.tools.build_charm_evidence
"""

import argparse
import glob
import json
import statistics
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from pricing.knowledge.market import convert_groups
from pricing.knowledge.refresh import atomic_json
from pricing.triage.charm_fills import EVIDENCE_FILE, facet_key, shape


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'pricing' / 'raw' / 'traderie'
FILL_DIRS = ('recent-20261024-charms',)
FILLS_SINCE = '2026-09-15'
LADDER = ROOT / 'pricing' / 'data' / 'wp-f-ladder.json'
SCOPE = ('PC', 'softcore', False, 'reign of the warlock')  # platform 798, mode 799, ladder 800, version 1854
NAMES = frozenset(('Small Charm', 'Large Charm', 'Grand Charm'))


def currencies() -> dict[str, float]:
    ladder = json.loads(LADDER.read_text())
    return {name.lower(): row['ist'] for name, row in ladder.items() if isinstance(row, dict) and 'ist' in row}


def properties(listing: Mapping[str, Any]) -> dict[str, Any]:
    found = {}
    for prop in listing.get('properties') or ():
        value = prop.get('number')
        if value is None:
            value = prop.get('string') if prop.get('string') is not None else prop.get('bool')
        found[str(prop['property_id'])] = value
    return found


def offers(dirs: Iterable[str]) -> Iterator[Mapping[str, Any]]:
    """Every offer of the pulls, both file shapes (a page {offers}, a product load {api: [{url, body}]})."""
    for directory in dirs:
        for path in sorted(glob.glob(str(RAW / directory / '*.json'))):
            doc = json.loads(Path(path).read_text())
            answers = doc.get('api', []) if 'api' in doc else [{'url': '/offers?', 'body': json.dumps(doc)}]
            for answer in answers:
                if '/offers?' not in answer.get('url', '') or not answer.get('body'):
                    continue
                try:
                    yield from json.loads(answer['body'], strict=False).get('offers') or ()
                except ValueError:
                    continue  # a refused request (an error page, 'Unauthorized jwt'): no trades


def paid(offer: Mapping[str, Any], listing: Mapping[str, Any], ladder: Mapping[str, float]) -> tuple[float | None, str]:
    """(Ist paid or None, the price as text): the counter-offer if any, else the listing's."""
    prices = offer.get('prices') or listing.get('prices') or []
    ist, _ = convert_groups(prices, ladder)
    groups: dict[Any, list[str]] = {}
    for price in prices:
        groups.setdefault(price.get('group') or 0, []).append(f'{price.get("quantity", 1)} {price.get("name")}')
    return ist, ' OR '.join(' + '.join(parts) for parts in groups.values())


def trades(dirs: Iterable[str] = FILL_DIRS, since: str = FILLS_SINCE) -> dict[str, list[dict[str, Any]]]:
    """The in-scope single-charm trades by facet key, newest first."""
    ladder = currencies()
    seen: set[Any] = set()
    found: dict[str, list[dict[str, Any]]] = {}
    for offer in offers(dirs):
        listing = offer.get('listing') or {}
        name = (listing.get('item') or {}).get('name')
        if offer.get('id') in seen or name not in NAMES or not (offer.get('accepted') and offer.get('completed')):
            continue
        props = properties(listing)
        if tuple(props.get(p) for p in ('798', '799', '800', '1854')) != SCOPE or listing.get('amount') not in (
            1,
            None,
        ):
            continue
        seen.add(offer.get('id'))
        when = (offer.get('updated_at') or '')[:10]
        shaped = shape(name, {k: v for k, v in props.items() if type(v) in (int, float) or type(v) is bool})
        if not when or when < since or shaped is None:
            continue
        ist, text = paid(offer, listing, ladder)
        lister = str((listing.get('seller') or {}).get('id'))
        seller, buyer = (
            (lister, str(offer.get('user_id'))) if listing.get('selling', True) else (offer.get('user_id'), lister)
        )
        found.setdefault(facet_key(*shaped), []).append({
            'date': when,
            'ist': round(ist, 3) if ist is not None else None,
            'paid': text,
            'seller': str(seller),
            'buyer': str(buyer),
            'offer': offer.get('id'),
        })  # fmt: skip
    for rows in found.values():
        rows.sort(key=lambda row: (row['date'], str(row['offer'])), reverse=True)
    return found


def summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts and q1/median of a facet's priced trades, for a reader (the runtime recomputes from `trades`)."""
    priced = sorted(row['ist'] for row in rows if row['ist'] is not None)
    found: dict[str, Any] = {'trades_n': len(rows), 'priced_n': len(priced)}
    if priced:
        q1 = priced[0] if len(priced) < 2 else statistics.quantiles(priced, n=4, method='inclusive')[0]
        found |= {'q1_ist': round(q1, 2), 'median_ist': round(statistics.median(priced), 2),
                  'dates': [rows[-1]['date'], rows[0]['date']]}  # fmt: skip
    return found


def build(dirs: Iterable[str] = FILL_DIRS, since: str = FILLS_SINCE) -> dict[str, Any]:
    found = trades(dirs, since)
    return {
        'schema_version': 1,
        'sources': {
            'fills': 'Traderie Recent Trades (accepted and completed offers), PC/SC/NL/RotW, via the player browser',
            'dirs': [f'pricing/raw/traderie/{d}' for d in dirs],
            'since': since,
            'ladder': 'pricing/data/wp-f-ladder.json ist',
        },
        'facets': {key: summary(rows) | {'trades': rows} for key, rows in sorted(found.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=EVIDENCE_FILE)
    args = parser.parse_args(argv)
    document = build()
    atomic_json(args.out, document)
    facets = document['facets']
    print(f'{args.out}: {len(facets)} facets, {sum(f["trades_n"] for f in facets.values())} trades')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
