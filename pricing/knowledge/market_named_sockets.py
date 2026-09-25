"""Socket-count proof from explicit fillers on named items without native sockets."""

from inventory_tracking.items.metadata import metadata


REFERENCE = 'third-parties/D2MOO/source/D2Game/src/UNIT/SUnitNpc.cpp:2286'


def single_socket_payload(row, variants):
    """Return a count proof, never infer an empty item from an omitted field."""
    if not variants or row.get('rarity') not in (None, 'unique', 'set'):
        return None
    for variant in variants:
        base = variant.get('base_definition', {})
        definition = variant.get('game_definition', {})
        cap = base.get('gemsockets')
        if (
            type(cap) is not int
            or cap < 1
            or base.get('hasinv') != 1
            or not definition
            or 'sock' in definition.values()
        ):
            return None
    payload = row['properties'].get('934')
    if not isinstance(payload, str):
        return None
    fillers = {
        b['name']
        for b in metadata()['bases'].values()
        if b.get('type') == 'rune' or b.get('type', '').startswith('gem')
    }
    if payload not in fillers:
        return None
    return {
        'kind': 'named_single_socket_payload',
        'property': '934',
        'payload': payload,
        'reference': REFERENCE,
        'definition_check': 'All named variants lack native sock modifiers.',
    }


def fixed_native_socket_count(variants):
    if not variants:
        return None
    counts = [(variant.get('native_socket_range') or {}).get('fixed') for variant in variants]
    if any(type(value) is not int or not 1 <= value <= 6 for value in counts) or len(set(counts)) != 1:
        return None
    return counts[0]
