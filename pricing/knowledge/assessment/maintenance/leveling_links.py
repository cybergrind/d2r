"""Link cached generic recommendations to existing conditional runtime policies.

Maintenance only. Exact source content establishes the link, not a name match.
This describes policy applicability without evaluating a captured item.
"""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.policies import generic_leveling, socket_leveling


MATCH_FIELDS = ('name', 'source_timestamp', 'slots', 'context', 'market_evidence')
SOCKET_POLICIES = {
    1: 'topaz_magic_find',
    5: 'resistance_setup',
    7: 'diamond_resistance',
    9: 'resistance_setup',
    10: 'resistance_setup',
}


def _implementation(module, symbol):
    path = Path(module.__file__)
    return {'symbol': module.__name__ + '.' + symbol, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def compile_leveling_links(recommendations):
    raw = generic_leveling.SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != generic_leveling.SOURCE_SHA256:
        raise ValueError('Stale generic leveling source; review policies before linking')
    source = json.loads(raw)
    by_index = defaultdict(list)
    for pattern in generic_leveling.PATTERNS:
        by_index[pattern.source_index].append(
            {
                'implementation': _implementation(generic_leveling, 'Pattern.matches'),
                'item_types': sorted(pattern.item_types),
                'qualities': list(pattern.qualities),
                'side': pattern.side,
                'ethereal_guard': 'any' if pattern.side == 'mercenary' else False,
                'impossible_ethereal_sets_excluded': True,
                'required_stat_groups': [list(group) for group in pattern.stat_groups],
                'stat_semantics': 'Positive known native stat: OR within group, AND across groups.',
                'archetype': pattern.archetype,
                'condition': pattern.condition,
            }
        )
    for index, symbol in SOCKET_POLICIES.items():
        by_index[index].append(
            {
                'implementation': _implementation(socket_leveling, symbol),
                'source_index': index,
                'side': 'player',
                'ethereal_guard': False,
                'applicability': (
                    'Exact slot/quality, filler linkage and observed effects are enforced by the referenced policy.'
                ),
                'condition': 'Current leveling need and equipment requirements remain conditional.',
            }
        )
    reviewed = {
        fingerprint({k: row.get(k) for k in MATCH_FIELDS}): (index, row)
        for index, row in enumerate(source['generic_patterns'])
    }
    sources = {r['id']: r for r in recommendations.get('sources', [])}
    links = {}
    for row in recommendations.get('patterns', []):
        match = reviewed.get(fingerprint({k: row.get(k) for k in MATCH_FIELDS}))
        if not match or sources.get(row.get('source_id'), {}).get('url') != source['source']['url']:
            continue
        index, original = match
        if index not in by_index:
            continue
        links[fingerprint(row)] = {
            'id': f'generic-leveling:{index}',
            'name': original['name'],
            'source': {
                'path': str(generic_leveling.SOURCE.relative_to(generic_leveling.SOURCE.parents[2])),
                'sha256': generic_leveling.SOURCE_SHA256,
                'locator': f'/generic_patterns/{index}',
                'date': '2025-04-24',
            },
            'common_guards': {'identified': True},
            'policies': by_index[index],
            'status': 'reviewed_conditional_use',
        }
    return links
