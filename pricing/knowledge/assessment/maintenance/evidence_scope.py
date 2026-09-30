"""Reviewed generic recommendations, separate from their items and useful builds."""

import hashlib
import json
from datetime import date

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.value_scope import SCOPE


SOURCE = 'pricing/data/appraisal-leveling-candidates-2026-09-23.json'


def evidence_exclusions(rows, review, root):
    if review is None:
        return {}
    if review.get('schema_version') != 1 or review.get('scope') != SCOPE:
        raise ValueError('Unsupported evidence scope review')
    indexed = {row['id']: row for row in rows}
    result = {}
    for index, entry in enumerate(review.get('evidence', [])):
        key = entry['row_id']
        row = indexed.get(key)
        if (
            key in result
            or row is None
            or entry.get('row_sha256') != fingerprint(row)
            or row.get('kind') != 'evidence'
            or row.get('evidence_kind') != 'leveling_pattern'
            or row.get('identity_ids') != []
            or row.get('candidate_identity_ids') != []
            or row.get('quality') is not None
            or entry.get('classification') != 'generic_leveling'
            or not isinstance(entry.get('reason'), str)
            or not entry['reason'].strip()
        ):
            raise ValueError('Invalid or changed evidence scope target')
        date.fromisoformat(entry.get('reviewed_at', ''))
        source = entry.get('source', {})
        path = root / SOURCE
        locator = source.get('locator', '')
        number = locator.removeprefix('/generic_patterns/')
        if (
            source.get('path') != SOURCE
            or not path.resolve().is_relative_to(root.resolve())
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != source.get('sha256')
            or not locator.startswith('/generic_patterns/')
            or not number.isascii()
            or not number.isdecimal()
            or str(int(number)) != number
        ):
            raise ValueError('Stale or invalid evidence scope source')
        patterns = json.loads(path.read_text())['generic_patterns']
        if int(number) >= len(patterns):
            raise ValueError('Missing evidence scope source row')
        original = patterns[int(number)]
        evidence = row.get('evidence', {})
        if (
            not original.get('context')
            or entry.get('quote') != original['context']
            or row.get('name') != original.get('name')
            or any(evidence.get(k) != v for k, v in original.items())
            or evidence.get('source_id') != 'mrllamasc-transcript'
            or evidence.get('kind') != 'recommendation_pattern'
            or evidence.get('intent') != 'pattern'
            or row.get('source') != {'artifact': 'recommendations', 'locator': f'/patterns/{number}'}
            or key != f'evidence:recommendations:patterns:{number}'
        ):
            raise ValueError('Unverified evidence scope source correspondence')
        result[key] = {
            'state': 'excluded',
            'reason': entry['reason'],
            'source': {'artifact': 'value_scope', 'locator': f'/evidence/{index}'},
        }
    return result
