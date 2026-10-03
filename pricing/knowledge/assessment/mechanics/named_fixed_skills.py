"""Exact named skill invariants do not need an invented market property.

Variable skill rolls still need a verified market projection. Neither a class
skill's layer nor an oskill/aura's layer is interchangeable with another skill.
"""

from inventory_tracking.items.metadata import metadata


SKILL_PROPERTIES = {97: 'oskill', 107: 'skill', 151: 'aura'}


def fixed_skill_keys(facts, definition):
    consumed, gaps = set(), []
    record = definition.get('game_definition', {})
    skills = metadata()['skills']
    for spec in definition.get('roll_ranges', {}).values():
        prop = SKILL_PROPERTIES.get(spec['stat_id'])
        if prop is None or spec['min'] != spec['max']:
            continue
        layer = spec.get('layer')
        key = f'{spec["stat_id"]}:{layer}'
        row = facts.stats.get(key, {})
        if row.get('market_property') is not None:
            continue  # Existing market projection and roll checks own this stat.
        skill = skills.get(str(layer), {})
        internal_name = skill.get('internal_name', skill.get('name'))
        slots = [
            i
            for i in range(1, 13)
            if record.get(f'prop{i}') == prop
            and (
                (type(record.get(f'par{i}')) is int and record[f'par{i}'] == layer)
                or (isinstance(record.get(f'par{i}'), str) and record[f'par{i}'] == internal_name)
            )
        ]
        expected = spec['min']
        if (
            type(layer) is not int
            or not skill
            or spec.get('property') != prop
            or type(expected) is not int
            or expected <= 0
            or len(slots) != 1
            or record.get(f'min{slots[0]}') != expected
            or record.get(f'max{slots[0]}') != expected
            or row.get('status') != 'decoded'
            or type(row.get('raw')) is not int
            or row['raw'] != expected
            or type(row.get('value')) is not int
            or row['value'] != expected
        ):
            gaps.append(f'Named fixed skill {key} is missing, changed or unverified.')
        else:
            consumed.add(key)
    return consumed, gaps
