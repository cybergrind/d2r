"""Named reanimation and cosmetic blood effects from native properties.

Reanimation fixes both the monster layer and chance. Native bloody is explicitly
Visuals Only: its legal rolled intensity is validated but does not partition
market comparisons. This exception does not apply to gameplay modifiers.
"""


def special_effect_keys(facts, definition):
    record = definition.get('game_definition', {})
    consumed, gaps = set(), []
    for stat, prop in ((140, 'bloody'), (155, 'reanimate')):
        slots = [i for i in range(1, 13) if record.get(f'prop{i}') == prop]
        if not slots:
            continue
        low, high = record.get(f'min{slots[0]}'), record.get(f'max{slots[0]}')
        layer = record.get(f'par{slots[0]}') if stat == 155 else 0
        key = f'{stat}:{layer}'
        row = facts.stats.get(key, {})
        valid = (
            len(slots) == 1
            and type(layer) is int
            and layer >= 0
            and type(low) is int
            and type(high) is int
            and 0 <= low <= high
            and (stat == 140 or low == high <= 100)
            and row.get('status') == 'decoded'
            and type(row.get('raw')) is int
            and type(row.get('value')) is int
            and low <= row['raw'] == row['value'] <= high
            and row.get('market_property') is None
        )
        if valid:
            consumed.add(key)
        else:
            gaps.append(f'Named {prop} effect {key} is missing, changed or unverified.')
    return consumed, gaps
