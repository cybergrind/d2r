"""Explicit source-only exclusions for reviewed area/reward table occurrences."""

import hashlib
import json
from datetime import date

from pricing.knowledge.assessment.maintenance.guide_positions import require_same_section
from pricing.knowledge.assessment.maintenance.guide_spans import occurrence_source
from pricing.knowledge.assessment.maintenance.source_context_reviews import OCCURRENCE_FIELDS, PLAYER_SLOTS
from pricing.knowledge.assessment.policies.sources import resolve_pointer


FIELDS = (*OCCURRENCE_FIELDS, 'id', 'kind', 'class')
EQUIPMENT_SLOTS = PLAYER_SLOTS | {'Helmet', 'Body Armor', 'unspecified'}


def compile_reward_mentions(document, occurrences, root):
    if document is None:
        return []
    if document.get('schema_version') != 1 or not isinstance(document.get('rows'), list):
        raise ValueError('Invalid reward mention review schema')
    indexed = {row['id']: row for row in occurrences}
    result, seen_ids, seen_occurrences, cache = [], set(), set(), {}

    def reference(ref):
        if ref.get('path') != 'pricing/data/appraisal-guide-sections.json':
            raise ValueError('Reward review needs the pinned guide cache')
        key = ref['path'], ref['sha256']
        if key not in cache:
            path = (root / ref['path']).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError('Missing reward evidence')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != ref['sha256']:
                raise ValueError('Stale reward evidence')
            cache[key] = json.loads(raw)
        return resolve_pointer(cache[key], ref['locator'])

    positions = {}
    for index, row in enumerate(document['rows']):
        rid, oid = row['id'], row['occurrence_id']
        if rid in seen_ids or oid in seen_occurrences:
            raise ValueError('Duplicate reward mention review')
        seen_ids.add(rid)
        seen_occurrences.add(oid)
        date.fromisoformat(row['review_date'])
        occurrence = indexed.get(oid)
        if (
            row.get('kind') not in ('farming_reward', 'farming_target')
            or not isinstance(row.get('reason'), str)
            or not row['reason'].strip()
            or not occurrence
            or occurrence.get('kind') != 'demand'
            or occurrence.get('variant') != 'Guide mention'
            or occurrence.get('side') != 'player'
            or not occurrence.get('slot')
            or not supported_context(row, occurrence)
            or row.get('expected_occurrence') != {key: occurrence.get(key) for key in FIELDS}
        ):
            raise ValueError('Changed or unsupported reward occurrence')
        source = row['source']
        if occurrence_source(source) != (occurrence['source_id'], occurrence['source_locator']):
            raise ValueError('Reward reference does not identify the exact occurrence')
        span = reference(source)
        if (
            span != source.get('expected')
            or span.get('label') != occurrence['original_label']
            or any(span.get(key) != occurrence[key] for key in ('side', 'slot'))
        ):
            raise ValueError('Changed reward span')
        evidence = row['evidence']
        prefix = source['locator'].split('/item_spans/')[0] + '/sections/'
        quote = evidence.get('quote')
        if (
            evidence.get('path') != source['path']
            or evidence.get('sha256') != source['sha256']
            or not evidence.get('locator', '').startswith(prefix)
            or not isinstance(quote, str)
            or not quote.strip()
        ):
            raise ValueError('Reward rationale needs a quote from the same guide')
        passage = reference(evidence)
        if not isinstance(passage, str) or quote not in passage or not supported_quote(row, occurrence, quote):
            raise ValueError('Reward quote must identify the area, reward and table context')
        if row['kind'] == 'farming_target':
            if passage.count(occurrence['original_label']) != 1:
                raise ValueError('Ambiguous reward target: repeated name in section needs a narrower review')
            guide = cache[(source['path'], source['sha256'])]['sources'][occurrence['source_id']]
            require_same_section(root, occurrence, guide, evidence, positions, label='reward')
        result.append(
            {
                'id': rid,
                'occurrence_id': oid,
                'state': 'excluded',
                'reason': row['reason'],
                'source': {'artifact': 'reward_reviews', 'locator': f'/rows/{index}'},
            }
        )
    return result


def supported_context(row, occurrence):
    if row['kind'] == 'farming_reward':
        return occurrence['slot'] not in EQUIPMENT_SLOTS
    return (
        occurrence['slot'] == 'unspecified'
        and occurrence.get('name') == occurrence.get('original_label')
        and (occurrence.get('name'), occurrence.get('category'))
        in {('Hellfire Torch', 'unique'), ('Key of Destruction', 'misc')}
    )


def supported_quote(row, occurrence, quote):
    if row['kind'] == 'farming_reward':
        return all(token in quote for token in ('Area', 'Rewards', occurrence['slot'], occurrence['original_label']))
    if occurrence['name'] == 'Hellfire Torch':
        return (
            'Farm Hellfire Torches with this build to use it to its full potential!' in quote
            or 'defeating the Uber Bosses and acquiring a Hellfire Torch' in quote
        )
    return 'Nihlathak' in quote and 'farming this Boss for the Key of Destruction' in quote
