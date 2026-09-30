"""Exact guide-use bindings for reviewed consumables, separate from equipped roles."""

import hashlib
import json
from datetime import date

from pricing.knowledge.assessment.maintenance.guide_positions import require_same_section
from pricing.knowledge.assessment.maintenance.guide_spans import occurrence_source
from pricing.knowledge.assessment.maintenance.reward_mentions import FIELDS
from pricing.knowledge.assessment.policies.consumables import (
    HEALING,
    REJUVENATION,
    RESISTANCE,
    SOURCE_SHA256,
    definitions,
)
from pricing.knowledge.assessment.policies.sources import resolve_pointer


GUIDE_CACHE = 'pricing/data/appraisal-guide-sections.json'
NATIVE = 'third-parties/d2data/json/misc.json'


def compile_utility_source_reviews(document, occurrences, root):
    if document is None:
        return []
    if document.get('schema_version') != 1 or not isinstance(document.get('rows'), list):
        raise ValueError('Invalid utility source review schema')
    indexed = {r['id']: r for r in occurrences}
    result, seen_ids, seen_occurrences, cached = [], set(), set(), {}

    def reference(ref):
        if ref.get('path') not in (GUIDE_CACHE, NATIVE):
            raise ValueError('Unsupported utility evidence path')
        key = ref['path'], ref['sha256']
        if key not in cached:
            path = (root / ref['path']).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError('Missing utility evidence')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != ref['sha256']:
                raise ValueError('Stale utility evidence')
            cached[key] = definitions(raw) if ref['path'] == NATIVE else json.loads(raw)
        return resolve_pointer(cached[key], ref['locator'])

    positions = {}
    for index, row in enumerate(document['rows']):
        rid, oid = row['id'], row['occurrence_id']
        if rid in seen_ids or oid in seen_occurrences:
            raise ValueError('Duplicate utility source review')
        seen_ids.add(rid)
        seen_occurrences.add(oid)
        date.fromisoformat(row['review_date'])
        occurrence = indexed.get(oid)
        if (
            not occurrence
            or occurrence.get('kind') != 'demand'
            or occurrence.get('identity_status') != 'resolved'
            or occurrence.get('category') != 'misc'
            or occurrence.get('variant') != 'Guide mention'
            or occurrence.get('side') not in ('merc', 'player')
            or occurrence.get('slot') != 'unspecified'
            or row.get('expected_occurrence') != {k: occurrence.get(k) for k in FIELDS}
            or not isinstance(row.get('reason'), str)
            or not row['reason'].strip()
        ):
            raise ValueError('Changed or unsupported utility occurrence')
        source = row['source']
        if source.get('path') != GUIDE_CACHE or occurrence_source(source) != (
            occurrence['source_id'],
            occurrence['source_locator'],
        ):
            raise ValueError('utility reference must identify the exact occurrence')
        span = reference(source)
        if (
            span != source.get('expected')
            or any(span.get(k) != occurrence.get(k) for k in ('side', 'slot'))
            or span.get('label') != occurrence['original_label']
        ):
            raise ValueError('Changed utility span')
        evidence = row['evidence']
        prefix = source['locator'].split('/item_spans/')[0] + '/sections/'
        quote = evidence.get('quote')
        if (
            evidence.get('path') != source['path']
            or evidence.get('sha256') != source['sha256']
            or not evidence.get('locator', '').startswith(prefix)
            or not isinstance(quote, str)
            or occurrence['original_label'] not in quote
            or 'mercenary' not in quote.lower()
            or quote not in reference(evidence)
        ):
            raise ValueError('Unsupported utility recipient quote')
        if occurrence['side'] == 'player' and (
            row.get('recipient_correction') != 'explicit_mercenary_instruction'
            or not explicit_mercenary_instruction(occurrence['original_label'], quote)
        ):
            raise ValueError('Unproven utility recipient correction')
        guide = cached[(source['path'], source['sha256'])]['sources'][occurrence['source_id']]
        require_same_section(root, occurrence, guide, evidence, positions)
        policy = row['policy']
        code = policy.get('id', '').removeprefix('consumable:')
        allowed = HEALING | REJUVENATION | RESISTANCE.keys()
        if (
            code not in allowed
            or policy.get('id') != 'consumable:' + code
            or policy.get('recipient') != 'mercenary'
            or row.get('item_bank_target') != policy['id']
        ):
            raise ValueError('Unreviewed utility policy or recipient')
        native = policy['native_source']
        if native != {'path': NATIVE, 'sha256': SOURCE_SHA256, 'locator': '/' + code}:
            raise ValueError('Unsupported utility native definition')
        definition = reference(native)
        if definition['name'] != occurrence['name'] or definition['name'] != occurrence['original_label']:
            raise ValueError('utility policy identity does not match the occurrence')
        result.append(
            {
                'id': rid,
                'occurrence_id': oid,
                'state': 'reviewed',
                'reason': row['reason'],
                'policy_id': policy['id'],
                'item_bank_target': row['item_bank_target'],
                'source': {'artifact': 'utility_reviews', 'locator': f'/rows/{index}'},
            }
        )
    return result


def explicit_mercenary_instruction(name, quote):
    if name in ('Thawing Potion', 'Antidote Potion'):
        return 'The Mercenary also gains bonus Resistances from Thawing Potions and Antidote Potions.' in quote
    if name == 'Healing Potion':
        return (
            'The Mercenary is hard to keep alive' in quote and 'directly feed them a Healing Potion from your' in quote
        )
    return False
