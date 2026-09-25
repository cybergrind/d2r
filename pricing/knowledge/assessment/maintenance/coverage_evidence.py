"""Conservative identity links for leveling and valuable-item review evidence."""

from collections import defaultdict
from copy import deepcopy


NAMED_TABLE_QUALITIES = {'uniqueitems': 'unique', 'setitems': 'set'}


def evidence_records(identities, recommendations, valuable):
    by_name = defaultdict(list)
    for identity in identities.values():
        if identity.get('catalog_ids'):
            by_name[identity['category'], identity['name']].append('identity:' + identity['id'])
    inputs = [
        ('recommendations', 'rows', 'leveling', recommendations.get('rows', [])),
        ('recommendations', 'patterns', 'leveling_pattern', recommendations.get('patterns', [])),
        ('valuable', 'rows', 'valuable', valuable.get('rows', [])),
    ]
    for artifact, field, kind, records in inputs:
        for index, original in enumerate(records):
            quality = original.get('rarity')
            if kind == 'leveling':
                parts = original.get('item_id', '').split(':', 2)
                quality = NAMED_TABLE_QUALITIES.get(parts[1]) if len(parts) == 3 and parts[0] == 'd2data' else None
            candidates = sorted(by_name.get((quality, original['name']), []))
            linked = candidates if len(candidates) == 1 else []
            yield {
                'id': f'evidence:{artifact}:{field}:{index}',
                'kind': 'evidence',
                'evidence_kind': kind,
                'name': original['name'],
                'quality': quality,
                'identity_ids': linked,
                'candidate_identity_ids': candidates,
                'evidence': deepcopy(original),
                'source': {'artifact': artifact, 'locator': f'/{field}/{index}'},
            }
