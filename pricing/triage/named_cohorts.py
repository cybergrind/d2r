"""Named bands: preserve exclusive identities, then apply supported roll splits."""

import json
from collections import defaultdict
from functools import lru_cache
from typing import Any

from pricing.triage.cohort_splits import numeric_partition, worthwhile


FACETS = ('socket_variant', 'base_code', 'roll_bucket')
# Exclusive native choices in appraisal-definitions.json are identities, not
# optional statistical roll splits. Unknown choices cannot use the pooled band.
IDENTITY_FACETS = {
    'hellfire torch': 'torch_class',
    'wraithstep': 'wraithstep_tree',
    'opalvein': 'opalvein_bonus',
    "ormus' robes": 'ormus_skill',
    'rainbow facet': 'facet_roll',
}
# Colossal Ancient jewels: (enemy -res market property, native stat), (skill damage property, native stat).
# uniqueitems.json pierce-*/extra-* 5-10; ids verified in metadata stats 2026-10-22. Protector's Stone's second
# stat is ED (not captured on the unique path) and its pierce 366 has no market projection, hence the native key.
COLOSSAL_RES = {
    "defender's fire": (('735', '333:0'), ('750', '329:0')),
    "defender's bile": (('723', '336:0'), ('783', '332:0')),
    "protector's frost": (('609', '335:0'), ('747', '331:0')),
    "guardian's thunder": (('736', '334:0'), ('743', '330:0')),
    "guardian's light": (('1877', '358:0'), ('1879', '357:0')),
    "protector's stone": (('1881', '366:0'), None),
}
IDENTITY_FACETS |= dict.fromkeys(COLOSSAL_RES, 'colossal_res')
# The price-driving roll regions, lowest first (rca/2026-10-22/jewel-verify-G5.md §2-3). A region with fewer
# than three sellers, or an unreadable roll, takes the next-lower supported region: never no price.
REGIONS = {
    'facet_roll': ('3-roll', '5/3-4/4', '5/4', '5/5'),
    'colossal_res': ('5-7', '8-9', '10', '10/10'),
}
# Rainbow Facet: element and trigger split only the 5/5 copies (15-23 sellers each); below, the fills agree
# across variants. An undecoded trigger prices from the pooled 5/5 band.
SCOPED_FACETS = {'rainbow_variant': ('facet_roll', '5/5')}


def roll_value(item, prop, native):
    value = item.get('properties', {}).get(prop)
    if value is None:
        value = item.get('native_rolls', {}).get(native)
    return value if type(value) in (int, float) else None


def facet_roll(item):
    """'5/5' | '5/4' | '5/3-4/4' | '3-roll' from the one element's (skill damage, -res) pair, both 3-5."""
    from pricing.triage.facet_identity import variants

    properties = item.get('properties', {})
    pairs = {props for _, props, _, _ in variants()}
    found = [
        (properties.get(mastery), properties.get(pierce))
        for mastery, pierce in pairs
        if properties.get(mastery) not in (None, 0) or properties.get(pierce) not in (None, 0)
    ]
    if len(found) != 1 or not all(type(v) in (int, float) and 3 <= v <= 5 for v in found[0]):
        return None
    high, low = sorted(found[0], reverse=True)
    if (high, low) == (5, 5):
        return '5/5'
    if (high, low) == (5, 4):
        return '5/4'
    return '5/3-4/4' if high == 5 or (high, low) == (4, 4) else '3-roll'


def colossal_res(item):
    """'5-7' | '8-9' | '10' | '10/10' (-10 with +10 skill damage) from a Colossal jewel's -res roll."""
    stats = COLOSSAL_RES.get(str(item.get('name', '')).casefold())
    if not stats:
        return None
    pierce = roll_value(item, *stats[0])
    if pierce is None or not 5 <= pierce <= 10:
        return None
    if pierce < 8:
        return '5-7'
    if pierce < 10:
        return '8-9'
    mastery = roll_value(item, *stats[1]) if stats[1] else None
    return '10/10' if mastery == 10 else '10'


