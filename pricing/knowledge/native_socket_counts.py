"""Prepare conservative socket ranges from native property function 14."""


def native_socket_range(record, base, types):
    indices = [key[4:] for key, value in record.items() if key.startswith('prop') and value == 'sock']
    if len(indices) != 1:
        return None
    index = indices[0]
    low, high, parameter = (record.get(prefix + index) for prefix in ('min', 'max', 'par'))
    if low is None and high is None:
        if type(parameter) is not int or not 1 <= parameter <= 255:
            return None
        rolls = [parameter]
    elif type(low) is int and type(high) is int and 1 <= low <= high <= 255:
        rolls = range(low, high + 1)
    else:
        return None  # Unreviewed zero/negative/fallback or malformed property encoding.
    limits = [types.get(base.get('type'), {}).get(key) for key in ('MaxSockets1', 'MaxSockets2', 'MaxSockets3')]
    cap, width, height = (base.get(key) for key in ('gemsockets', 'invwidth', 'invheight'))
    if any(type(value) is not int or value < 1 for value in (cap, width, height, *limits)):
        return None
    brackets = []
    for limit in limits:
        maximum = min(cap, width * height, limit)
        values = sorted({min(max(roll, 1), maximum) for roll in rolls})
        brackets.append({'min': values[0], 'max': values[-1]})
    low, high = min(b['min'] for b in brackets), max(b['max'] for b in brackets)
    return {
        'min': low,
        'max': high,
        'fixed': low if low == high else None,
        'by_ilvl_bracket': brackets,
        'reference': 'third-parties/D2MOO/source/D2Common/src/Items/ItemMods.cpp:ITEMMODS_PropertyFunc14',
    }
