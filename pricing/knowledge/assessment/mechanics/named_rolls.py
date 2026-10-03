"""Bounds for standalone named-item modifiers, excluding base-dependent totals."""

import math

from pricing.knowledge.assessment.mechanics.elemental import ENDPOINTS, cold_duration_matches
from pricing.knowledge.assessment.mechanics.named_charms import CHARM_TYPES, is_standalone_charm, shared_roll_gaps


# Integer bonuses after NamedHandler removes native shield base blocking.
# Empty sockets are required independently by NamedHandler. Set contributions
# outside these standalone bounds need separate evidence before comparison.
# Do not bound total defense (31), weapon damage (21-24) or durability
# against a definition's added bonus. Named skills107 use their definition,
# not the generic1..3 staffmod cap; successful unique/set creation does not
# also call the random staffmod generator.
# Oskills97/aura151 use PropertyFunc22: native layer is skill ID, value is
# the rolled level (not the wearer-dependent effective skill level).
# Class skills83 and skill tabs188 are native unique rolls; random base
# auto-prefixes are not rolled for unique/set quality (D2MOO ItemMode.cpp).
# Native passive elemental mastery/pierce329..336 are scalar item rolls.
# Socket-adjusted facts reach this validator after known insert subtraction.
# Reviewed standalone equipment bonuses must match fixed values as well as
# variable ranges. Additional-affix charm recipes retain their separate proof.
# Flat attributes/resources and these recovery/absorb bonuses have no weapon or
# armor base contribution. Values are decoded item units, not player totals.
RESISTANCE_STATS = frozenset({37, 39, 41, 43, 45})
RESOURCE_STATS = frozenset({0, 1, 2, 3, 7, 9, 11, 27, 32, 34, 74, 76, 77, 78, 86, 89, 96, 128, 138, 139, 145, 149})
# RotW magic mastery, magic pierce and physical pierce are scalar modifiers.
ROTW_PASSIVE_STATS = frozenset({357, 358, 366})
# Stat122 is only the rolled undead modifier; inherent blunt damage is a
# separate derived base row with no native stat ID in the capture adapter.
COMBAT_STATS = frozenset({19, 111, 119, 121, 122, 123, 124, 134})
# Native PropertyFunc01 boolean effects have fixed integer1, no base contribution.
BOOLEAN_STATS = frozenset({81, 115, 117, 118, 153})
# Standalone scalar bonuses, not base totals or composite damage/duration.
SCALAR_STATS = frozenset(
    {28, 33, 40, 42, 44, 46, 85, 91, 102, 110, 113, 114, 116, 120, 135, 141, 150, 154, 156, 157, 158, 254}
)
BOUNDED_STATS = (
    SCALAR_STATS
    | BOOLEAN_STATS
    | RESOURCE_STATS
    | COMBAT_STATS
    | ROTW_PASSIVE_STATS
    | frozenset(stat for endpoints in ENDPOINTS.values() for stat, _ in endpoints)
    | frozenset(
        {
            16,
            17,
            18,
            20,
            35,
            36,
            60,
            62,
            79,
            80,
            83,
            93,
            97,
            99,
            105,
            107,
            127,
            136,
            142,
            143,
            144,
            147,
            148,
            151,
            188,
            *range(329, 337),
        }
    )
)


def roll_gaps(facts, definition):
    gaps = shared_roll_gaps(facts, definition)
    standalone_charm = is_standalone_charm(facts)
    for spec in definition.get('roll_ranges', {}).values():
        key = f'{spec["stat_id"]}:{spec.get("layer", 0)}'
        row = facts.stats.get(key, {})
        value = row.get('value')
        if row.get('status') != 'decoded' or value is None:
            gaps.append(f'Named property {key} was not captured.')
        elif spec['stat_id'] == 56:
            # Native cold-len ranges are frames, while the adapter exposes seconds.
            frames = row.get('raw')
            if not cold_duration_matches(facts, frames) or not spec['min'] <= frames <= spec['max']:
                gaps.append(
                    f'Named roll {key} has invalid cold duration or is outside its native frame range '
                    f'{spec["min"]}-{spec["max"]}.'
                )
        elif (
            standalone_charm
            or (spec['stat_id'] in BOUNDED_STATS and (spec['min'] != spec['max'] or facts.item_type not in CHARM_TYPES))
            or (spec['stat_id'] in RESISTANCE_STATS and facts.item_type not in CHARM_TYPES)
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
