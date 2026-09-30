"""Ravenlore's Ubers endorsement retains its actual Fire Facet dependency."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
IDS = {'fissure-player-standard-ravenlore', 'fissure-player-ubers-ravenlore'}


def test_ravenlore_sources_keep_native_choice_separate_from_socket_setup():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in IDS
    ]
    assert len(rows) == 2
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        assert row['required_predicates'] == [
            {'op': 'context_eq', 'field': 'player_class', 'value': 'Druid'},
            {'op': 'fact_eq', 'field': 'ethereal', 'value': False},
        ]
        deps = row.get('required_dependencies', [])
        if 'standard' in row['profile_id']:
            assert deps == []
        else:
            assert deps == [
                {
                    'all': [
                        {'op': 'fact_eq', 'field': 'sockets', 'value': 1},
                        {'op': 'fact_eq', 'field': 'socket_contents', 'value': 'filled'},
                        {'op': 'socket_jewel_matches', 'name': 'Rainbow Facet', 'stats': {'329:0': 3, '333:0': 3}},
                        {'not': {'op': 'socket_jewel_matches', 'name': 'Rainbow Facet', 'stats': {'329:0': 6}}},
                        {'not': {'op': 'socket_jewel_matches', 'name': 'Rainbow Facet', 'stats': {'333:0': 6}}},
                    ]
                }
            ]
