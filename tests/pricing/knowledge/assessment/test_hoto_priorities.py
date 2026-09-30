from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('double-throw-barbarian-guide', 1, 'Barbarian', False),
    ('fire-blast-assassin', 1, 'Assassin', False),
    ('fissure-druid', 1, 'Druid', False),
    ('fissure-druid', 2, 'Druid', False),
    ('fist-of-the-heavens-paladin', 2, 'Paladin', False),
    ('gold-find-barbarian', 1, 'Barbarian', True),
    ('gold-find-barbarian', 2, 'Barbarian', True),
    ('gold-find-barbarian', 3, 'Barbarian', False),
    ('lightning-sentry-assassin', 2, 'Assassin', False),
    ('lightning-sorceress', 1, 'Sorceress', False),
    ('summoner-necromancer-guide', 1, 'Necromancer', True),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'ethereal'), MEMBERS)
def test_hoto_minimum_resistance_roll_keeps_caster_and_swap_utility(slug, index, cls, ethereal):
    bundle = build()
    rid = f'{slug}-{index}-heart-oak'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {'127:0': 3, '105:0': 40, '77:0': 15, '39:0': 30, '41:0': 30, '43:0': 30, '45:0': 30}
    item = replace(
        facts('Flail', name='Heart of the Oak'),
        runeword='Heart of the Oak',
        sockets=4,
        socket_contents='filled',
        ethereal=ethereal,
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    context = {'player_class': cls}

    def evaluate(candidate=item):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == set(values)
    assert evaluate().annotations['127:0']['desirability'] == 'desirable'
    assert evaluate(replace(item, rarity='superior')).annotations
    assert evaluate(replace(item, rarity='low_quality')).annotations
    for change in [
        {'runeword': None},
        {'rarity': 'magic'},
        {'sockets': 3},
        {'socket_contents': 'empty'},
        {'identified': None},
        {'base_code': facts('Crystal Sword').base_code},
    ]:
        assert not evaluate(replace(item, **change)).annotations
    if slug == 'double-throw-barbarian-guide' or (slug == 'gold-find-barbarian' and index == 1):
        assert any('two' in c and '+6' in c for c in role['conditions'])
    if cls == 'Assassin':
        assert any('trap' in c and 'attack speed' in c for c in role['conditions'])
    if ethereal:
        assert not evaluate(replace(item, ethereal=False)).annotations


def test_hoto_demand_excludes_ambiguous_nova_table_alternative():
    b = build()
    assert b['guide_demand']['summaries']['Heart of the Oak']['distinct_builds'] >= 8
    assert b['guide_demand']['summaries']['Heart of the Oak']['distinct_builds'] == len(
        set(b['guide_demand']['summaries']['Heart of the Oak']['builds'])
    )

    assert 'nova-sorceress-guide-3-heart-oak' not in {r['id'] for r in b['profiles']}
