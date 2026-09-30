"""Compile conditional native property groups without flattening their alternatives."""

import math


SOURCE = 'third-parties/d2data/json/propertygroups.json'


def compile_groups(record, groups, scalar_ranges, digest):
    result = []
    guaranteed = scalar_ranges(record)
    for slot in range(1, 13):
        code = record.get(f'prop{slot}')
        native = groups.get(code)
        if native is None:
            continue
        choices = []
        supported = native.get('PickMode') == 1 and record.get(f'min{slot}') == record.get(f'max{slot}') == 1
        supported &= record.get(f'par{slot}') in (None, '', 0)
        for index in range(1, 13):
            prop = native.get(f'Prop{index}')
            if not prop:
                continue
            low, high = native.get(f'ModMin{index}'), native.get(f'ModMax{index}')
            param_low, param_high = native.get(f'ParMin{index}'), native.get(f'ParMax{index}')
            ranges = scalar_ranges({'prop1': prop, 'min1': low, 'max1': high})
            supported &= (
                param_low in (None, '', 0)
                and param_high in (None, '', 0)
                and native.get(f'Chance{index}') == 1
                and bool(ranges)
                and type(low) is int
                and type(high) is int
                and 0 < low <= high
                and not set(ranges).intersection(guaranteed)
            )
            choices.append({'property': prop, 'roll_ranges': ranges})
        keys = [set(c['roll_ranges']) for c in choices]
        supported &= bool(choices) and sum(map(len, keys)) == len(set().union(*keys))
        result.append(
            {
                'code': code,
                'slot': slot,
                'game_definition': dict(native),
                'selection': 'single_scalar_choice' if supported else 'unresolved',
                'choices': choices,
                'source': {'path': SOURCE, 'sha256': digest, 'locator': '/' + code},
            }
        )
    return result


def selected_ranges(group, stats):
    """Return one completely observed alternative, or None for ambiguous/invalid evidence.

    stats uses native id:layer keys and decoded scalar values. An alternative may
    span multiple native stats (Enhanced Damage's paired minimum/maximum values).
    """
    if group.get('selection') != 'single_scalar_choice':
        return None
    choices = group['choices']
    keyed = [{f'{r["stat_id"]}:{r.get("layer", 0)}': r for r in c['roll_ranges'].values()} for c in choices]
    present = set(stats).intersection(set().union(*(set(c) for c in keyed)))
    matches = [c for c in keyed if set(c) == present]
    if len(matches) != 1:
        return None
    chosen = matches[0]
    values = []
    for key, spec in chosen.items():
        row = stats[key]
        value = row.get('value')
        if (
            row.get('status') != 'decoded'
            or type(value) not in (int, float)
            or not math.isfinite(value)
            or value != int(value)
            or not spec['min'] <= value <= spec['max']
        ):
            return None
        values.append(value)
    # Every native stat emitted by one scalar property receives the same roll.
    if len(set(values)) != 1:
        return None
    return {key: {**spec, 'source': group['source']} for key, spec in chosen.items()}
