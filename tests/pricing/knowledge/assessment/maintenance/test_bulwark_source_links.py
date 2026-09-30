"""Bulwark source links retain each mercenary, base and known ethereal scope."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
# Independent source review: player class, base, allowed aura, requires ethereal.
EXPECTED = {
    'smite-paladin-0': ('Paladin', 'crn', ('Act 2 Holy Freeze',), False),
    'fist-of-the-heavens-paladin-1': ('Paladin', 'msk', ('Act 2 Might', 'Act 2 Holy Freeze'), False),
    'double-throw-barbarian-guide-0': ('Barbarian', 'crn', ('Act 2 Might',), True),
    'wake-of-fire-assassin-0': ('Assassin', 'ci2', ('Act 2 Might',), False),
    'abyss-warlock-build-guide-0': ('Warlock', 'uh9', ('Act 2 Might',), True),
    'echoing-strike-warlock-guide-0': ('Warlock', 'crn', ('Act 2 Blessed Aim',), True),
    'lightning-sorceress-0': ('Sorceress', 'xsk', ('Act 2 Holy Freeze',), False),
    'lightning-fury-amazon-guide-0': ('Amazon', 'xsk', ('Act 2 Might',), False),
    'enchant-sorceress-0': ('Sorceress', 'ci3', ('Act 1 Fire',), True),
    'poison-nova-necromancer-0': ('Necromancer', 'xsk', ('Act 2 Might',), False),
    'fist-of-the-heavens-paladin-0': ('Paladin', 'msk', ('Act 2 Might', 'Act 2 Holy Freeze'), False),
    'blessed-hammer-paladin-0': ('Paladin', 'crn', ('Act 2 Holy Freeze',), True),
    'lightning-sentry-assassin-0': ('Assassin', 'ci2', ('Act 2 Holy Freeze',), False),
    'blizzard-sorceress-0': ('Sorceress', 'ci3', ('Act 2 Might',), False),
    'strafe-amazon-0': ('Amazon', 'crn', ('Act 2 Might',), False),
    'fire-warlock-guide-0': ('Warlock', 'crn', ('Act 2 Might',), True),
    'lightning-strike-amazon-0': ('Amazon', 'xsk', ('Act 2 Holy Freeze',), False),
    'berserk-barbarian-0': ('Barbarian', 'xsk', ('Act 2 Might',), False),
    'nova-sorceress-guide-0': ('Sorceress', 'crn', ('Act 2 Holy Freeze',), False),
}


def test_bulwark_sources_preserve_base_wearer_ethereal_and_survival_qualifications():
    def read(path):
        return json.loads((ROOT / path).read_text())

    ids = {key + '-merc-bulwark-native' for key in EXPECTED}
    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in ids
    ]
    assert len(rows) == len(EXPECTED) == 19
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
        key = row['profile_id'].removesuffix('-merc-bulwark-native')
        klass, base, auras, ethereal = EXPECTED[key]
        mercs = [{'op': 'context_eq', 'field': 'mercenary_type', 'value': aura} for aura in auras]
        expected = [
            {'op': 'context_eq', 'field': 'player_class', 'value': klass},
            {'any': mercs} if len(mercs) > 1 else mercs[0],
        ]
        expected += [
            {'op': 'fact_eq', 'field': field, 'value': value}
            for field, value in (
                ('identified', True),
                ('base_code', base),
                ('runeword', 'Bulwark'),
                ('sockets', 3),
                ('socket_contents', 'filled'),
            )
        ]
        eth = {'op': 'fact_eq', 'field': 'ethereal', 'value': True}
        expected.append(eth if ethereal else {'any': [eth, {**eth, 'value': False}]})
        assert row['required_predicates'] == expected
        conditions = ' '.join(row['required_conditions'])
        if key.startswith('fist-of-the-heavens'):
            assert 'Might is the linked planner choice' in conditions
            assert 'Helmet stats do not transfer to the player' in conditions
        else:
            assert 'Non-Ladder Bulwark definition' in conditions
        if key == 'double-throw-barbarian-guide-0':
            assert 'preserve the armor conflict' in conditions
        if key == 'enchant-sorceress-0':
            assert 'elemental damage' in conditions
            assert 'not physical leech' in conditions
