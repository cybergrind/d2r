"""Display bounded recipe rolls including fixed, verified rune contributions."""

from inventory_tracking.items.metadata import metadata
from inventory_tracking.items.ranges import annotate_roll_ranges
from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.mechanics.runeword_rolls import BOUNDED_STATS, enhancement_gaps
from pricing.knowledge.assessment.registry import classify
from pricing.knowledge.definition_store import catalog


ROLL_FIELDS = ('roll_range', 'roll_quality', 'roll_quality_range', 'roll_tier', 'roll_tier_count')


def verified_recipe(facts, definition, family):
    return (
        facts.identified is True
        and facts.rarity in ('normal', 'superior', 'low_quality')
        and facts.base_code in definition['base_codes']
        and family in definition.get('socket_bonus_ranges', {})
        and facts.socket_contents == 'filled'
        and facts.sockets == len(definition['runes'])
        and tuple(child.get('base_code') for child in facts.socket_items) == tuple(definition['runes'])
    )


def enhancement_row(original, native, facts, definition, family, spec, bonus, verified):
    """Grade observed enhancement totals, retaining gaps in superior outcomes."""
    stat = native['id']
    row = {k: v for k, v in original.items() if k not in ROLL_FIELDS}
    label = row.get('range_label') or row.get('label')
    value = row.get('value')
    if not label or '{{value}}' not in label or type(value) not in (int, float):
        return row
    row['text'] = label.replace('{{value}}', f'{value:g}')
    supported = (stat in (17, 18) and family == 'weapon') or (stat == 16 and family in ('armor', 'helm'))
    if not verified or not supported or native.get('layer') != 0:
        return row
    # A recipe may have no enhancement of its own (Enigma, Flickering Flame).
    spec = spec or {'stat_id': stat, 'min': 0, 'max': 0}
    if bonus['min'] != bonus['max'] or enhancement_gaps(facts, spec, bonus, value, family):
        return row
    extra = 0
    if facts.rarity == 'superior':
        category = 'weapons' if family == 'weapon' else 'armor'
        superior = metadata()['superior'][category]['roll_ranges'].get(str(stat))
        if not superior:
            return row
        extra = superior['max']
    low, high = spec['min'] + bonus['min'], spec['max'] + bonus['max'] + extra
    if low == high:
        return row  # Fixed totals have no roll quality.
    annotate_roll_ranges(
        [row],
        {
            'roll_ranges': {str(stat): {**spec, 'min': low, 'max': high}},
            'source': definition['source'],
            'scope': 'runeword recipe and rune enhancement plus possible superior base contribution',
        },
    )
    return row


def display_runeword_rolls(extraction):
    rows = extraction.get('decoded_stats', [])
    facts = normalize(extraction)
    definition = catalog().runewords.get(facts.runeword)
    if not definition:
        return rows
    family, _ = classify(facts)
    socket_ranges = definition.get('socket_bonus_ranges', {})
    bonuses = socket_ranges.get(family, {})
    verified = verified_recipe(facts, definition, family)
    displayed = []
    for original in rows:
        native = original.get('memory_stat') or next(iter(original.get('memory_stats', [])), {})
        key = f'{native.get("id")}:{native.get("layer")}'
        ranges = definition.get('roll_ranges', {})
        spec = ranges.get(key) or ranges.get(str(native.get('id')))
        bonus = bonuses.get(key) or bonuses.get(str(native.get('id'))) or {'min': 0, 'max': 0}
        enhancement = native.get('id') in (16, 17, 18)
        if enhancement:
            displayed.append(enhancement_row(original, native, facts, definition, family, spec, bonus, verified))
            continue
        # An unknown/incompatible base must not retain a recipe-only color for
        # a total that needs rune contributions on a supported base.
        possible_bonuses = [bounds.get(key) or bounds.get(str(native.get('id'))) for bounds in socket_ranges.values()]
        shifted = any(b and b['min'] == b['max'] and b['min'] > 0 for b in possible_bonuses)
        if (
            not spec
            or not shifted
            or spec['stat_id'] not in BOUNDED_STATS
            or native.get('layer') != spec.get('layer', 0)
            or spec['min'] == spec['max']
        ):
            displayed.append(original)
            continue
        row = {k: v for k, v in original.items() if k not in ROLL_FIELDS}
        label = row.get('range_label') or row.get('label')
        value = row.get('value')
        if label and '{{value}}' in label and type(value) in (int, float):
            row['text'] = label.replace('{{value}}', f'{value:g}')
            if verified and bonus and bonus['min'] == bonus['max']:
                annotate_roll_ranges(
                    [row],
                    {
                        'roll_ranges': {
                            key: {**spec, 'min': spec['min'] + bonus['min'], 'max': spec['max'] + bonus['max']}
                        },
                        'source': definition['source'],
                        'scope': 'runeword recipe plus fixed rune contribution',
                    },
                )
        displayed.append(row)
    return displayed
