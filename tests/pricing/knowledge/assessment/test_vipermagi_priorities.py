from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


MEMBERS = [
    ('blizzard-sorceress', 1, 'Sorceress', 105, None, False),
    ('enchant-sorceress', 1, 'Sorceress', None, None, False),
    ('enchant-sorceress', 2, 'Sorceress', None, None, False),
    ('fist-of-the-heavens-paladin', 4, 'Paladin', None, None, True),
    ('meteor-sorceress', 4, 'Sorceress', 105, 86, False),
    ('nova-sorceress-guide', 1, 'Sorceress', 105, None, True),
    ('nova-sorceress-guide', 2, 'Sorceress', 105, None, True),
]


@pytest.mark.parametrize(('slug', 'index', 'cls', 'fcr', 'fhr', 'original_only'), MEMBERS)
def test_vipermagi_role_preserves_base_gear_and_breakpoint_requirements(slug, index, cls, fcr, fhr, original_only):
    bundle = build()
    rid = f'{slug}-{index}-vipermagi'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    values = {'105:0': 30, '127:0': 1, '39:0': 20, '41:0': 20, '43:0': 20, '45:0': 20}
    item = replace(
        facts('Serpentskin Armor', 'unique', 'Skin of the Vipermagi'),
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = {'player_class': cls}
    if fcr:
        ctx['player_total_fcr'] = fcr
    if fhr:
        ctx['player_total_fhr'] = fhr
    if slug == 'blizzard-sorceress':
        ctx['player_equipment'] = {'head': facts('Spired Helm', 'unique', "Nightwing's Veil")}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    result = evaluate()
    assert set(result.annotations) == set(values)
    assert result.annotations['105:0']['desirability'] == 'desirable'
    assert result.annotations['127:0']['desirability'] == 'desirable'
    assert result.annotations['45:0']['desirability'] == (
        'desirable' if slug == 'nova-sorceress-guide' else 'supporting'
    )
    assert result.annotations['39:0']['desirability'] == 'supporting'
    upgraded = replace(facts('Wyrmhide', 'unique', 'Skin of the Vipermagi'), stats=item.stats)
    assert bool(evaluate(upgraded).annotations) is not original_only
    wrong = replace(facts('Leather Armor', 'unique', 'Skin of the Vipermagi'), stats=item.stats)
    assert not evaluate(wrong).annotations
    for changes in ({'identified': None}, {'ethereal': True}, {'rarity': 'rare'}, {'name': 'Other'}):
        assert not evaluate(replace(item, **changes)).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    for field, target in [('player_total_fcr', fcr), ('player_total_fhr', fhr)]:
        if target:
            for value in (None, target - 1, str(target), True):
                assert not evaluate(context={**ctx, field: value}).annotations
    if slug == 'blizzard-sorceress':
        for equipment in (None, {}, {'head': None}, {'head': facts('Shako', 'unique', 'Harlequin Crest')}):
            assert not evaluate(context={**ctx, 'player_equipment': equipment}).annotations
    assert not evaluate(replace(item, stats={})).annotations
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'


def test_vipermagi_counts_distinct_supported_builds_and_excludes_out_of_scope_sources():
    bundle = build()
    demand = bundle['guide_demand']['summaries'].get('Skin of the Vipermagi')
    assert demand is not None
    assert demand['distinct_builds'] >= 5
    assert demand['distinct_builds'] == len(set(demand['builds']))

    assert demand['lower_bound_grade'] == 'High'
    assert demand['grade'] == 'Pending'
    assert 'blizzard-sorceress' in demand['alternative_builds']
    ids = {p['id'] for p in bundle['profiles']}
    assert 'blizzard-sorceress-4-vipermagi' not in ids
    assert 'poison-nova-necromancer-4-vipermagi' not in ids
