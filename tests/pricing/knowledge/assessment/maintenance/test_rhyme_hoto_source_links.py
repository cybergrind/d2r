"""Casting and shield source links preserve active-set limitations."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
RHYME = {
    'berserk-barbarian-0': ('Barbarian', 'Off-Hand'),
    'lightning-sorceress-0': ('Sorceress', 'Off-Hand-Swap'),
    'lightning-fury-amazon-guide-0': ('Amazon', 'Off-Hand'),
    'fire-blast-assassin-0': ('Assassin', 'Off-Hand'),
    'lightning-strike-amazon-0': ('Amazon', 'Off-Hand'),
    'lightning-sentry-assassin-0': ('Assassin', 'Off-Hand'),
    'meteor-sorceress-0': ('Sorceress', 'Off-Hand-Swap'),
    'blizzard-sorceress-0': ('Sorceress', 'Off-Hand Swap'),
}
HOTO = {
    'lightning-sentry-assassin-2': ('Assassin', 'Weapon'),
    'fissure-druid-2': ('Druid', 'Weapon'),
    'fire-blast-assassin-1': ('Assassin', 'Weapon'),
    'double-throw-barbarian-guide-1': ('Barbarian', 'Weapon-Swap'),
    'fist-of-the-heavens-paladin-2': ('Paladin', 'Weapon'),
    'lightning-sorceress-1': ('Sorceress', 'Weapon'),
    'fissure-druid-1': ('Druid', 'Weapon'),
}
EXPECTED = {
    **{k + '-rhyme': (*v, 'Rhyme', 'bsh', 2) for k, v in RHYME.items()},
    **{k + '-heart-oak': (*v, 'Heart of the Oak', 'fla', 4) for k, v in HOTO.items()},
}


def test_rhyme_hoto_sources_preserve_completed_item_and_active_set_scope():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 15
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    by_id = {r['id']: r for r in profiles}
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        profiles,
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == set(EXPECTED)
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        klass, slot, word, base, sockets = EXPECTED[row['profile_id']]
        assert by_id[row['profile_id']]['slot'] == slot
        expected = [{'op': 'context_eq', 'field': 'player_class', 'value': klass}]
        expected += [
            {'op': 'fact_eq', 'field': field, 'value': value}
            for field, value in (
                ('identified', True),
                ('base_code', base),
                ('runeword', word),
                ('sockets', sockets),
                ('socket_contents', 'filled'),
            )
        ]
        if word == 'Rhyme':
            expected.append({'op': 'fact_eq', 'field': 'ethereal', 'value': False})
        assert row['required_predicates'] == expected
        qualifications = ' '.join(row['required_conditions'])
        if word == 'Rhyme' and klass == 'Sorceress':
            assert 'only with this swap set active' in qualifications
        if word == 'Heart of the Oak' and klass == 'Barbarian':
            assert 'two actual Heart of the Oak weapons' in qualifications
            assert 'one captured weapon establishes only its own +3' in qualifications
        if word == 'Heart of the Oak' and klass == 'Assassin':
            assert 'Fire Blast throwing use attack speed instead' in qualifications
