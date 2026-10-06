"""Steering 7 base ladder: exact, without superior ED, then without sockets."""

import json
from collections import defaultdict

from pricing.triage.named_cohorts import compile_named, lookup as cohort_lookup
from pricing.triage.named_fallback import supported


LEVELS = ((), ('base_ed',), ('base_ed', 'sockets'))


def comparison_policy(policy, relaxed):
    facets = ('rarity', 'ethereal', 'base_modifiers', 'base_ed', 'sockets')
    return policy | {'facets': [facet for facet in facets if facet not in relaxed]}


def comparison_bucket(relaxed):
    return 'base-fallback-comparison:' + ','.join(relaxed)


def keys(item, *, allow_missing_ed=False):
    ed = item.get('base_ed')
    valid_ed = type(ed) in (int, float) and 0 <= ed <= 15
    if (
        item.get('category') != 'base'
        or item.get('rarity') not in ('normal', 'superior')
        or type(item.get('ethereal')) is not bool
        or item.get('socket_contents') != 'empty'
        or not isinstance(item.get('base_modifiers'), dict)
        or not (valid_ed or (allow_missing_ed and ed is None))
        or type(item.get('sockets')) is not int
        or not 0 <= item['sockets'] <= 6
    ):
        return []
    core = {k: item.get(k) for k in ('rarity', 'ethereal', 'base_modifiers', 'base_ed', 'sockets')}
    if item['rarity'] == 'superior':
        # Native qualityitems.json; retain inherent shield AR and all skill/resistance rolls.
        limits = {'423': (1, 3), '937': (10, 15)}
        core['base_modifiers'] = {
            prop: value
            for prop, value in core['base_modifiers'].items()
            if prop not in limits or type(value) not in (int, float) or not limits[prop][0] <= value <= limits[prop][1]
        }
    result = []
    for relaxed in LEVELS:
        facets = {k: v for k, v in core.items() if k not in relaxed}
        if any(v is None for v in facets.values()):
            continue
        result.append(('base-fallback-rolls:' + json.dumps(facets, sort_keys=True, separators=(',', ':')), relaxed))
    return result


def compile_bands(name, rows, policy):
    from inventory_tracking.items.metadata import metadata
    from pricing.triage.adapters import from_listing
    from pricing.triage.market_bases import clean_modifiers

    base = next((b for b in metadata()['bases'].values() if b['name'] == name), None)
    if not base or not base.get('max_sockets'):
        return []
    groups = defaultdict(list)
    valid = []
    for row in rows:
        item = from_listing(row)
        sockets = item.get('sockets')
        if (
            item.get('base_code') != base['code']
            or type(sockets) is not int
            or not 0 <= sockets <= base['max_sockets']
            or not clean_modifiers(item, base, policy)
        ):
            continue
        # An omitted ED value is usable only after that facet is dropped.
        # It cannot contribute to an exact ED band or be interpreted as zero.
        item_keys = keys(item, allow_missing_ed=True)
        if item_keys:
            valid.append(row)
        for key, relaxed in item_keys:
            groups[key, relaxed].append(row)
    bands = []
    for (key, relaxed), members in groups.items():
        compiled = compile_named(
            'base', name, members, [], facets=('base_modifier:423', 'base_modifier:937'), bucket=key
        )
        for band in compiled:
            band['relaxed_facets'] = list(relaxed)
        bands.extend(compiled)
    # The same no-better modifier rule used by exact base buckets also applies
    # at each fallback level. Skill identities and unreviewed modifiers stay exact.
    from pricing.triage.base_comparisons import compile_modifiers

    for relaxed in LEVELS:
        compiled = compile_modifiers(
            'base', name, comparison_bucket(relaxed), valid, comparison_policy(policy, relaxed)
        )
        for band in compiled:
            band['relaxed_facets'] = list(relaxed)
        bands.extend(compiled)
    return bands


def lookup(item, bands):
    from inventory_tracking.items.metadata import metadata_generation
    from pricing.triage.adapters import bases_by_code
    from pricing.triage.market_bases import clean_modifiers, native_staffmods
    from pricing.triage.variants import scoped_bucket

    bases = bases_by_code(metadata_generation())
    base = (
        bases.get(item.get('base_code'))
        if item.get('base_code')
        else next((b for b in bases.values() if b['name'].casefold() == item.get('name', '').casefold()), None)
    )
    if base is None or (type(item.get('sockets')) is int and item['sockets'] > base.get('max_sockets', 0)):
        return None
    if not clean_modifiers(item, base, {}):
        return None
    needs_preparation = item.get('sockets') == 0 and bool(
        item['base_modifiers'].keys() & native_staffmods(metadata_generation()).get(base['type'], {}).keys()
    )
    # Missing ED skips the exact level for both targets and sources;
    # unknown is never silently converted to zero.
    for key, relaxed in keys(item, allow_missing_ed=True):
        # Guide §2 gray: an unsocketed staffmod candidate must not inherit
        # the price of an already socketed base, even when ED is relaxed.
        if needs_preparation and 'sockets' in relaxed:
            continue
        found = bands.get(('base', item['name'].casefold(), key))
        selected = cohort_lookup(item, found) if found else None
        if supported(selected):
            return selected
        key = scoped_bucket(comparison_bucket(relaxed), item, comparison_policy({}, relaxed)['facets'])
        selected = bands.get(('base', item['name'].casefold(), key)) if key is not None else None
        if supported(selected):
            return selected
    return None


def missing_reason(item, rules):
    """Keep reviewed base patterns when only price facets lack evidence."""
    from pricing.triage.engine import matches

    if (
        item.get('category') != 'base'
        or item.get('rarity') not in ('normal', 'superior')
        or item.get('socket_contents') != 'empty'
    ):
        return None
    for rule in rules:
        source = rule.get('source', '')
        if (
            rule.get('category') != 'base'
            or not rule.get('bucket')
            or not source.startswith(('guides/', 'pricing/data/wp-'))
        ):
            continue
        conditions = dict(rule.get('conditions', {}))
        for facet in ('sockets', 'base_ed', 'base_ed_grade'):
            conditions.pop(facet, None)
        if item.get('ethereal') is None:
            conditions.pop('ethereal', None)
        if not matches(item, rule | {'conditions': conditions}):
            continue
        missing = [
            label
            for facet, label in (
                ('ethereal', 'ethereal status'),
                ('sockets', 'sockets'),
                ('base_ed', 'superior ED'),
                ('base_modifiers', 'modifiers'),
            )
            if item.get(facet) is None
        ]
        if missing:
            return 'guide-listed base; missing ' + ', '.join(missing)
        return 'guide-listed base; fewer than three sellers for matching ethereal status, sockets, ED and modifiers'
    return None
