"""Nova and Lightning Fury keep the actual Guardian's Thunder and casting scope."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
EXPECTED = {
    'nova-sorceress-guide-1-griffon-eye': 'Sorceress',
    'nova-sorceress-guide-3-griffon-eye': 'Sorceress',
    'lightning-fury-amazon-guide-2-griffon-eye': 'Amazon',
}


def test_griffon_tail_sources_retain_lightning_payload_and_build_qualifications():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == 3
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
            {'op': 'context_eq', 'field': 'player_class', 'value': EXPECTED[row['profile_id']]},
            *[
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in (
                    ('identified', True),
                    ('base_code', 'ci3'),
                    ('ethereal', False),
                    ('sockets', 1),
                    ('socket_contents', 'filled'),
                )
            ],
        ]
        assert row['required_dependencies'] == [
            {'op': 'socket_jewel_matches', 'count': 1, 'name': "Guardian's Thunder", 'stats': {'330:0': 5, '334:0': 5}},
        ]
        conditions = ' '.join(row['required_conditions'])
        assert 'does not establish a complete breakpoint' in conditions
        if row['profile_id'].startswith('lightning-fury'):
            assert 'not javelin attack speed' in conditions
        if row['profile_id'].startswith('nova-sorceress-guide-3'):
            assert 'do not increase Hydra fire damage' in conditions
