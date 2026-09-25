"""Compile fixed elemental endpoint properties from unique/set definitions."""

from pricing.knowledge.rune_effects import FUNCTIONS


def fixed_elemental_effects(record, properties, *, runeword=False):
    effects = []
    for slot in range(1, 13):
        code = record.get(f'T1Code{slot}' if runeword else f'prop{slot}')
        if code not in ('dmg-cold', 'dmg-fire', 'dmg-ltng'):
            continue
        kind, functions = FUNCTIONS[code]
        spec = properties.get(code, {})
        if any((spec.get(f'func{i}'), spec.get(f'stat{i}')) != pair for i, pair in enumerate(functions, 1)):
            continue
        prefixes = ('T1Min', 'T1Max', 'T1Param') if runeword else ('min', 'max', 'par')
        low, high, frames = (record.get(f'{prefix}{slot}') for prefix in prefixes)
        # A recipe can omit cold duration. Retain its source so rune-only cold
        # totals cannot accidentally become intrinsic; runtime cannot verify None.
        values = (low, high, frames) if kind == 'cold' and not (runeword and frames is None) else (low, high)
        if any(type(value) is not int or value <= 0 for value in values) or low > high:
            continue
        effects.append(
            {
                'kind': kind,
                'slot': slot,
                'minimum_damage': low,
                'maximum_damage': high,
                **({'duration_frames': frames} if kind == 'cold' else {}),
            }
        )
    return effects


def fixed_poison_effect(record, properties):
    """One fixed source, either compound or three fixed scalar components."""
    codes = ('dmg-pois', 'pois-min', 'pois-max', 'pois-len')
    slots = [(i, record.get(f'prop{i}')) for i in range(1, 13) if record.get(f'prop{i}') in codes]
    if len(slots) == 1 and slots[0][1] == 'dmg-pois':
        slot = slots[0][0]
        spec = properties.get('dmg-pois', {})
        if any(
            (spec.get(f'func{i}'), spec.get(f'stat{i}')) != pair for i, pair in enumerate(FUNCTIONS['dmg-pois'][1], 1)
        ):
            return None
        low, high, frames = (record.get(f'{prefix}{slot}') for prefix in ('min', 'max', 'par'))
    elif len(slots) == 3 and {code for _, code in slots} == set(codes[1:]):
        values = {}
        for slot, code in slots:
            spec = properties.get(code, {})
            expected = {'pois-min': 'poisonmindam', 'pois-max': 'poisonmaxdam', 'pois-len': 'poisonlength'}[code]
            if spec.get('func1') != 1 or spec.get('stat1') != expected:
                return None
            if record.get(f'min{slot}') != record.get(f'max{slot}'):
                return None
            values[code] = record.get(f'min{slot}')
        low, high, frames = (values[code] for code in codes[1:])
    else:
        return None
    if any(type(value) is not int or value <= 0 for value in (low, high, frames)) or low > high:
        return None
    return {'minimum_rate_raw': low, 'maximum_rate_raw': high, 'duration_frames': frames, 'source_count': 1}
