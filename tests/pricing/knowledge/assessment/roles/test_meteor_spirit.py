from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_blizzard_set_spirit import PIECES
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('suffix', 'fcr', 'fhr', 'companions'),
    [
        ('standard', 63, 60, ['The Oculus']),
        ('mf', 105, 60, ['The Oculus', *PIECES[2:]]),
        ('set', 105, 86, PIECES),
    ],
)
def test_meteor_spirit_variants_keep_breakpoints_alternatives_and_piece_dependencies(suffix, fcr, fhr, companions):
    bundle = build()
    rid = 'meteor-' + suffix + '-spirit-shield'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = {'127:0': 2, '105:0': 25, '99:0': 55, '9:0': 89, '3:0': 22, '41:0': 35, '43:0': 35, '45:0': 35}
    item = replace(
        facts('Monarch', name='Spirit'),
        runeword='Spirit',
        sockets=4,
        socket_contents='filled',
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': 'Sorceress', 'player_total_fcr': fcr, 'player_total_fhr': fhr, 'player_items': companions}

    def evaluate(context=ctx, candidate=item):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == set(values)
    for field, target in (('player_total_fcr', fcr), ('player_total_fhr', fhr)):
        for v in (None, True, str(target), target - 1):
            assert not evaluate({**ctx, field: v}).annotations
    for piece in companions:
        assert not evaluate({**ctx, 'player_items': [p for p in companions if p != piece]}).annotations
    assert not evaluate({**ctx, 'player_items': [], 'mercenary_items': companions}).annotations
    for changes in (
        {'name': 'Other'},
        {'sockets': 0},
        {'socket_contents': 'empty'},
        {'runeword': None},
        {'base_code': facts('Targe').base_code},
    ):
        assert not evaluate(candidate=replace(item, **changes)).annotations
    if suffix == 'standard':
        assert set(evaluate({**ctx, 'player_items': ["Eschuta's Temper"]}).annotations) == set(values)
        pref = next(p for p in role['preferences'] if p['when'].get('field') == 'player_total_fcr')
        assert pref['when']['value'] == 105
        from pricing.knowledge.assessment.roles.predicates import evaluate as predicate

        assert predicate(pref['when'], item, ctx).truth == 'false'
        assert predicate(pref['when'], item, {**ctx, 'player_total_fcr': 105}).truth == 'true'
        from inventory_tracking.appraisal.build_use_summary import build_use_summary
        from pricing.knowledge.assessment.profiles import assess_roles

        lines = build_use_summary(assess_roles(item, [role], ctx)).lines
        assert any('Targets: Optional higher 105%' in line for line in lines)
        assert not any('Better rolls:' in line for line in lines)
    else:
        assert not evaluate({**ctx, 'player_total_fcr': 63}).annotations
    demand = bundle['guide_demand']['summaries']['Spirit']
    assert demand['builds'].count('meteor-sorceress') == 1
    assert demand['distinct_builds'] >= 6
    assert demand['distinct_builds'] == len(set(demand['builds']))
