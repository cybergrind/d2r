from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('hammer-starter-spirit-sword', 'Crystal Sword'),
    ('hammer-starter-spirit-shield', 'Targe'),
    ('foh-starter-spirit-shield', 'Targe'),
    ('holy-bolt-starter-spirit-shield', 'Targe'),
    ('hammer-standard-spirit-shield', 'Sacred Targe'),
    ('hammer-mf-spirit-shield', 'Sacred Targe'),
]


@pytest.mark.parametrize(('role_id', 'base'), CASES)
def test_paladin_spirit_base_rolls_and_whole_loadout_dependencies(role_id, base):
    bundle = build()
    role = next((p for p in bundle['profiles'] if p['id'] == role_id), None)
    assert role is not None
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == role_id
    ]
    assert len(configs) == 1
    keys = {'127:0': 2, '105:0': 25, '99:0': 55, '9:0': 89, '3:0': 22}
    if base != 'Crystal Sword':
        keys.update({'39:0': 5, '41:0': 40, '43:0': 40, '45:0': 40})
    item = replace(
        facts(base, name='Spirit'),
        runeword='Spirit',
        sockets=4,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in keys.items()},
    )
    companions = ['Sling', "Hellwarden's Will"] if 'standard' in role_id else ['Void', 'Sling', 'Arachnid Mesh']
    context = {'player_class': 'Paladin', 'player_total_fcr': 125, 'player_items': companions}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    assert set(evaluate().annotations) == set(keys)
    # Low inherent resistances are useful; source planner rolls are not minima.
    for key in keys:
        assert set(evaluate(replace(item, stats={k: v for k, v in item.stats.items() if k != key})).annotations) == set(
            keys
        ) - {key}
    for eth in (False, True, None):
        assert set(evaluate(replace(item, ethereal=eth)).annotations) == set(keys)
    for changes in (
        {'base_code': facts('Monarch').base_code},
        {'rarity': 'magic'},
        {'runeword': None},
        {'sockets': 3},
        {'socket_contents': 'empty'},
        {'socket_contents': None},
        {'name': 'Other'},
    ):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(ctx={**context, 'player_class': 'Sorceress'}).annotations
    if base == 'Sacred Targe':
        assert not evaluate(ctx={**context, 'player_total_fcr': 124}).annotations
        assert not evaluate(ctx={'player_class': 'Paladin', 'player_items': companions}).annotations
        for companion in companions:
            assert not evaluate(ctx={**context, 'player_items': [c for c in companions if c != companion]}).annotations
        assert not evaluate(
            ctx={'player_class': 'Paladin', 'player_total_fcr': 125, 'mercenary_items': companions}
        ).annotations
    else:
        assert set(evaluate(ctx={'player_class': 'Paladin'}).annotations) == set(keys)


def test_paladin_starter_variants_add_two_builds_not_four_votes():
    d = build()['guide_demand']['summaries']['Spirit']
    assert d['distinct_builds'] >= 6
    assert d['distinct_builds'] == len(set(d['builds']))

    assert d['grade'] == 'Pending'
    assert d['lower_bound_grade'] == 'High'
    assert d['builds'].count('fist-of-the-heavens-paladin') == 1
    assert d['builds'].count('blessed-hammer-paladin') == 1
