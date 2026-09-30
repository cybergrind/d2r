"""Enigma source coverage distinguishes completed armor from an empty base."""

import copy
import json
from pathlib import Path

import pytest

from pricing.knowledge.assessment.maintenance.guide_inventory import fingerprint
from pricing.knowledge.assessment.maintenance.structured_named_variants import validate_link
from pricing.knowledge.assessment.maintenance.table_equivalence import _read, compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
# Independently reviewed source variants. The tuple gives wearer and exact base.
GROUPS = {
    ('Amazon', 'xtp'): ('lightning-strike-amazon-1',),
    ('Amazon', 'uui'): ('lightning-fury-amazon-guide-1', 'lightning-fury-amazon-guide-2'),
    ('Warlock', 'xtp'): (
        'abyss-warlock-build-guide-1',
        'abyss-warlock-build-guide-2',
        'echoing-strike-warlock-guide-1',
        'echoing-strike-warlock-guide-2',
        'echoing-strike-warlock-guide-3',
        'fire-warlock-guide-1',
        'fire-warlock-guide-2',
        'mirrored-blades-warlock-guide-1',
        'mirrored-blades-warlock-guide-2',
    ),
    ('Necromancer', 'xtp'): ('poison-nova-necromancer-1', 'poison-nova-necromancer-2'),
    ('Necromancer', 'utp'): ('summoner-necromancer-guide-1', 'summoner-necromancer-guide-2'),
    ('Assassin', 'xtp'): (
        'fire-blast-assassin-1',
        'lightning-sentry-assassin-1',
        'lightning-sentry-assassin-2',
        'dragon-talon-assassin-1',
        'wake-of-fire-assassin-1',
    ),
    ('Paladin', 'xtp'): (
        'blessed-hammer-paladin-1',
        'blessed-hammer-paladin-2',
        'dream-paladin-0',
        'fist-of-the-heavens-paladin-2',
        'fist-of-the-heavens-paladin-3',
    ),
    ('Barbarian', 'xtp'): (
        'berserk-barbarian-1',
        'gold-find-barbarian-1',
        'gold-find-barbarian-2',
        'gold-find-barbarian-3',
    ),
    ('Barbarian', 'utp'): ('double-throw-barbarian-guide-2',),
    ('Druid', 'utp'): ('fissure-druid-1', 'fissure-druid-2'),
    ('Sorceress', 'xtp'): ('lightning-sorceress-1',),
}
EXPECTED = {f'{prefix}-player-enigma': pair for pair, prefixes in GROUPS.items() for prefix in prefixes}


def read(path):
    return json.loads((ROOT / path).read_text())


def test_enigma_sources_require_exact_completed_nonethereal_armor():
    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in EXPECTED
    ]
    assert len(rows) == len(EXPECTED) == 34
    profiles = read('pricing/data/appraisal-build-profiles.json')['profiles']
    occurrences = read('pricing/data/appraisal-guide-inventory.json')['occurrences']
    uses = read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses']
    result = compile_table_equivalence({'schema_version': 1, 'rows': rows}, occurrences, profiles, uses, ROOT)
    assert {r['profile_id'] for r in result} == set(EXPECTED)
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        klass, base = EXPECTED[row['profile_id']]
        assert row['required_predicates'] == [
            {'op': 'context_eq', 'field': 'player_class', 'value': klass},
            *[
                {'op': 'fact_eq', 'field': field, 'value': value}
                for field, value in (
                    ('identified', True),
                    ('base_code', base),
                    ('runeword', 'Enigma'),
                    ('sockets', 3),
                    ('socket_contents', 'filled'),
                    ('ethereal', False),
                )
            ],
        ]


@pytest.mark.parametrize('field', ['base_code', 'runeword', 'sockets', 'socket_contents', 'ethereal'])
def test_enigma_source_cannot_survive_a_weakened_configuration(field):
    rows = read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
    row = copy.deepcopy(next(r for r in rows if r['profile_id'] == 'fissure-druid-1-player-enigma'))
    role = next(
        r for r in read('pricing/data/appraisal-build-profiles.json')['profiles'] if r['id'] == row['profile_id']
    )
    occurrence = next(
        r for r in read('pricing/data/appraisal-guide-inventory.json')['occurrences'] if r['id'] == row['occurrence_id']
    )
    role['must']['all'] = [p for p in role['must']['all'] if p.get('field') != field]
    row['profile_fingerprint'] = fingerprint(role)
    with pytest.raises(ValueError, match='mandatory reviewed predicates'):
        validate_link(row, occurrence, role, [], ROOT, lambda pin: json.loads(_read(ROOT, pin)))
