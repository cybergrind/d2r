"""Reviewed Hardcore prose spans, bounded by exact headings in the pinned HTML."""

import hashlib
import json
from datetime import date
from html import unescape

from pricing.knowledge.assessment.maintenance.guide_positions import PositionedMentions
from pricing.knowledge.assessment.maintenance.guide_spans import occurrence_source
from pricing.knowledge.assessment.maintenance.hardcore_bounds import validate_hardcore_bounds
from pricing.knowledge.assessment.maintenance.reward_mentions import FIELDS
from pricing.knowledge.assessment.policies.sources import resolve_pointer


def compile_hardcore_mentions(document, occurrences, root):
    if document is None:
        return []
    if document.get('schema_version') != 1 or not isinstance(document.get('rows'), list):
        raise ValueError('Invalid Hardcore review schema')
    indexed = {r['id']: r for r in occurrences}
    result, seen_ids, seen_occurrences, caches, guides = [], set(), set(), {}, {}
    for index, row in enumerate(document['rows']):
        rid, oid = row['id'], row['occurrence_id']
        if rid in seen_ids or oid in seen_occurrences:
            raise ValueError('Duplicate Hardcore occurrence review')
        seen_ids.add(rid)
        seen_occurrences.add(oid)
        date.fromisoformat(row['review_date'])
        occurrence = indexed.get(oid)
        if (
            not occurrence
            or occurrence.get('kind') != 'demand'
            or occurrence.get('variant') != 'Guide mention'
            or not isinstance(row.get('reason'), str)
            or not row['reason'].strip()
            or row.get('expected_occurrence') != {k: occurrence.get(k) for k in FIELDS}
        ):
            raise ValueError('Changed or unsupported Hardcore occurrence')
        ref = row['source']
        if ref['path'] != 'pricing/data/appraisal-guide-sections.json' or occurrence_source(ref) != (
            occurrence['source_id'],
            occurrence['source_locator'],
        ):
            raise ValueError('Hardcore reference must identify the exact guide span')
        key = ref['path'], ref['sha256']
        if key not in caches:
            raw = (root / ref['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != ref['sha256']:
                raise ValueError('Stale Hardcore cache')
            caches[key] = json.loads(raw)
        cache = caches[key]
        span = resolve_pointer(cache, ref['locator'])
        if (
            span != ref.get('expected')
            or span['label'] != occurrence['original_label']
            or any(span.get(k) != occurrence.get(k) for k in ('side', 'slot'))
        ):
            raise ValueError('Changed Hardcore span')
        gid = occurrence['source_id']
        guide = cache['sources'][gid]
        if gid not in guides:
            path = (root / gid).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError('Missing Hardcore HTML source')
            html = path.read_text()
            if hashlib.sha256(html.encode()).hexdigest() != guide['source_sha256']:
                raise ValueError('Stale Hardcore HTML source')
            parser = PositionedMentions()
            parser.feed(unescape(html))
            parser.close()
            if parser.mentions != guide['item_spans']:
                raise ValueError('Hardcore HTML spans disagree with cached evidence')
            # SectionParser positions refer to the original HTML, whereas guide_mentions
            # parses unescaped HTML. Align the same ordered spans, then use original positions.
            original = PositionedMentions()
            original.feed(html)
            original.close()
            if original.mentions != parser.mentions:
                raise ValueError('Ambiguous Hardcore HTML positions')
            guides[gid] = original.positions
        ordinal = int(ref['locator'].rsplit('/', 1)[1])
        validate_hardcore_bounds(guide['sections'], row['section_range'], guides[gid][ordinal])
        result.append(
            {
                'id': rid,
                'occurrence_id': oid,
                'state': 'excluded',
                'reason': row['reason'],
                'source': {'artifact': 'hardcore_reviews', 'locator': f'/rows/{index}'},
            }
        )
    return result
