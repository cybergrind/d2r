"""Bounds for standalone named-item modifiers, excluding base-dependent totals."""

import math

from pricing.knowledge.assessment.mechanics.named_charms import is_standalone_charm, shared_roll_gaps


# Integer bonuses with no inherent base contribution on unique/set equipment.
# Empty sockets are required independently by NamedHandler. Set contributions
# outside these standalone bounds need separate evidence before comparison.
# Do not bound total defense (31), weapon damage (21-24), durability, resistances
# or staffmods against a definition's added bonus.
BOUNDED_STATS = frozenset({16, 17, 18, 35, 36, 60, 62, 79, 80, 93, 99, 105, 127, 136, 142, 143, 144, 147, 148})


def roll_gaps(facts, definition):
    gaps = shared_roll_gaps(facts, definition)
    standalone_charm = is_standalone_charm(facts)
    for spec in definition.get('roll_ranges', {}).values():
        key = f'{spec["stat_id"]}:{spec.get("layer", 0)}'
        row = facts.stats.get(key, {})
        value = row.get('value')
        if row.get('status') != 'decoded' or value is None:
            gaps.append(f'Named property {key} was not captured.')
        elif (
            standalone_charm
            or (spec['stat_id'] in BOUNDED_STATS and spec['min'] != spec['max'])
            or spec['stat_id'] == 126
        ):
            low, high = spec['min'], spec['max']
            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or value != int(value)
                or not low <= value <= high
            ):
                gaps.append(f'Named roll {key} is outside its standalone integer range {low}-{high}.')
    return gaps


def variable_projection_gaps(facts, definition, properties):
    """A known scalar variable bonus must survive in the market contract.

    Structural defense/socket values have dedicated contract fields. Compound
    effects and parameterized skills retain their specialized projection proofs.
    """
    from inventory_tracking.items.metadata import metadata

    catalog = metadata()['stats']
    gaps = []
    for spec in definition.get('roll_ranges', {}).values():
        stat, layer = spec['stat_id'], spec.get('layer', 0)
        if spec['min'] == spec['max'] or stat in (31, 194):
            continue
        key = f'{stat}:{layer}'
        row = facts.stats.get(key, {})
        prop = row.get('market_property')
        if prop is None and layer == 0:
            prop = catalog.get(str(stat), {}).get('property_id')
        if prop is not None and (
            row.get('status') != 'decoded' or prop not in properties or properties[prop] != row.get('value')
        ):
            gaps.append(f'Named roll {key} has a missing or conflicting market projection.')
    return gaps
