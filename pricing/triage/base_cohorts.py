"""Pool superior secondary bonuses without crossing required base combinations."""

from collections import defaultdict

from pricing.triage.named_cohorts import compile_named, lookup, token
from pricing.triage.variants import scoped_bucket


def identity(item, bucket, policy, properties=()):
    modifiers = item.get('base_modifiers')
    if item.get('rarity') not in ('normal', 'superior') or not isinstance(modifiers, dict):
        return None, ()
    secondary = []
    bonuses = policy.get('compare_modifiers', {}) if item['rarity'] == 'superior' else {}
    for prop, spec in bonuses.items():
        value = modifiers.get(prop, 0)
        # Native shield attack rating is not the superior 1-3 AR bonus.
        if value == 0 or (type(value) in (int, float) and spec['min'] <= value <= spec['max']):
            secondary.append(prop)
    # Explicit multi-stat/staffmod comparisons retain their no-better semantics.
    # Only otherwise exact-split ranges inherit the coarse bucket policy here.
    declared = [
        p
        for p, spec in dict(properties).items()
        if isinstance(spec, dict)
        and ('min' in spec or 'max' in spec)
        and p in modifiers
        and p not in policy.get('compare_inherent', {})
        and p not in policy.get('compare_staffmods', {})
    ]
    secondary = sorted(set(secondary + declared))
    if not secondary:
        return None, ()
    core = item | {'base_modifiers': {p: v for p, v in modifiers.items() if p not in secondary}}
    if '441' in declared:
        # Projection expands all-res into its four components. They are one roll.
        core['base_modifiers'] = {
            p: v
            for p, v in core['base_modifiers'].items()
            if p not in ('401', '426', '427', '428') or v != modifiers['441']
        }
    facets = [f for f in policy.get('facets', []) if f != 'ethereal']
    key = scoped_bucket('base-coarse:' + bucket + ':' + token(sorted(secondary)), core, facets)
    return key, tuple('base_modifier:' + p for p in sorted(secondary))


def compile_bands(name, bucket, rows, policy, properties=()):
    from pricing.triage.adapters import from_listing

    groups = defaultdict(list)
    for row in rows:
        key, facets = identity(from_listing(row), bucket, policy, properties)
        if key is not None:
            groups[key, facets].append(row)
    bands = []
    for (key, facets), members in groups.items():
        compiled = compile_named('base', name, members, [], facets=facets, bucket=key)
        if any('cohort_depth' in b and b['sellers'] >= 3 for b in compiled):
            bands.extend(compiled)
    return bands


def band(item, bucket, policy, bands, properties=()):
    key, _ = identity(item, bucket, policy, properties)
    reference = bands.get(('base', item['name'].casefold(), key)) if key is not None else None
    return lookup(item, reference) if reference else None
