"""Native flee chance uses128 as100%; displayed integerpercent loses precision."""


def capture_gap(facts, definition):
    record = definition.get('game_definition', {})
    slots = [i for i in range(1, 13) if record.get(f'prop{i}') == 'howl']
    if not slots:
        return None
    gap = 'Named flee chance112:0 is missing or conflicts with its native encoded roll.'
    if len(slots) != 1:
        return gap
    low, high = record.get(f'min{slots[0]}'), record.get(f'max{slots[0]}')
    row = facts.stats.get('112:0', {})
    raw, value = row.get('raw'), row.get('value')
    if (
        type(low) is not int
        or type(high) is not int
        or low > high
        or row.get('status') != 'decoded'
        or type(raw) is not int
        or not low <= raw <= high
        or type(value) not in (int, float)
        or value != raw * 100 // 128
    ):
        return gap
    return None
