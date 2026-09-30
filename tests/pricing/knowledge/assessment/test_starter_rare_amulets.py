from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'cls', 'skill', 'fcr'),
    [
        ('blessed-hammer-paladin', 'Paladin', '188:24', None),
        ('summoner-necromancer-guide', 'Necromancer', '188:18', 75),
    ],
)
def test_rare_starter_amulet_core_does_not_require_illustrated_secondary_rolls(slug, cls, skill, fcr):
    bundle = build()
    rid = slug + '-starter-rare-amulet'
    role = next((p for p in bundle['profiles'] if p['id'] == rid), None)
    assert role is not None
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(
        facts('Amulet', 'rare'), stats={k: {'status': 'decoded', 'value': v} for k, v in [(skill, 1), ('105:0', 10)]}
    )
    ctx = {'player_class': cls, **({'player_total_fcr': fcr} if fcr else {})}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == {skill, '105:0'}
    supported = replace(item, stats={**item.stats, '9:0': {'status': 'decoded', 'value': 1}})
    assert evaluate(supported).annotations['9:0']['desirability'] == 'supporting'
    for key in (skill, '105:0'):
        missing = replace(item, stats={k: v for k, v in item.stats.items() if k != key})
        assert not evaluate(missing, {**ctx, 'player_equipment': {'ring_left': item}}).annotations
    for change in ({'rarity': 'magic'}, {'rarity': 'crafted'}, {'identified': None}, {'ethereal': True}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={'player_class': 'Other'}).annotations
    if fcr:
        resistances = {key: {'status': 'decoded', 'value': 10} for key in ('39:0', '41:0', '43:0', '45:0')}
        complete = replace(item, stats={**item.stats, **resistances})
        assert set(evaluate(complete).annotations) == {skill, '105:0', *resistances}
        incomplete = replace(complete, stats={k: v for k, v in complete.stats.items() if k != '39:0'})
        assert set(evaluate(incomplete).annotations) == {skill, '105:0'}
        for value in (None, 74, '75', True):
            assert not evaluate(context={**ctx, 'player_total_fcr': value}).annotations
        assert any('+4' in c for c in role['conditions'])
    else:
        assert any('charges' in c for c in role['conditions'])
    assert assess_role_results(item, [role], ctx)[0].status == 'partial'
