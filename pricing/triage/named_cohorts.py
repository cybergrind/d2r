"""Named bands: preserve exclusive identities, then apply supported roll splits."""

import json
from collections import defaultdict
from functools import lru_cache

from pricing.triage.cohort_splits import numeric_partition, worthwhile


FACETS = ('socket_variant', 'base_code', 'roll_bucket')
# Exclusive native choices in appraisal-definitions.json are identities, not
# optional statistical roll splits. Unknown choices cannot use the pooled band.
IDENTITY_FACETS = {
    'hellfire torch': 'torch_class',
    'wraithstep': 'wraithstep_tree',
    'opalvein': 'opalvein_bonus',
    "ormus' robes": 'ormus_skill',
    'rainbow facet': 'rainbow_variant',
}
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
    if identity == 'rainbow_variant':
        from pricing.triage.facet_identity import variants

        rolls = dict.fromkeys(p for _, props, _, _ in variants() for p in props)
        facets = (*(f'property:{p}' for p in rolls), *facets)
    facets = (*mandatory, *facets)
    prepared = [(row, from_listing(row)) for row in rows]
    bands = []

    def node(members, facets, path):
        band = band_for(category, name, [r for r, _ in members])
        band['bucket'] = bucket + '|cohort:' + token(path)
        band['cohort_depth'] = len(path) - 1
        result = {'band': band}
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
                    key: node(group, facets[index if 'split_at' in result else index + 1 :], [*path, [facet, key]])
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
        reference['required_identity'] = list(mandatory)
    return [reference, *bands]


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
