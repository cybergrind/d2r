"""Render captured totals with separately verified intrinsic roll evidence."""

from inventory_tracking.appraisal.damage import display_damage
from inventory_tracking.items.ranges import annotate_roll_ranges
from inventory_tracking.items.stat_constants import TOTAL_LABELS
from pricing.knowledge.assessment.domain.facts import FactStatus
from pricing.knowledge.assessment.domain.sockets import socket_state


ROLL_FIELDS = ('roll_range', 'roll_quality', 'roll_quality_range', 'roll_tier', 'roll_tier_count')


def display_stats(result):
    extraction = result.get('extraction', {})
    item = extraction.get('item', {})
    rows = extraction.get('decoded_stats', [])
    if item.get('rarity') not in ('unique', 'set'):
        return display_damage(rows, item)
    state = socket_state(
        item.get('sockets'),
        item.get('socket_contents'),
        item.get('socket_items', []),
        item.get('filled_sockets'),
        item.get('empty_sockets'),
    )
    occupancy_verified = (
        state.total.status == FactStatus.KNOWN
        and state.occupied.status == FactStatus.KNOWN
        and state.identities_complete
    )
    if state.total.status == FactStatus.KNOWN and (
        state.total.value == 0 or (occupancy_verified and state.occupied.value == 0)
    ):
        return display_damage(rows, item)
    tier = result.get('assessment', {}).get('trade_tier', {})
    intrinsic = tier.get('intrinsic_rolls', {}) if occupancy_verified else {}
    ranges = tier.get('intrinsic_roll_ranges', {})
    displayed = []
    for original in rows:
        row = dict(original)
        native = row.get('memory_stat') or next(iter(row.get('memory_stats', [])), {})
        key = f'{native.get("id")}:{native.get("layer")}'
        if key == '31:0' and row.get('roll_range', {}).get('scope') == 'unmodified non-ethereal base defense':
            # defense_range_context already compared the owned and total arrays.
            displayed.append(row)
            continue
        if key not in intrinsic and not any(field in row for field in ROLL_FIELDS):
            displayed.append(row)
            continue
        label = row.get('range_label') or row.get('label')
        if not label and native.get('id') in TOTAL_LABELS:
            label = TOTAL_LABELS[native['id']] + ': {{value}}'
        value = row.get('value')
        if row.get('status') != 'decoded' or not label or '{{value}}' not in label or type(value) not in (int, float):
            displayed.append(row)
            continue
        for field in ROLL_FIELDS:
            row.pop(field, None)
        row['text'] = label.replace('{{value}}', f'{value:g}')
        proof, bounds = intrinsic.get(key), ranges.get(key)
        if (
            proof
            and bounds
            and proof.get('observed') == value
            and all(type(proof.get(k)) is int for k in ('observed', 'socket', 'intrinsic'))
            and proof['socket'] >= 0
            and proof['intrinsic'] + proof['socket'] == value
        ):
            ranked = {**row, 'value': proof['intrinsic']}
            annotate_roll_ranges(
                [ranked],
                {
                    'roll_ranges': {key: bounds},
                    'source': tier.get('source', {}),
                    'scope': 'verified intrinsic item roll',
                },
            )
            if 'roll_range' in ranked:
                for field in ROLL_FIELDS:
                    if field in ranked:
                        row[field] = ranked[field]
                row['text'] += (
                    f' — item roll: {proof["intrinsic"]} ({bounds["min"]}-{bounds["max"]}), sockets: +{proof["socket"]}'
                )
        if 'roll_range' not in row:
            definition_range = original.get('roll_range', {})
            low, high = definition_range.get('min'), definition_range.get('max')
            if type(low) in (int, float) and type(high) in (int, float) and low < high:
                row['text'] += f' — item range: {low:g}-{high:g}'
        displayed.append(row)
    return display_damage(displayed, item)