IDENTITY_PROPERTIES = {
    'torch_class': dict.fromkeys(('453', '514', '498', '442', '403', '488', '519', '1862'), 3),
    'wraithstep_tree': dict.fromkeys(('1546', '1547', '1548'), 1),
    'opalvein_bonus': dict.fromkeys(('1879', '510', '750', '747', '743', '783')),
}


@lru_cache(maxsize=1)
def ormus_skills():
    """Use the native random-skill interval, not all Sorceress skill properties."""
    from inventory_tracking.items.metadata import metadata
    from pricing.knowledge.assessment.adapters.market_projection import market_properties

    definition = next(d for d in metadata()['identities']['unique'].values() if d['name'] == "Ormus' Robes")
    game = definition['game_definition']
    slot = next(i for i in range(1, 13) if game.get(f'prop{i}') == 'skill-rand')
    projection = market_properties()
    return {
        projection[key]: game[f'par{slot}']
        for skill in range(game[f'min{slot}'], game[f'max{slot}'] + 1)
        if (key := f'107:{skill}') in projection
    }


def identity_facet(item):
    if item.get('category') == 'uniques':
        return IDENTITY_FACETS.get(str(item.get('name', '')).casefold())
    return None


def value(item, facet, rules):
    from pricing.triage.engine import matches

    if facet == 'rainbow_variant':
        from pricing.triage.facet_identity import identity

        return identity(item)
    if facet == 'facet_roll':
        return facet_roll(item)
    if facet == 'colossal_res':
        return colossal_res(item)
    if facet in IDENTITY_PROPERTIES or facet == 'ormus_skill':
        properties = item.get('properties', {})
        choices = ormus_skills() if facet == 'ormus_skill' else IDENTITY_PROPERTIES[facet]
        present = [p for p in choices if properties.get(p) not in (None, 0)]
        if len(present) != 1:
            return None
        prop = present[0]
        observed, exact = properties[prop], choices[prop]
        if type(observed) not in (int, float) or observed <= 0 or (exact is not None and observed != exact):
            return None
        return prop
    if facet.startswith('property:'):
        return item.get('properties', {}).get(facet[9:])
    if facet.startswith('base_modifier:'):
        modifiers = item.get('base_modifiers')
        return modifiers.get(facet[14:], 0) if isinstance(modifiers, dict) else None
    if facet == 'socket_variant':
        return [item.get('sockets'), item.get('socket_contents')]
    if facet == 'roll_bucket':
        properties = {p for rule in rules for p in rule.get('properties', {})}
        if properties and not any(p in item.get('properties', {}) for p in properties):
            return None
        return next((r['bucket'] for r in rules if r.get('bucket') and matches(item, r)), 'other')
    return item.get(facet)


