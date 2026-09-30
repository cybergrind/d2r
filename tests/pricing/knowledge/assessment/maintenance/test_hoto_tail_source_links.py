"""Heart of the Oak source coverage preserves casting and swap qualifications."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
EXPECTED = {
    'gold-find-barbarian-1-heart-oak': ('Barbarian', True),
    'gold-find-barbarian-2-heart-oak': ('Barbarian', True),
    'gold-find-barbarian-3-heart-oak': ('Barbarian', False),
    'summoner-necromancer-guide-1-heart-oak': ('Necromancer', True),
}


def test_hoto_sources_keep_swap_and_single_weapon_limits():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED and not r.get('paired_swap')
    ]
    assert len(rows) == len(EXPECTED) == 4
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
        klass, ethereal = EXPECTED[row['profile_id']]
        expected = [
            {'op': 'context_eq', 'field': 'player_class', 'value': klass},
            *[
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in (
                    ('identified', True),
                    ('base_code', 'fla'),
                    ('runeword', 'Heart of the Oak'),
                    ('sockets', 4),
                    ('socket_contents', 'filled'),
                )
            ],
        ]
        if ethereal:
            expected.append({'op': 'fact_eq', 'field': 'ethereal', 'value': True})
        assert row['required_predicates'] == expected
        conditions = ' '.join(row['required_conditions'])
        assert 'does not increase physical attack speed' in conditions
        if row['profile_id'] == 'gold-find-barbarian-1-heart-oak':
            assert 'one captured weapon establishes only its own +3' in conditions
        if row['profile_id'] == 'gold-find-barbarian-3-heart-oak':
            assert 'six-Lem gold-find swap' in conditions
        if row['profile_id'].startswith('summoner'):
            assert '125%FCR setup' in conditions
