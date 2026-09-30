from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('enchant-sorceress', 1, 'Sorceress', True, None, None),
    ('fire-blast-assassin', 1, 'Assassin', True, 102, None),
    ('fire-warlock-guide', 1, 'Warlock', True, None, None),
    ('fissure-druid', 1, 'Druid', True, 99, None),
    ('fissure-druid', 2, 'Druid', True, None, None),
    ('fissure-druid', 3, 'Druid', True, None, None),
    ('fist-of-the-heavens-paladin', 2, 'Paladin', False, 125, None),
    ('fist-of-the-heavens-paladin', 3, 'Paladin', False, 75, 48),
    ('lightning-sentry-assassin', 1, 'Assassin', False, 65, None),
    ('meteor-sorceress', 1, 'Sorceress', True, 63, 60),
    ('meteor-sorceress', 3, 'Sorceress', True, 105, 86),
    ('meteor-sorceress', 4, 'Sorceress', True, 105, 86),
    ('nova-sorceress-guide', 1, 'Sorceress', False, 105, None),
    ('nova-sorceress-guide', 2, 'Sorceress', False, None, None),
    ('nova-sorceress-guide', 3, 'Sorceress', True, None, None),
    ('wake-of-fire-assassin', 1, 'Assassin', True, 102, None),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'fire', 'fcr', 'fhr'), MEMBERS)
def test_magefist_priorities_follow_spells_and_legal_upgrade_scope(slug, index, cls, fire, fcr, fhr):
    bundle = build()
    rid = f'{slug}-{index}-magefist'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {'105:0': 20, '27:0': 25, '126:1': 1}
    elite_only = slug == 'fissure-druid' and index == 3
    item = replace(
        facts('Crusader Gauntlets' if elite_only else 'Light Gauntlets', 'unique', 'Magefist'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {
        'player_class': cls,
        **({'player_total_fcr': fcr} if fcr else {}),
        **({'player_total_fhr': fhr} if fhr else {}),
    }

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == {'105:0', '27:0'} | ({'126:1'} if fire else set())
    assert evaluate().annotations['105:0']['desirability'] == 'desirable'
    assert evaluate().annotations['27:0']['desirability'] == 'supporting'
    for base in ('Light Gauntlets', 'Battle Gauntlets', 'Crusader Gauntlets'):
        candidate = replace(facts(base, 'unique', 'Magefist'), stats=item.stats)
        assert bool(evaluate(candidate).annotations) == (not elite_only or base == 'Crusader Gauntlets')
    wrong_base = replace(facts('Heavy Gloves', 'unique', 'Magefist'), stats=item.stats)
    assert not evaluate(wrong_base).annotations
    for change in ({'rarity': 'set'}, {'ethereal': True}, {'identified': None}, {'name': 'Other'}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    for field, target in [('player_total_fcr', fcr), ('player_total_fhr', fhr)]:
        if target:
            for value in (None, target - 1, str(target), True):
                assert not evaluate(context={**ctx, field: value}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'


def test_magefist_demand_counts_distinct_builds_and_excludes_prebuff():
    bundle = build()
    summary = bundle['guide_demand']['summaries'].get('Magefist')
    assert summary is not None
    assert {member[0] for member in MEMBERS} <= set(summary['builds'])
    assert summary['distinct_builds'] == len(set(summary['builds']))
    assert summary['grade'] == 'Pending'
    assert summary['lower_bound_grade'] == 'High'
    assert not any(p['id'] == 'enchant-sorceress-3-magefist' for p in bundle['profiles'])
