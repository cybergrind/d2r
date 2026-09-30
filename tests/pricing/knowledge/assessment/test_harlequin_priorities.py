from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('abyss-warlock-build-guide', 2, 'Warlock', 125),
    ('blessed-hammer-paladin', 2, 'Paladin', 125),
    ('blizzard-sorceress', 2, 'Sorceress', 105),
    ('double-throw-barbarian-guide', 2, 'Barbarian', None),
    ('echoing-strike-warlock-guide', 2, 'Warlock', 125),
    ('enchant-sorceress', 2, 'Sorceress', None),
    ('fire-warlock-guide', 2, 'Warlock', None),
    ('meteor-sorceress', 2, 'Sorceress', 105),
    ('lightning-sentry-assassin', 2, 'Assassin', 102),
    ('berserk-barbarian', 1, 'Barbarian', None),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'fcr'), MEMBERS)
def test_harlequin_mf_family_retains_variant_conditions(slug, index, cls, fcr):
    bundle = build()
    rid = f'{slug}-{index}-harlequin'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Shako', 'unique', 'Harlequin Crest'),
        stats={'127:0': {'status': 'decoded', 'value': 2}, '80:0': {'status': 'decoded', 'value': 50}},
    )
    ctx = {'player_class': cls, **({'player_total_fcr': fcr} if fcr else {})}
    if slug == 'meteor-sorceress':
        ctx['player_total_fhr'] = 60

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == {'127:0', '80:0'}
    assert evaluate().annotations['80:0']['desirability'] == 'desirable'
    for change in ({'rarity': 'rare'}, {'ethereal': True}, {'identified': None}, {'name': 'Other'}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    if fcr:
        for value in (None, fcr - 1, str(fcr), True):
            assert not evaluate(context={**ctx, 'player_total_fcr': value}).annotations
    if slug == 'meteor-sorceress':
        assert not evaluate(context={**ctx, 'player_total_fhr': 59}).annotations
    if cls == 'Barbarian':
        assert any('Weapon-Swap' in c for c in role['conditions'])
        # Swap-only breakpoint must not be applied to main-hand casting.
        assert evaluate(context={**ctx, 'player_total_fcr': 0}).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
    assert any('socket' in c.lower() for c in role['conditions'])
    assert set(evaluate(replace(item, stats={})).annotations) == set()


def test_harlequin_demand_is_reviewed_breadth_not_price():
    summary = build()['guide_demand']['summaries'].get('Harlequin Crest')
    assert summary is not None
    assert summary['distinct_builds'] >= 10
    assert summary['distinct_builds'] == len(set(summary['builds']))

    assert summary['grade'] == 'Pending'
    assert summary['lower_bound_grade'] == 'High'
