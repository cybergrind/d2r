from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('blizzard-sorceress', 1, 'Sorceress', 105),
    ('echoing-strike-warlock-guide', 1, 'Warlock', 125),
    ('echoing-strike-warlock-guide', 2, 'Warlock', 125),
    ('echoing-strike-warlock-guide', 3, 'Warlock', None),
    ('summoner-necromancer-guide', 1, 'Necromancer', 125),
    ('summoner-necromancer-guide', 2, 'Necromancer', 75),
    ('poison-nova-necromancer', 0, 'Necromancer', 75),
    ('poison-nova-necromancer', 1, 'Necromancer', 125),
    ('poison-nova-necromancer', 2, 'Necromancer', 125),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'fcr'), MEMBERS)
def test_trang_glove_stats_follow_beneficiary_not_item_name_alone(slug, index, cls, fcr):
    bundle = build()
    rid = f'{slug}-{index}-trang-claws'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {'105:0': 20, '43:0': 30, '188:16': 2, '332:0': 25}
    item = replace(
        facts('Heavy Bracers', 'set', "Trang-Oul's Claws"),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': cls, **({'player_total_fcr': fcr} if fcr else {})}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    expected = {'105:0', '43:0'}
    if cls == 'Necromancer':
        expected.add('188:16')
    if slug == 'poison-nova-necromancer':
        expected.add('332:0')
    assert set(evaluate().annotations) == expected
    assert evaluate().annotations['105:0']['desirability'] == 'desirable'
    assert evaluate().annotations['43:0']['desirability'] == 'supporting'
    if '332:0' in expected:
        assert evaluate().annotations['332:0']['desirability'] == 'desirable'
    for change in ({'rarity': 'unique'}, {'ethereal': True}, {'identified': None}, {'name': 'Other'}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    if fcr:
        for value in (None, fcr - 1, str(fcr), True):
            assert not evaluate(context={**ctx, 'player_total_fcr': value}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'


def test_trang_demand_deduplicates_variants_and_does_not_claim_full_set():
    summary = build()['guide_demand']['summaries'].get("Trang-Oul's Claws")
    assert summary is not None
    assert summary['distinct_builds'] >= 4
    assert summary['distinct_builds'] == len(set(summary['builds']))

    assert summary['grade'] == 'Pending'
    assert summary['lower_bound_grade'] == 'High'
