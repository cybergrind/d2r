"""Comparable skiller suffixes: omitted numeric affixes differ from present rolls."""

# Tree IDs verified against native stat 188 mappings and cached Traderie labels.
TREES = frozenset(
    [
        '443',
        '444',
        '445',
        '516',
        '517',
        '515',
        '408',
        '410',
        '409',
        '456',
        '454',
        '455',
        '500',
        '499',
        '501',
        '406',
        '405',
        '404',
        '487',
        '485',
        '486',
        '1547',
        '1548',
        '1546',
    ]
)
# Scope, quality, required level, ethereal/socket metadata are not charm suffixes.
METADATA = frozenset(['799', '800', '798', '1854', '797', '796', '738', '402', '934'])


def suffix(name, properties):
    if name != 'Grand Charm':
        return None
    return {
        key: value
        for key, value in sorted(properties.items())
        if key not in TREES | METADATA and type(value) in (int, float) and value != 0
    }


def poison_total(facts):
    """Project a single-source charm tooltip total, never a poison rate alone."""
    from inventory_tracking.items.poison import DAMAGE_SCALE, FRAMES_PER_SECOND, POISON_STATS

    if facts.item_type not in ('scha', 'mcha', 'lcha'):
        return None
    rows = [facts.stats.get(f'{stat}:0', {}) for stat in sorted(POISON_STATS)]
    if any(row.get('status') != 'decoded' or type(row.get('raw')) is not int or row['raw'] <= 0 for row in rows):
        return None
    low, high, frames, sources = [row['raw'] for row in rows]
    if low != high or sources != 1 or frames % FRAMES_PER_SECOND:
        return None
    return (low * frames + DAMAGE_SCALE // 2) // DAMAGE_SCALE
