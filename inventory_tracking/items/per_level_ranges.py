"""Rank native coefficients and display their bounds at the captured level."""


def annotate_per_level_range(row, identity):
    stat = row.get('memory_stat', {})
    matches = [
        effect for effect in identity.get('variable_per_level_effects', ()) if effect['stat_id'] == stat.get('id')
    ]
    if len(matches) != 1 or row.get('status') != 'decoded' or stat.get('layer') != 0:
        return
    effect = matches[0]
    low, high = effect['minimum_raw'], effect['maximum_raw']
    step, divisor = effect['step_raw'], effect['denominator']
    raw, level = stat.get('raw'), row.get('viewer_level')
    label = row.get('range_label', '')
    if (
        any(type(value) is not int for value in (low, high, step, divisor, raw, level))
        or not 0 < low < high
        or step <= 0
        or divisor <= 0
        or not 1 <= level <= 99
        or not low <= raw <= high
        or (raw - low) % step
        or (high - low) % step
        or row.get('per_level') != {'numerator': raw, 'denominator': divisor}
        or row.get('value') != raw * level // divisor
        or '{{value}}' not in label
    ):
        return
    minimum, maximum = low * level // divisor, high * level // divisor
    row['roll_range'] = {
        **effect,
        'min': minimum,
        'max': maximum,
        'viewer_level': level,
        'better': 'higher',
        'source': identity['source'],
        'scope': 'item definition coefficient at captured character level',
    }
    # Rounding can make distinct coefficients display the same value. Rank the
    # coefficient so a low roll never becomes perfect just because level is low.
    row['roll_quality'] = 'perfect' if raw == high else 'low' if 5 * (raw - low) <= high - low else 'normal'
    unit = '%' if '{{value}}%' in label else ''
    row['text'] = label.replace('{{value}}' + unit, f'{row["value"]}{unit} ({minimum}-{maximum}{unit})').replace(
        '+-', '-'
    )
