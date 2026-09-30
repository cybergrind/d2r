from dataclasses import replace

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def test_zeal_lawbringer_requires_frenzy_legal_sword_and_filled_recipe():
    bundle = build()
    roles = [r for r in bundle['profiles'] if r['id'] == 'zeal-paladin-lawbringer-act-5-frenzy']
    assert len(roles) == 1
    configs = [
        configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == roles[0]['id']
    ]
    stats = {
        '151:119': {'status': 'decoded', 'value': 16},
        '198:5583': {'status': 'decoded', 'value': 20, 'unit': 'percent_chance'},
    }
    item = replace(
        facts('Phase Blade'),
        name='Lawbringer',
        runeword='Lawbringer',
        sockets=3,
        socket_contents='filled',
        filled_sockets=3,
        stats=stats,
    )
    context = {'player_class': 'Paladin', 'mercenary_type': 'Act 5 Frenzy'}

    def evaluate(candidate, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, roles, ctx)
        )

    for quality in ('normal', 'superior', 'low_quality'):
        assert set(evaluate(replace(item, rarity=quality)).annotations) == set(stats)
    for base in ('Legend Sword', 'War Scepter'):
        assert not evaluate(replace(item, base_code=facts(base).base_code)).annotations
    ethereal = replace(item, base_code=facts('Cryptic Sword').base_code, ethereal=True)
    assert set(evaluate(ethereal).annotations) == set(stats)
    for patch in ({'socket_contents': 'empty'}, {'sockets': 2}, {'runeword': None}, {'rarity': 'magic'}):
        assert not evaluate(replace(item, **patch)).annotations
    for ctx in (
        {'player_class': 'Paladin'},
        {**context, 'mercenary_type': 'Act 2 Might'},
        {**context, 'player_class': 'Sorceress'},
    ):
        assert not evaluate(item, ctx).annotations
    wrong = replace(item, stats={**stats, '198:5583': {'status': 'decoded', 'value': 20, 'unit': 'skill_level'}})
    assert '198:5583' not in evaluate(wrong).annotations
