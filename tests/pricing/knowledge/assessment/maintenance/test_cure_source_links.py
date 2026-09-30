"""Cure source reviews must not turn Cleansing into unsupported Prayer healing."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
EXPECTED = {
    'nova-sorceress-guide-1-merc-cure': ('Sorceress', 'ci3', ('Act 2 Holy Freeze', 'Act 2 Might')),
    'nova-sorceress-guide-2-merc-cure': ('Sorceress', 'ci3', ('Act 2 Holy Freeze', 'Act 2 Might')),
    'nova-sorceress-guide-3-merc-cure': ('Sorceress', 'ci3', ('Act 2 Holy Freeze', 'Act 2 Might')),
    'enchant-sorceress-1-merc-cure': ('Sorceress', 'usk', ('Act 2 Prayer',)),
    'enchant-sorceress-2-merc-cure': ('Sorceress', 'usk', ('Act 2 Prayer',)),
    'echoing-strike-warlock-guide-1-merc-cure': ('Warlock', 'xrn', ('Act 2 Prayer',)),
    'echoing-strike-warlock-guide-2-merc-cure': ('Warlock', 'xrn', ('Act 2 Prayer',)),
}


def test_cure_source_links_preserve_healing_and_equipment_conditions():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 7
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == set(EXPECTED)
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        klass, base, mercs = EXPECTED[row['profile_id']]
        assert row['required_predicates'] == [
            {'op': 'context_eq', 'field': 'player_class', 'value': klass},
            *[
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in (
                    ('identified', True),
                    ('runeword', 'Cure'),
                    ('sockets', 3),
                    ('socket_contents', 'filled'),
                    ('base_code', base),
                    ('ethereal', True),
                )
            ],
            {'any': [{'op': 'context_eq', 'field': 'mercenary_type', 'value': m} for m in mercs]},
        ]
        text = ' '.join(row['required_conditions'])
        assert 'requires an actual Prayer mercenary' in text
        if row['profile_id'].startswith('nova'):
            assert 'does not gain Prayer healing from Cure' in text
        else:
            assert 'Enchant uses Infinity, while Echoing Strike uses Insight' in text
