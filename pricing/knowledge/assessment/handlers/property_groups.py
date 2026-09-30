"""Named random-property alternatives must be observed and survive price projection."""

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.property_groups import selected_ranges


def comparison_gaps(facts, definition, properties):
    gaps = []
    groups = definition.get('property_groups', ())
    # Old published metadata cannot silently waive a known random roll.
    codes = {definition.get('game_definition', {}).get(f'prop{i}') for i in range(1, 13)}
    if 'magdam-rand' in codes and not any(g['code'] == 'magdam-rand' for g in groups):
        gaps.append('Random property group magdam-rand requires compiled native alternatives.')
    for group in groups:
        if group['code'] == 'skilltab-war':
            continue  # The parameterized random_skills handler validates this group.
        ranges = selected_ranges(group, facts.stats)
        if not facts.capture_complete or ranges is None:
            gaps.append(f'Random property group {group["code"]} is missing, conflicting or unsupported.')
            continue
        for key, spec in ranges.items():
            row = facts.stats[key]
            prop = row.get('market_property') or metadata()['stats'].get(str(spec['stat_id']), {}).get('property_id')
            if prop is None or properties.get(prop) != row['value']:
                gaps.append(f'Random property group {group["code"]} roll {key} has no matching market projection.')
    return gaps