def token(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def compile_named(category, name, rows, rules, *, facets=FACETS, bucket='name'):
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import band_for
    from pricing.triage.engine import matches

    rules = [
        r
        for r in rules
        if matches({'category': category, 'name': name}, {k: r[k] for k in ('category', 'name') if k in r})
        and r.get('bucket')
    ]
    if category in ('uniques', 'sets'):
        # Socket contents have their own value; they cannot price the bare item.
        rows = [row for row in rows if row.get('socket_contents') != 'filled']
    identity = identity_facet({'category': category, 'name': name})
    mandatory = (identity,) if identity else ()
    if identity == 'facet_roll':
        mandatory, facets = ('facet_roll', 'rainbow_variant'), ('rainbow_variant',)
    facets = (*mandatory[:1], *facets)
    prepared = [(row, from_listing(row)) for row in rows]
    bands = []

    def node(members, facets, path):
        band = band_for(category, name, [r for r, _ in members])
        band['bucket'] = bucket + '|cohort:' + token(path)
        band['cohort_depth'] = len(path) - 1
        result: dict[str, Any] = {'band': band}
        for index, facet in enumerate(facets):
            groups = defaultdict(list)
            for row, item in members:
                groups[token(value(item, facet, rules))].append((row, item))
            if facet not in mandatory and not worthwhile([[r for r, _ in group] for group in groups.values()]):
                split = (
                    numeric_partition(members, [value(item, facet, rules) for _, item in members])
                    if (facet.startswith(('property:', 'base_modifier:')))
                    else None
                )
                if split is None:
                    continue
                groups = split['groups']
                result.update(split_at=split['split_at'], minimum=split['minimum'])
            result.update(
                facet=facet,
                children={
                    key: node(
                        group,
                        tuple(
                            f
                            for f in facets[index if 'split_at' in result else index + 1 :]
                            if f not in SCOPED_FACETS or SCOPED_FACETS[f] == (facet, json.loads(key))
                        ),
                        [*path, [facet, key]],
                    )
                    for key, group in sorted(groups.items())
                },
            )
            break
        bands.append(band)
        return result

    ethereal = defaultdict(list)
    for row, item in prepared:
        ethereal[token(item.get('ethereal'))].append((row, item))
    tree = {eth: node(group, facets, [['ethereal', eth]]) for eth, group in sorted(ethereal.items())}
    reference = band_for(category, name, rows)
    from pricing.triage.named_fallback import compile_bands

    fallback = compile_bands(category, name, 'name', rows, 1)
    summaries = fallback[0]['variant_prices'] if fallback else []
    reference.update(bucket=bucket, named_cohorts=tree, cohort_rules=rules, variant_prices=summaries)
    if mandatory:
        reference['required_identity'] = list(mandatory[:1])
    return [reference, *bands]


def region_priced(category, name):
    """True when a roll-region facet prices this name; a roll model must not override its regions."""
    return identity_facet({'category': category, 'name': name}) in REGIONS


def region_band(node, facet, observed):
    """The observed region's band, else the next-lower then the next-higher one with three sellers."""
    order = REGIONS[facet]
    start = order.index(observed) if observed in order else 0
    for region in (*order[start::-1], *order[start + 1 :]):
        child = node['children'].get(token(region))
        if child is not None and child['band'].get('sellers', 0) >= 3 and child['band'].get('q1_ist') is not None:
            return child
    return None


def lookup(item, reference):
    identity = identity_facet(item)
    if identity and reference.get('required_identity') != [identity]:
        return None
    filled = item.get('category') in ('uniques', 'sets') and item.get('socket_contents') == 'filled'
    if filled:
        # Native socket counts (for example Tomb Reaver) retain their empty-socket band.
        bare_sockets = 0 if any(v['sockets'] == 0 for v in reference['variant_prices']) else item.get('sockets')
        item = item | {'sockets': bare_sockets, 'socket_contents': 'empty'}
    tree = reference['named_cohorts']
    node = tree.get(token(item.get('ethereal')))
    if node is None:
        return None
    while 'children' in node:
        facet = node['facet']
        if filled and facet == 'roll_bucket':
            # Captured totals include inserts; do not buy a roll premium from them.
            return node['band']
        observed = value(item, facet, reference['cohort_rules'])
        if facet in REGIONS:
            child = region_band(node, facet, observed)
            if child is None:
                return None
            if token(observed) not in node['children'] or child is not node['children'][token(observed)]:
                return child['band']  # a fallback region prices the item; its sub-splits are another roll's
            node = child
            continue
        if facet in SCOPED_FACETS:
            child = node['children'].get(token(observed)) if observed is not None else None
            if child is None or child['band'].get('sellers', 0) < 3 or child['band'].get('q1_ist') is None:
                return node['band']  # undecoded trigger or a thin variant: the pooled 5/5 band
            node = child
            continue
        if observed is None or (facet == 'socket_variant' and any(v in (None, 'unknown') for v in observed)):
            return None
        child = node['children'].get(token(observed))
        if child is None and facet.startswith(('property:', 'base_modifier:')):
            points = [(json.loads(k), n) for k, n in node['children'].items()]
            lower = [
                (v, n)
                for v, n in points
                if type(v) in (int, float) and type(observed) in (int, float) and v <= observed
            ]
            if not lower:
                return None
            child = max(lower, key=lambda pair: pair[0])[1]
        if child is None and facet in reference.get('required_identity', []):
            return None
        if child is None:
            # Known but unlisted variant uses the supported parent approximation.
            return node['band']
        node = child
    return node['band']
