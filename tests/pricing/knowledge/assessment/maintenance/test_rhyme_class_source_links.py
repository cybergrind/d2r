"""Class-specific Rhyme endorsements retain every required staffmod and base."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
EXPECTED = {
    'blessed-hammer-paladin-0-rhyme': ('Paladin', 'pa1', ()),
    'poison-nova-necromancer-0-rhyme': ('Necromancer', 'ne7', ((92, 2),)),
    'echoing-strike-warlock-guide-0-rhyme': ('Warlock', 'wa3', ((389, 1), (381, 1), (377, 1))),
    'smite-paladin-0-rhyme': ('Paladin', 'pa1', ()),
    'fire-warlock-guide-0-rhyme': ('Warlock', 'wa3', ()),
}


def test_rhyme_sources_preserve_class_base_staffmods_and_active_set():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 5
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert all(row['state'] == 'reviewed' for row in result)
    for row in rows:
        klass, base, skills = EXPECTED[row['profile_id']]
        assert row['required_predicates'] == [
            {'op': 'context_eq', 'field': 'player_class', 'value': klass},
            *[
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in (
                    ('identified', True),
                    ('base_code', base),
                    ('runeword', 'Rhyme'),
                    ('sockets', 2),
                    ('socket_contents', 'filled'),
                    ('ethereal', False),
                )
            ],
            *[
                {'op': 'stat_at_least', 'key': f'107:{skill}', 'value': value, 'absent_is_zero': True}
                for skill, value in skills
            ],
        ]
        conditions = ' '.join(row['required_conditions'])
        assert 'empty two-socket preparation base' in conditions
        if skills:
            assert 'All specified staffmods are required together' in conditions
        if row['profile_id'].startswith('blessed-hammer'):
            assert 'only with this swap set active' in conditions
        if row['profile_id'].startswith('smite'):
            assert 'better base target rather than minimum usefulness' in conditions
        if row['profile_id'].startswith('fire-warlock'):
            assert 'historical, not a second simultaneous offhand' in conditions
