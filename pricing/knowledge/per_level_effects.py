"""Compile per-level coefficients, retaining native fixed-point units."""


def coefficient_ranges(record, properties, stats, *, runeword=False):
    result = []
    for slot in range(1, 13):
        code = record.get(f'T1Code{slot}' if runeword else f'prop{slot}')
        prop = properties.get(code, {})
        stat = stats.get(prop.get('stat1'), {})
        parameter = record.get(f'T1Param{slot}' if runeword else f'par{slot}')
        shift, scale = stat.get('ValShift', 0), stat.get('op param')
        if (
            prop.get('func1') != 17
            # Native op4 reads the wielder's level (D2MOO D2StatList.cpp).
            # Limit this to the flat defense/damage coefficients we decode.
            or not (stat.get('op') == 2 or (stat.get('*ID') in (214, 218) and stat.get('op') == 4))
            or stat.get('op base') != 'level'
            or stat.get('descfunc') != 19
            or type(shift) is not int
            or not 0 <= shift <= 16
            or type(scale) is not int
            or not 0 <= scale <= 16
        ):
            continue
        if parameter is None or (type(parameter) is int and parameter == 0):
            low = record.get(f'T1Min{slot}' if runeword else f'min{slot}')
            high = record.get(f'T1Max{slot}' if runeword else f'max{slot}')
        else:
            low = high = parameter
        if any(type(v) is not int or v <= 0 for v in (low, high)) or low > high:
            continue
        result.append(
            {
                'stat_id': stat['*ID'],
                'minimum_raw': low << shift,
                'maximum_raw': high << shift,
                'step_raw': 1 << shift,
                'denominator': 1 << (shift + scale),
            }
        )
    return result


def fixed_per_level_effects(record, properties, stats, *, runeword=False):
    return [
        {'stat_id': r['stat_id'], 'coefficient_raw': r['minimum_raw'], 'denominator': r['denominator']}
        for r in coefficient_ranges(record, properties, stats, runeword=runeword)
        if r['minimum_raw'] == r['maximum_raw']
    ]


def variable_per_level_effects(record, properties, stats, *, runeword=False):
    return [
        r
        for r in coefficient_ranges(record, properties, stats, runeword=runeword)
        if r['minimum_raw'] != r['maximum_raw']
    ]
