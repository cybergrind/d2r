"""Precompute no-better base modifier bands; runtime stays an ordinary table lookup."""

from itertools import product
from math import prod

from pricing.triage.variants import scoped_bucket


# A native Knight's shield automod plus superior durability spans
# 15 damage rolls * 21 attack-rating rolls * 6 durability rolls = 1,890.
# Bound offline expansion without silently dropping this legal combination.
MAX_ROLL_COMBINATIONS = 2048

# Native automagic groups 300/302: one to three skill-tree levels on Amazon bases.
AMAZON_AUTOMODS = {'abow': '454', 'aspe': '456', 'ajav': '456'}


def with_rolls(modifiers, rolls):
    """Keep the projected elemental copies of one all-resistance roll linked."""
    updated = modifiers | rolls
    if '441' in rolls and '441' in modifiers:
        for prop in ('401', '426', '427', '428'):
            if modifiers.get(prop) == modifiers['441']:
                updated[prop] = rolls['441']
    return updated


def comparison_bounds(item, policy):
    modifiers = item.get('base_modifiers')
    if not isinstance(modifiers, dict):
        return {}
    allowed = {p: {'min': 1, 'max': 3, 'label': label} for p, label in policy.get('compare_staffmods', {}).items()}
    if item.get('rarity') == 'superior':
        allowed |= policy.get('compare_modifiers', {})
    allowed |= {
        p: spec
        for p, spec in policy.get('compare_inherent', {}).items()
        if type(modifiers.get(p)) is int and spec['min'] <= modifiers[p] <= spec['max']
    }
    if (
        item.get('category') == 'base'
        and item.get('rarity') in ('normal', 'superior')
        and (prop := AMAZON_AUTOMODS.get(item.get('family')))
    ):
        allowed[prop] = {'min': 1, 'max': 3, 'label': 'native Amazon skill-tree levels'}
    bounds = {p: allowed[p] for p in modifiers if p in allowed}
    if prod(spec['max'] - spec['min'] + 1 for spec in bounds.values()) > MAX_ROLL_COMBINATIONS or any(
        type(modifiers[p]) is not int or not spec['min'] <= modifiers[p] <= spec['max'] for p, spec in bounds.items()
    ):
        return {}
    return bounds


def no_worse_modifiers(item, policy):
    modifiers = item['base_modifiers']
    bounds = comparison_bounds(item, policy)
    props = sorted(bounds)
    return [
        with_rolls(modifiers, dict(zip(props, values, strict=True)))
        for values in product(*(range(modifiers[p], bounds[p]['max'] + 1) for p in props))
    ]


def no_better_modifiers(item, policy):
    modifiers = item['base_modifiers']
    bounds = comparison_bounds(item, policy)
    props = sorted(bounds)
    return [
        with_rolls(modifiers, dict(zip(props, values, strict=True)))
        for values in product(*(range(bounds[p]['min'], modifiers[p] + 1) for p in props))
    ]


def compile_modifiers(category, name, bucket, rows, policy, *, coarse_index=None, coarse_properties=()):
    from pricing.triage.adapters import from_listing
    from pricing.triage.bands import band_for

    groups = {}
    for row in rows:
        item = from_listing(row)
        modifiers = item.get('base_modifiers')
        if not isinstance(modifiers, dict):
            continue
        bounds = comparison_bounds(item, policy)
        skills = {p: modifiers[p] for p in bounds}
        if not skills:
            continue
        # Same skill set, same other modifiers. A different skill is a different
        # paid pattern; absent skills are not guessed to be zero-valued rolls.
        anchor = item | {'base_modifiers': with_rolls(modifiers, {p: bounds[p]['min'] for p in skills})}
        key = scoped_bucket(bucket, anchor, policy['facets'])
        if key is not None:
            groups.setdefault(key, []).append((row, item, skills, bounds))
    bands = []
    for members in groups.values():
        sample = members[0][1]
        props = sorted(members[0][2])
        bounds = members[0][3]
        for values in product(*(range(bounds[p]['min'], bounds[p]['max'] + 1) for p in props)):
            target_rolls = dict(zip(props, values, strict=True))
            selected = [r for r, _, skills, _ in members if all(skills[p] <= v for p, v in target_rolls.items())]
            if not selected:
                continue
            target = sample | {'base_modifiers': with_rolls(sample['base_modifiers'], target_rolls)}
            if coarse_index:
                from pricing.triage.base_cohorts import band as base_cohort

                replacement = base_cohort(target, bucket, policy, coarse_index, coarse_properties)
                if replacement and replacement['sellers'] >= 3:
                    continue
            band = band_for(category, name, selected)
            band.update(
                bucket=scoped_bucket(bucket, target, policy['facets']),
                comparison={
                    'kind': 'base_modifiers',
                    'rolls': target_rolls,
                    'label': ', '.join(f'+{v} {bounds[p]["label"]}' for p, v in target_rolls.items()),
                },
            )
            bands.append(band)
    return bands
