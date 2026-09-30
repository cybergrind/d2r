"""Treachery source coverage preserves wearer, active-proc and encounter limits."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
EXPECTED = {
    'abyss-warlock-build-guide-0': ('Warlock', 'Act 2 Might', 'xtp', True),
    'gold-find-barbarian-0': ('Barbarian', 'Act 2 Might', 'xtp', False),
    'lightning-sorceress-3': ('Sorceress', 'Act 5 Frenzy', 'utp', False),
    'strafe-amazon-0': ('Amazon', 'Act 2 Might', 'xtp', True),
    'echoing-strike-warlock-guide-0': ('Warlock', 'Act 2 Blessed Aim', 'xtp', True),
    'summoner-necromancer-guide-0': ('Necromancer', 'Act 2 Might', 'brs', True),
    'lightning-strike-amazon-2': ('Amazon', 'Act 5 Frenzy', 'utp', True),
    'enchant-sorceress-0': ('Sorceress', 'Act 1 Fire', 'xtp', True),
    'dream-paladin-0': ('Paladin', 'Act 2 Might', 'utp', True),
    'nova-sorceress-guide-0': ('Sorceress', 'Act 2 Holy Freeze', 'ltp', True),
    'berserk-barbarian-1': ('Barbarian', 'Act 2 Might', 'utp', True),
    'meteor-sorceress-4': ('Sorceress', 'Act 2 Might', 'utp', False),
    'lightning-fury-amazon-guide-3': ('Amazon', 'Act 5 Frenzy', 'xtp', True),
    'fire-warlock-guide-0': ('Warlock', 'Act 2 Might', 'xtp', True),
}


def test_treachery_sources_preserve_exact_wearer_and_conditional_fade():
    def read(path):
        return json.loads((ROOT / path).read_text())

    ids = {key + '-merc-treachery-native' for key in EXPECTED}
    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in ids
    ]
    assert len(rows) == len(EXPECTED) == 14
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == ids
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        key = row['profile_id'].removesuffix('-merc-treachery-native')
        klass, merc, base, ethereal = EXPECTED[key]
        expected = [
            {'op': 'context_eq', 'field': 'player_class', 'value': klass},
            {'op': 'context_eq', 'field': 'mercenary_type', 'value': merc},
            *[
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in (
                    ('identified', True),
                    ('base_code', base),
                    ('runeword', 'Treachery'),
                    ('sockets', 3),
                    ('socket_contents', 'filled'),
                )
            ],
        ]
        eth = {'op': 'fact_eq', 'field': 'ethereal', 'value': True}
        expected.append(eth if ethereal else {'any': [eth, {**eth, 'value': False}]})
        if key == 'lightning-sorceress-3':
            expected.append({'op': 'context_eq', 'field': 'activity', 'value': 'Uber Mephisto'})
        assert row['required_predicates'] == expected
        text = ' '.join(row['required_conditions'])
        assert 'not proof of an active buff' in text
        assert 'player does not inherit mercenary IAS or resistances' in text
        if key == 'lightning-fury-amazon-guide-3':
            assert 'retain that wording conflict' in text
        if key == 'summoner-necromancer-guide-0':
            assert 'preserve that helmet conflict' in text
        if key == 'meteor-sorceress-4':
            assert 'not a durable shared-armor recommendation' in text
