"""Possible shared base resistance bonuses from native automagic groups."""


def resistance_options(base, automagic):
    group = base.get('auto prefix')
    if not group:
        return [0]
    rows = [r for r in automagic.values() if r.get('group') == group and r.get('spawnable') == 1]
    if not rows:
        return None
    values = set()
    for row in rows:
        found = False
        for slot in range(1, 4):
            code = row.get(f'mod{slot}code', '')
            if not code.startswith('res-'):
                continue
            low, high = row.get(f'mod{slot}min'), row.get(f'mod{slot}max')
            if (
                code != 'res-all'
                or found
                or type(low) is not int
                or type(high) is not int
                or not 0 <= low <= high <= 100
            ):
                return None
            found = True
            values.update(range(low, high + 1))
        if not found:
            values.add(0)
    return sorted(values)
