"""Supported named-item fallback cohorts; ethereal never borrows the other side."""

import json
from collections import defaultdict


NAMED = {'uniques', 'sets'}


def key(bucket, ethereal, base=None, *, keep_base=False):
    values = [bucket, ethereal] + ([base] if keep_base else [])
    return 'named-fallback:' + json.dumps(values, separators=(',', ':'))


def compile_bands(category, name, bucket, rows, amount):
    from pricing.triage.bands import band_for

    if category not in NAMED | {'runewords'} or amount != 1:
        return []
    groups, variants = defaultdict(list), defaultdict(list)
    for row in rows:
        eth, base = row.get('ethereal'), row.get('base_code')
        groups[key(bucket, eth)].append(row)
        groups[key(bucket, eth, base, keep_base=True)].append(row)
        variants[eth, base, row.get('sockets'), row.get('socket_contents')].append(row)
    summaries = [
        dict(zip(('ethereal', 'base_code', 'sockets', 'socket_contents'), facets, strict=True))
        | {k: band[k] for k in ('q1_ist', 'sellers')}
        for facets, members in variants.items()
        if (band := band_for(category, name, members))['q1_ist'] is not None
    ]
    return [
        band_for(category, name, members) | {'bucket': name_key, 'variant_prices': summaries}
        for name_key, members in groups.items()
    ]


def supported(band):
    return band and band.get('sellers', 0) >= 3 and band.get('q1_ist') is not None


def protects_variant(item, band, keep_ist):
    """A cheap pooled price cannot dispose of a known or possibly premium variant."""
    if (
        band['q1_ist'] is None
        or band['q1_ist'] >= keep_ist
        or (item.get('ethereal') is False and item.get('sockets') == 0)
    ):
        return False
    for variant in band.get('variant_prices', []):
        if variant['q1_ist'] < keep_ist:
            continue
        if item.get('ethereal') is not None and variant['ethereal'] is not item['ethereal']:
            continue
        if item.get('base_code') is not None and variant['base_code'] not in (None, item['base_code']):
            continue
        if item.get('sockets') is not None and variant['sockets'] not in (None, item['sockets']):
            continue
        return True
    return False


def missing_dependent_facet(item, band):
    variants = [
        v for v in band.get('variant_prices', []) if item.get('ethereal') is None or v['ethereal'] is item['ethereal']
    ]
    for facet in ('base_code', 'sockets', 'socket_contents'):
        if item.get(facet) not in (None, 'unknown'):
            continue
        priced = [v for v in variants if v.get(facet) not in (None, 'unknown') and v['sellers'] >= 3]
        if len({v[facet] for v in priced}) > 1:
            prices = [v['q1_ist'] for v in priced]
            if min(prices) > 0 and max(prices) >= 1.5 * min(prices):
                return True
    return False


def lookup(item, tables, candidates, *, allow_name):
    if item.get('category') not in NAMED:
        return None
    category, name = item['category'], item['name'].casefold()
    ethereal = item.get('ethereal')
    keep = tables['rules']['keep_ist']
    bands = tables['bands']
    buckets = list(dict.fromkeys([*candidates, *(['name'] if allow_name else [])]))
    for bucket in buckets:
        if type(ethereal) is not bool:
            continue
        for code, keep_base in ((item.get('base_code'), True), (None, False)):
            band = bands.get((category, name, key(bucket, ethereal, code, keep_base=keep_base)))
            if supported(band) and not protects_variant(item, band, keep) and not missing_dependent_facet(item, band):
                return band
    # Name-only evidence can establish a low floor, never a positive price
    # across unknown or different ethereal status.
    pooled = bands.get((category, name, 'name'))
    if supported(pooled) and pooled['q1_ist'] < keep:
        variants = pooled.get('variant_prices') or [
            v
            for eth in (False, True, None)
            for v in (bands.get((category, name, key('name', eth))) or {}).get('variant_prices', [])
        ]
        candidate = pooled | {'variant_prices': variants}
        if not protects_variant(item, candidate, keep) and not missing_dependent_facet(item, candidate):
            return pooled
    return None
