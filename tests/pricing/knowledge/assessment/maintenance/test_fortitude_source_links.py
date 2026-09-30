"""Exact Fortitude sources retain wearer, base and completed-word requirements."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
# class, base, side, and allowed mercenaries, independently reviewed by variant.
GROUPS = {
    ('Amazon', 'utp', 'player', ()): ('strafe-amazon-1', 'strafe-amazon-2'),
    ('Barbarian', 'utp', 'player', ()): ('double-throw-barbarian-guide-1',),
    ('Assassin', 'uar', 'merc', ('Act 2 Holy Freeze',)): ('lightning-sentry-assassin-2',),
    ('Assassin', 'uar', 'merc', ('Act 2 Might',)): ('wake-of-fire-assassin-1', 'fire-blast-assassin-1'),
    ('Warlock', 'uar', 'merc', ('Act 2 Might',)): ('abyss-warlock-build-guide-1', 'abyss-warlock-build-guide-2'),
    ('Warlock', 'utp', 'merc', ('Act 2 Might',)): ('fire-warlock-guide-1', 'fire-warlock-guide-2'),
    ('Paladin', 'uar', 'merc', ('Act 2 Might',)): ('fist-of-the-heavens-paladin-2',),
    ('Paladin', 'uar', 'merc', ('Act 2 Holy Freeze',)): ('blessed-hammer-paladin-1', 'blessed-hammer-paladin-3'),
    ('Sorceress', 'uar', 'merc', ('Act 2 Might',)): (
        'meteor-sorceress-3',
        'lightning-sorceress-1',
        'lightning-sorceress-2',
    ),
    ('Druid', 'uar', 'merc', ('Act 2 Might', 'Act 2 Holy Freeze')): ('fissure-druid-1', 'fissure-druid-2'),
    ('Necromancer', 'uar', 'merc', ('Act 2 Might',)): ('poison-nova-necromancer-1', 'poison-nova-necromancer-2'),
    ('Amazon', 'uar', 'merc', ('Act 2 Might',)): ('lightning-fury-amazon-guide-1', 'lightning-fury-amazon-guide-2'),
}
EXPECTED = {f'{prefix}-{pair[2]}-fortitude': pair for pair, prefixes in GROUPS.items() for prefix in prefixes}


def test_fortitude_source_reviews_keep_exact_player_and_mercenary_configurations():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 22
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    occurrences = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        occurrences,
        profiles,
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == set(EXPECTED)
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        klass, base, side, mercenaries = EXPECTED[row['profile_id']]
        expected = [
            {'op': 'context_eq', 'field': 'player_class', 'value': klass},
            *[
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in (
                    ('identified', True),
                    ('base_code', base),
                    ('runeword', 'Fortitude'),
                    ('sockets', 4),
                    ('socket_contents', 'filled'),
                    ('ethereal', side == 'merc'),
                )
            ],
        ]
        merc = [{'op': 'context_eq', 'field': 'mercenary_type', 'value': name} for name in mercenaries]
        expected += [{'any': merc}] if len(merc) > 1 else merc
        assert row['required_predicates'] == expected
