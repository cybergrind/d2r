"""Audit structured variant slots against immutable occurrence locators.

Representation is not semantic review. Missing sides and delta inheritance remain
explicit; this audit never manufactures inherited equipment or recommendations.
"""

from collections import defaultdict
from copy import deepcopy


def audit_variant_slots(document, source, occurrences, *, prefix='', escape=True):
    index = defaultdict(list)
    for row in occurrences:
        if row['source_id'] == source:
            index[row['source_locator']].append(row)
    slots, sides = [], []
    for number, variant in enumerate(document.get('variants', [])):
        context = {k: deepcopy(v) for k, v in variant.items() if k not in {'player', 'merc'}}
        for side in ('player', 'merc'):
            side_prefix = f'{prefix}/variants/{number}/{side}'
            equipment = variant.get(side)
            sides.append(
                {
                    'locator': side_prefix,
                    'status': 'present' if isinstance(equipment, dict) else 'absent',
                    'build': document['slug'],
                    'variant': variant['name'],
                    'side': side,
                }
            )
            if not isinstance(equipment, dict):
                continue
            for slot, value in equipment.items():
                locator = side_prefix + '/' + (slot.replace('~', '~0').replace('/', '~1') if escape else slot)
                record = {
                    'source_id': source,
                    'locator': locator,
                    'build': document['slug'],
                    'variant': variant['name'],
                    'side': side,
                    'slot': slot,
                    'variant_context': context,
                    'value': deepcopy(value),
                    'occurrence_ids': [],
                    'missing_locators': [],
                    'conflicting_occurrence_ids': [],
                }
                inspect_slot(record, index)
                slots.append(record)
    return {
        'source_id': source,
        'slots': slots,
        'sides': sides,
        'complete': False,
        'scope': 'Structured variant slot representation only; inheritance and semantic review remain pending.',
    }


def inspect_slot(record, index):
    slot, value, locator = record['slot'], record['value'], record['locator']
    if (slot in {'type', '_source'} and isinstance(value, str)) or (slot == '_text_only' and isinstance(value, bool)):
        record['status'] = 'context'
    elif not isinstance(value, list) or any(not isinstance(label, str) for label in value):
        record['status'] = 'unsupported_shape'
    else:
        record['status'] = 'represented' if value else 'empty'
        for ordinal, label in enumerate(value):
            item_locator = f'{locator}/{ordinal}'
            candidates = index.get(item_locator, [])
            matches = [r['id'] for r in candidates if r.get('original_label') == label]
            conflicts = [r['id'] for r in candidates if r.get('original_label') != label]
            record['occurrence_ids'].extend(matches)
            record['conflicting_occurrence_ids'].extend(conflicts)
            if not matches:
                record['missing_locators'].append(item_locator)
        if record['missing_locators']:
            record['status'] = 'missing_occurrences'
        if record['conflicting_occurrence_ids']:
            record['status'] = 'conflict'
        if slot == 'Mercenary Type' and record['status'] in {'represented', 'empty'}:
            record['status'] = 'context'


def audit_build_slots(documents, source, occurrences):
    """Consolidated extractor uses legacy unescaped locators; retain them exactly."""
    index = defaultdict(list)
    for row in occurrences:
        if row['source_id'] == source:
            index[row['source_locator']].append(row)
    slots, sides = [], []
    for slug, document in sorted(documents.items()):
        variants = audit_variant_slots({'slug': slug, **document}, source, occurrences, prefix=f'/{slug}', escape=False)
        slots.extend(variants['slots'])
        sides.extend(variants['sides'])
        entries = [
            (f'/{slug}/slots/{slot}', 'player', slot, 'Main alternatives', value)
            for slot, value in document.get('slots', {}).items()
        ]
        for slot, stages in document.get('merc', {}).items():
            if isinstance(stages, dict):
                entries.extend(
                    (f'/{slug}/merc/{slot}/{stage}', 'merc', slot, stage, value) for stage, value in stages.items()
                )
            else:
                entries.append((f'/{slug}/merc/{slot}', 'merc', slot, 'unspecified', stages))
        if 'prose_only_items' in document:
            entries.append(
                (
                    f'/{slug}/prose_only_items',
                    'unspecified',
                    'unspecified',
                    'Prose alternatives',
                    document['prose_only_items'],
                )
            )
        for locator, side, slot, variant, value in entries:
            record = {
                'source_id': source,
                'locator': locator,
                'build': slug,
                'variant': variant,
                'side': side,
                'slot': slot,
                'value': deepcopy(value),
                'variant_context': {},
                'occurrence_ids': [],
                'missing_locators': [],
                'conflicting_occurrence_ids': [],
            }
            inspect_slot(record, index)
            slots.append(record)
    return {
        'source_id': source,
        'slots': slots,
        'sides': sides,
        'complete': False,
        'scope': 'Consolidated tables; raw source completeness and semantic review remain pending.',
    }
