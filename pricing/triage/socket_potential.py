"""Socket preparation from compiled caps, separate from the item's price band."""


def preparation(item, rules):
    if (
        item.get('category') != 'base'
        or item.get('rarity') not in ('normal', 'superior')
        or type(item.get('sockets')) is not int
        or item['sockets'] != 0
    ):
        return None
    caps = rules.get('socket_caps', {}).get(item.get('name'))
    if not isinstance(caps, list) or len(caps) != 3 or any(type(c) is not int or not 0 <= c <= 6 for c in caps):
        return None
    level = item.get('item_level')
    known = type(level) is int and 1 <= level <= 99
    values = [caps[0 if level <= 25 else 1 if level <= 40 else 2]] if known else sorted(set(caps))
    values = [v for v in values if v > 0]
    if not values:
        return None
    return {
        'larzuk': values,
        'cube': list(range(1, max(values) + 1)) if item['rarity'] == 'normal' else [],
        'conditional': not known and len(set(caps)) > 1,
    }
