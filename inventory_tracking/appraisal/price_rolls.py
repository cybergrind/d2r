"""Color only price-deciding native stats when a validated roll model applies."""

from math import isfinite

from inventory_tracking.presentation import Tone


def native_keys(stat):
    rows = ([stat['memory_stat']] if stat.get('memory_stat') else []) + list(stat.get('memory_stats', []))
    return {f'{row.get("id")}:{row.get("layer")}' for row in rows}


def deciding_specs(stat, comparison):
    keys = native_keys(stat)
    return [spec for spec in (comparison or {}).get('deciding', {}).values() if spec.get('native_key') in keys]


def listed_roll_tone(stat, comparison):
    tones = set()
    for spec in deciding_specs(stat, comparison):
        value = stat.get('native_values', {}).get(spec['native_key'], {}).get('value', stat.get('value'))
        if type(value) not in (int, float) or not isfinite(value) or not spec['min'] <= value <= spec['max']:
            tones.add(Tone.DEFAULT)
            continue
        low, high = spec.get('observed_min', spec['min']), spec.get('observed_max', spec['max'])
        lower = spec.get('better') == 'lower'
        if value <= low if lower else value >= high:
            tones.add(Tone.PERFECT)
        elif value > high if lower else value < low:
            tones.add(Tone.LOW)
        else:
            fraction = (value - low) / (high - low)
            tones.add(Tone.LOW if (1 - fraction if lower else fraction) <= 0.2 else Tone.DEFAULT)
    return next(iter(tones)) if len(tones) == 1 else Tone.DEFAULT
