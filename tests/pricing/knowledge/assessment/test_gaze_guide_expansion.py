from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('smite-paladin', 1, 'Paladin'),
    ('smite-paladin', 2, 'Paladin'),
    ('strafe-amazon', 1, 'Amazon'),
    ('strafe-amazon', 2, 'Amazon'),
]


@pytest.mark.parametrize(('slug', 'index', 'cls'), MEMBERS)
def test_gaze_native_survival_excludes_mana_leech_and_socket_ias(slug, index, cls):
    bundle = build()
    rid = f'{slug}-{index}-merc-gaze-native'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Grim Helm', 'unique', 'Vampire Gaze'),
        ethereal=True,
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('60:0', 6), ('36:0', 15), ('35:0', 10), ('62:0', 8), ('93:0', 15)]
        },
    )
    context = {'player_class': cls, 'mercenary_type': 'Act 2 Might'}

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    assert set(evaluate().annotations) == {'60:0', '36:0', '35:0'}
    assert evaluate().annotations['60:0']['desirability'] == 'desirable'
    assert evaluate().annotations['36:0']['desirability'] == 'desirable'
    assert evaluate().annotations['35:0']['desirability'] == 'supporting'
    assert bool(evaluate(replace(item, ethereal=False)).annotations) == (slug == 'strafe-amazon')
    for change in (
        {'ethereal': None},
        {'identified': None},
        {'rarity': 'set'},
        {'name': 'Other'},
        {'base_code': facts('Bone Visage').base_code},
    ):
        assert not evaluate(replace(item, **change)).annotations
    for merc in (None, 'Act 1 Cold', True):
        assert not evaluate(ctx={**context, 'mercenary_type': merc}).annotations
    assert not evaluate(ctx={**context, 'player_class': 'Other'}).annotations
    assert assess_role_results(item, [role], context)[0].status == 'partial'
    assert any('physical damage' in c for c in role['conditions'])
    if slug == 'smite-paladin':
        assert any('Smite' in c and 'Life Tap' in c for c in role['conditions'])
    else:
        assert any('alternative' in c and 'Pride' in c for c in role['conditions'])


def test_gaze_new_builds_deduplicate_variants_and_preserve_alternatives():
    demand = build()['guide_demand']['summaries']['Vampire Gaze']
    assert demand['distinct_builds'] == 8
    assert demand['grade'] == 'Pending'
    assert demand['lower_bound_grade'] == 'High'
    assert demand['alternative_builds'] == ['abyss-warlock-build-guide', 'strafe-amazon', 'zeal-paladin']
