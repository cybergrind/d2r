from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('blizzard-mf', False),
    ('blizzard-set', True),
    ('meteor-standard', True),
    ('meteor-mf', False),
    ('meteor-set', True),
    ('lightning-standard', True),
    ('lightning-mf', True),
]


@pytest.mark.parametrize(
    ('prefix', 'needs_spirit', 'player_class'),
    [(p, s, 'Sorceress') for p, s in CASES]
    + [
        (p, True, 'Warlock')
        for p in (
            'echoing-standard',
            'echoing-mf',
            'echoing-ubers',
            'abyss-standard',
            'abyss-mf',
            'mirrored-standard',
            'mirrored-ubers',
            'fire-standard',
            'fire-mf',
        )
    ],
)
def test_cta_prebuff_needs_native_shouts_and_actual_swap_companion(prefix, needs_spirit, player_class):
    bundle = build()
    rid = prefix + '-cta-prebuff'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = {'97:149': 1, '97:155': 2, '127:0': 1, '97:146': 4, '17:0': 240, '18:0': 240, '93:0': 40}
    item = replace(
        facts('Crystal Sword', name='Call to Arms'),
        runeword='Call to Arms',
        sockets=5,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': player_class, 'player_swap_items': ['Call to Arms', 'Spirit']}
    wanted = {'97:149', '97:155', '127:0'}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == wanted
    for key in ('97:149', '97:155'):
        assert not evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key})).annotations
    for eth in (False, True, None):
        assert set(evaluate(replace(item, ethereal=eth)).annotations) == wanted
    for changes in (
        {'name': 'Other'},
        {'runeword': None},
        {'sockets': 4},
        {'socket_contents': 'empty'},
        {'rarity': 'magic'},
        {'base_code': facts('Phase Blade').base_code},
        {'identified': False},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(context={'player_class': 'Barbarian', 'player_swap_items': ['Spirit']}).annotations
    no_swap = {'player_class': player_class, 'player_items': ['Spirit'], 'mercenary_items': ['Spirit']}
    if needs_spirit:
        assert not evaluate(context=no_swap).annotations
        assert not evaluate(context={**ctx, 'player_swap_items': []}).annotations
        assert not evaluate(context={**ctx, 'player_swap_items': ['Spirit', None]}).annotations
    else:
        assert set(evaluate(context=no_swap).annotations) == wanted
    top = replace(item, stats={**item.stats, '97:149': {'status': 'decoded', 'value': 6}})
    assert set(evaluate(top).annotations) == wanted
    assert all(a['roll_quality'] == 'unassessed' for a in evaluate(top).annotations.values())
    d = bundle['guide_demand']['summaries']['Call to Arms']
    assert d['distinct_builds'] >= 7
    assert d['distinct_builds'] == len(set(d['builds']))

    assert d['builds'].count(role['build']) == 1
    assert d['grade'] == 'Pending'
