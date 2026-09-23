"""Annotate observed scalar values with separately sourced definition ranges."""

from typing import Any

from inventory_tracking.items.stat_constants import TOTAL_LABELS


def annotate_roll_ranges(decoded: list[dict[str, Any]], identity):
    if not identity:
        return
    for row in decoded:
        stat: dict[str, Any] = row.get('memory_stat') or next(iter(row.get('memory_stats', [])), {})
        definition = identity['roll_ranges'].get(f'{stat.get("id")}:{stat.get("layer")}')
        if definition is None:
            definition = identity['roll_ranges'].get(str(stat.get('id')))
        label = row.get('range_label') or row.get('label')
        if not label and stat.get('id') in TOTAL_LABELS:
            label = TOTAL_LABELS[stat['id']] + ': {{value}}'
        value = row.get('value')
        if (
            row['status'] != 'decoded'
            or not definition
            or stat.get('layer') != definition.get('layer', 0)
            or not label
            or '{{value}}' not in label
            or value is None
        ):
            continue
        low, high = definition['min'], definition['max']
        if low > high or (low == high and not definition.get('tiers')):
            continue
        # Total values can include socket/set contributions. Never turn an
        # out-of-range total into a claimed roll on this definition.
        if not low <= value <= high:
            continue
        row['roll_range'] = {
            **definition,
            'source': definition.get('source', identity['source']),
            'scope': identity.get('scope', 'item definition; not proof of contribution split'),
        }
        suffix = label.split('{{value}}', 1)[1]
        token = '{{value}}%' if suffix.startswith('%') else '{{value}}'
        unit = '%' if suffix.startswith('%') else ''
        better = definition.get('better', 'higher')
        quality_range = definition.get('quality_range')
        rank_low, rank_high = (quality_range['min'], quality_range['max']) if quality_range else (low, high)
        if rank_low < rank_high and rank_low <= value <= rank_high:
            fraction = (
                (value - rank_low) / (rank_high - rank_low)
                if better == 'higher'
                else (rank_high - value) / (rank_high - rank_low)
            )
            row['roll_quality'] = 'perfect' if fraction == 1 else 'low' if fraction <= 0.2 else 'normal'
            if quality_range:
                row['roll_quality_range'] = {
                    **quality_range,
                    'scope': identity.get('quality_scope', 'all spawnable tiers for this charm size'),
                }
        display_low, display_high = (rank_low, rank_high) if quality_range else (low, high)
        row['text'] = label.replace(token, f'{value}{unit} ({display_low}-{display_high}{unit})').replace('+-', '-')
        tiers = definition.get('tiers', [])
        tier = next((i for i, bounds in enumerate(tiers, 1) if (bounds['min'], bounds['max']) == (low, high)), None)
        if tier is not None:
            row['roll_tier'] = tier
            row['roll_tier_count'] = len(tiers)
            best = tiers[0]
            row['text'] += f' [T{tier}; T1: {best["min"]}-{best["max"]}{unit}]'
