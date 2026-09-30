from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('abyss-warlock-build-guide', 1, 'Warlock', 125),
    ('blessed-hammer-paladin', 1, 'Paladin', 125),
    ('blizzard-sorceress', 1, 'Sorceress', 105),
    ('echoing-strike-warlock-guide', 1, 'Warlock', 125),
    ('echoing-strike-warlock-guide', 2, 'Warlock', 125),
    ('echoing-strike-warlock-guide', 3, 'Warlock', None),
    ('fissure-druid', 3, 'Druid', None),
    ('lightning-sentry-assassin', 1, 'Assassin', 65),
    ('lightning-sorceress', 1, 'Sorceress', 117),
    ('summoner-necromancer-guide', 1, 'Necromancer', 125),
    ('summoner-necromancer-guide', 2, 'Necromancer', 75),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'fcr'), MEMBERS)
def test_maras_skills_and_minimum_resistance_roll_support_reviewed_use(slug, index, cls, fcr):
    bundle = build()
    rid = f'{slug}-{index}-maras'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    config = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    stats = {
        k: {'status': 'decoded', 'value': 2 if k == '127:0' else 20} for k in ('127:0', '39:0', '41:0', '43:0', '45:0')
    }
    item = replace(facts('Amulet', 'unique', "Mara's Kaleidoscope"), stats=stats)
    ctx = {'player_class': cls, **({'player_total_fcr': fcr} if fcr else {})}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, config, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    result = evaluate()
    assert result.annotations['127:0']['desirability'] == 'desirable'
    assert all(k in result.annotations for k in stats)
    assert not evaluate(context={'player_class': 'Other'}).annotations
    for change in ({'identified': None}, {'ethereal': True}, {'rarity': 'rare'}, {'name': 'Other'}):
        assert not evaluate(replace(item, **change)).annotations
    if fcr:
        for value in (None, fcr - 1, str(fcr), True):
            assert not evaluate(context={**ctx, 'player_total_fcr': value}).annotations
    missing_res = evaluate(replace(item, stats={k: v for k, v in stats.items() if k != '39:0'}))
    assert set(missing_res.annotations) == {'127:0'}
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'


def test_maras_demand_counts_builds_not_variants():
    demand = build()['guide_demand']['summaries'].get("Mara's Kaleidoscope")
    assert demand is not None
    assert demand['distinct_builds'] >= 8
    assert demand['distinct_builds'] == len(set(demand['builds']))

    assert demand['grade'] == 'Pending'
    assert demand['lower_bound_grade'] == 'High'
