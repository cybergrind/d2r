"""Ranges for class-restricted native staffmods, separate from affix tiers."""

from inventory_tracking.items.identity import IDENTIFIED_FLAG, RUNEWORD_FLAG, item_flags
from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.ranges import annotate_roll_ranges
from inventory_tracking.items.stat_constants import StatId


def annotate_staffmods(decoded, details, arrays, base):
    flags = item_flags(details, arrays)
    if flags is None or not flags & IDENTIFIED_FLAG or details.get('quality') not in (1, 2, 3, 4, 6, 8):
        return
    catalog = metadata()
    rules = catalog['staffmods']
    class_name = rules['classes_by_type'].get(base.get('type'))
    if not class_name:
        return
    bounds = rules['inferior_range'] if details['quality'] == 1 else rules['range']
    low, high = bounds['min'], bounds['max']
    for row in decoded:
        stat = row.get('memory_stat', {})
        skill = catalog['skills'].get(str(stat.get('layer')), {})
        if (
            stat.get('id') != StatId.CLASS_SINGLE_SKILL
            or row['status'] != 'decoded'
            or skill.get('class') != class_name
            or 'roll_range' in row
        ):
            continue
        row['staffmod_range'] = {**bounds, 'source': rules['source']}
        value = row['value']
        if flags & RUNEWORD_FLAG or not low <= value <= high:
            row['text'] += f' [staffmod range: {low}-{high}; total contributions unverified]'
            continue
        # Keep decoder labels and market facets unchanged; annotate only presentation.
        label = row['text'].replace(f'+{value} to ', '+{{value}} to ', 1)
        row['range_label'] = label
        if low == high:
            row['text'] = label.replace('{{value}}', f'{value} ({low}-{high})')
        else:
            annotate_roll_ranges(
                [row],
                {
                    'roll_ranges': {f'{stat["id"]}:{stat["layer"]}': {**bounds, 'layer': stat['layer']}},
                    'source': rules['source'],
                    'scope': 'native staffmod magnitude; not an affix tier',
                },
            )
