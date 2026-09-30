"""Chains of Honor source links retain wearer and alternative-base semantics."""

import json
from pathlib import Path

from pricing.knowledge.assessment.maintenance.table_equivalence import compile_table_equivalence


ROOT = Path(__file__).resolve().parents[5]
GROUPS = {
    ('Amazon', 'uui', 'player', ()): ('lightning-fury-amazon-guide-3',),
    ('Amazon', 'utp', 'player', ()): ('lightning-strike-amazon-2',),
    ('Sorceress', 'uui', 'player', ()): ('meteor-sorceress-1',),
    ('Sorceress', 'utp', 'player', ()): ('lightning-sorceress-3',),
    ('Sorceress', 'uea', 'player', ()): ('nova-sorceress-guide-3',),
    ('Paladin', 'utp', 'player', ()): ('blessed-hammer-paladin-3', 'smite-paladin-1', 'smite-paladin-2'),
    ('Druid', 'utp', 'player', ()): ('fissure-druid-3',),
    ('Sorceress', 'utp', 'merc', ('Act 2 Might', 'Act 2 Holy Freeze')): (
        'nova-sorceress-guide-1',
        'nova-sorceress-guide-2',
        'nova-sorceress-guide-3',
    ),
    ('Sorceress', 'utp', 'merc', ('Act 2 Prayer',)): ('enchant-sorceress-1', 'enchant-sorceress-2'),
    ('Warlock', 'utp', 'merc', ('Act 2 Prayer',)): ('echoing-strike-warlock-guide-1', 'echoing-strike-warlock-guide-2'),
    ('Warlock', 'utp', 'merc', ('Act 2 Might',)): ('mirrored-blades-warlock-guide-1',),
    ('Paladin', 'uar', 'merc', ('Act 5 Frenzy',)): ('fist-of-the-heavens-paladin-3',),
    ('Amazon', 'utp', 'merc', ('Act 2 Might',)): ('strafe-amazon-1', 'strafe-amazon-2'),
    ('Druid', 'utp', 'merc', ('Act 2 Might',)): ('fissure-druid-3',),
}
EXPECTED = {f'{prefix}-{pair[2]}-chains-honor': pair for pair, prefixes in GROUPS.items() for prefix in prefixes}
HAMMER = 'blessed-hammer-paladin-2-merc-chains-honor'


def fact(field, value):
    return {'op': 'fact_eq', 'field': field, 'value': value}


def test_coh_sources_preserve_class_base_ethereal_breakpoints_and_alternatives():
    def read(path):
        return json.loads((ROOT / path).read_text())

    rows = [
        r
        for r in read('pricing/knowledge/assessment/rules/table_equivalence_reviews.json')['rows']
        if r['profile_id'] in {*EXPECTED, HAMMER}
    ]
    assert len(rows) == len(EXPECTED) + 1 == 22
    result = compile_table_equivalence(
        {'schema_version': 1, 'rows': rows},
        read('pricing/data/appraisal-guide-inventory.json')['occurrences'],
        read('pricing/data/appraisal-build-profiles.json')['profiles'],
        read('pricing/knowledge/assessment/rules/guide_use_reviews.json')['uses'],
        ROOT,
    )
    assert {r['profile_id'] for r in result} == {*EXPECTED, HAMMER}
    assert all(r['state'] == 'reviewed' for r in result)
    for row in rows:
        pid = row['profile_id']
        if pid == HAMMER:
            # Planner Archon Plate is ethereal; prose Sacred Armor permits either known status.
            assert row['required_predicates'][-1] == {
                'any': [
                    {'all': [fact('base_code', 'utp'), fact('ethereal', True)]},
                    {'all': [fact('base_code', 'uar'), {'any': [fact('ethereal', True), fact('ethereal', False)]}]},
                ]
            }
            assert {'op': 'context_eq', 'field': 'mercenary_type', 'value': 'Act 2 Holy Freeze'} in row[
                'required_predicates'
            ]
            assert any('only when the mercenary gets the kill' in c for c in row['required_conditions'])
            continue
        klass, base, side, mercenaries = EXPECTED[pid]
        predicates = [
            {'op': 'context_eq', 'field': 'player_class', 'value': klass},
            fact('identified', True),
            fact('base_code', base),
            fact('runeword', 'Chains of Honor'),
            fact('sockets', 4),
            fact('socket_contents', 'filled'),
            fact('ethereal', side == 'merc'),
        ]
        if mercenaries:
            predicates.append(
                {'any': [{'op': 'context_eq', 'field': 'mercenary_type', 'value': m} for m in mercenaries]}
            )
        if pid == 'meteor-sorceress-1-player-chains-honor':
            predicates += [
                {'op': 'context_at_least', 'field': field, 'value': value}
                for field, value in (('player_total_fcr', 63), ('player_total_fhr', 60))
            ]
        if pid == 'lightning-sorceress-3-player-chains-honor':
            predicates.append({'op': 'context_at_least', 'field': 'player_total_fcr', 'value': 105})
        assert row['required_predicates'] == predicates
        if pid.startswith('strafe-'):
            assert any('Shaftstop are survival alternatives' in c for c in row['required_conditions'])
