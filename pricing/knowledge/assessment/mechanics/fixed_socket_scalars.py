"""Recipient-specific fixed rune/gem scalars from bundled, source-checked metadata."""

from inventory_tracking.items.metadata import metadata


def contribution(facts, child, key):
    data = metadata()
    bundle = data.get('fixed_socket_scalars', {})
    code = child.get('base_code')
    base = next((b for b in data['bases'].values() if b['code'] == code), None)
    if not base or child.get('name') != base['name'] or child.get('item_type') != base['type']:
        return None
    recipient = next((b for b in data['bases'].values() if b['code'] == facts.base_code), None)
    if not recipient or recipient['type'] != facts.item_type:
        return None
    destination = bundle.get('recipients', {}).get(facts.base_code)
    value = bundle.get('effects', {}).get(code, {}).get(destination, {}).get(key)
    return value if type(value) is int else None
