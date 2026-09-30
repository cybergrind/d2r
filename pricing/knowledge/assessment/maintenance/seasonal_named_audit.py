"""Preserve evidence of seasonal unique overlays before reviewing their variants.

This audit does not establish transfer availability or select an ordinary/seasonal
variant from an item ID shared by both. Those remain separate implementation work.
"""

import hashlib
import json

from pricing.knowledge.assessment.maintenance.inventory import ROOT
from pricing.knowledge.refresh import atomic_json


BASE = 'third-parties/d2data/json/base/uniqueitems.json'
OVERLAY = 'pricing/raw/d2data/uniqueitems.json'
OUTPUT = 'pricing/data/appraisal-seasonal-named-audit.json'


def audit(ordinary, seasonal):
    rows = []
    for key, record in seasonal.items():
        if not any(record.get(k) for k in ('firstLadderSeason', 'lastLadderSeason')):
            continue
        original = ordinary.get(key)
        if original == record:
            continue
        state = 'requires_variant_support'
        if original is None:
            state = 'ordinary_definition_missing'
        elif any(original.get(k) != record.get(k) for k in ('*ID', 'index', 'code')):
            state = 'identity_conflict'
        before = original or {}
        differences = {
            field: {
                'ordinary_present': field in before,
                'seasonal_present': field in record,
                'ordinary': before.get(field),
                'seasonal': record.get(field),
            }
            for field in sorted(before.keys() | record.keys())
            if (field in before, before.get(field)) != (field in record, record.get(field))
        }
        if state == 'requires_variant_support' and set(differences) <= {'disableChronicle'}:
            state = 'requires_mode_review'
        rows.append(
            {
                'table_key': key,
                'name': record['index'],
                'state': state,
                'ordinary': original,
                'seasonal': record,
                'differences': differences,
            }
        )
    return rows


def build(root):
    paths = (BASE, OVERLAY)
    sources = {p: (root / p).read_bytes() for p in paths}
    return {
        'schema_version': 1,
        'inputs': {p: hashlib.sha256(raw).hexdigest() for p, raw in sources.items()},
        'limits': [
            'Season restrictions do not prove Non-Ladder transfer availability.',
            'A shared native table ID alone cannot distinguish these versions.',
            'Audit findings are required work, not reviewed pricing dispositions.',
        ],
        'rows': audit(*(json.loads(sources[p]) for p in paths)),
    }


def completion_tasks(document, root):
    """Derive unresolved Non-Ladder correctness work from current native differences.

    This is not a disposition reader: an audit cannot certify its own resolution.
    Reviewed runtime/version-selection evidence is still separate required work.
    """
    if document != build(root):
        raise ValueError('Stale or incomplete seasonal definition audit')
    return [
        {
            'id': 'seasonal_definition:' + row['table_key'],
            'dimension': 'source_review',
            'state': 'pending',
            'reason': (
                f'{row["name"]}: {row["state"]}; resolve ordinary/seasonal definition '
                'or mode-eligibility differences for Non-Ladder correctness. '
                'This does not establish seasonal transfer availability or Ladder demand.'
            ),
        }
        for row in document['rows']
    ]


def main():
    result = build(ROOT)
    atomic_json(ROOT / OUTPUT, result)
    print(json.dumps([{'name': r['name'], 'state': r['state']} for r in result['rows']]))


if __name__ == '__main__':
    main()
