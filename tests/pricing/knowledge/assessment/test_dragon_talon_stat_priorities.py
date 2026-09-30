from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_fissure_pelts import facet
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('suffix', 'name', 'base', 'quality', 'wanted'),
    [
        ('guillaume', "Guillaume's Face", 'Winged Helm', 'set', {'136:0', '93:0', '41:0', '99:0', '0:0'}),
        ('goblin-toe', 'Goblin Toe', 'Mirrored Boots', 'unique', {'136:0'}),
        ('hexfire-merc', 'Hexfire', 'Shamshir', 'unique', {'126:1', '329:0'}),
        ('ormus-merc', "Ormus' Robes", 'Dusk Shroud', 'unique', {'329:0'}),
        ('lidless-merc', 'Lidless Wall', 'Grim Shield', 'unique', {'127:0', '329:0'}),
    ],
)
def test_dragon_talon_player_and_enchant_support_have_distinct_priorities(suffix, name, base, quality, wanted):
    bundle = build()
    rid = 'dragon-talon-budget-' + suffix
    role = next(p for p in bundle['profiles'] if p['id'] == rid)
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = {
        '136:0': 35 if suffix == 'guillaume' else 25,
        '93:0': 15,
        '41:0': 30,
        '99:0': 30,
        '0:0': 15,
        '126:1': 3,
        '127:0': 1,
        '329:0': 13 if suffix == 'ormus-merc' else 3,
    }
    stats = {k: {'status': 'decoded', 'value': values[k]} for k in wanted}
    # These unrelated modifiers must not acquire build-desirability from this use.
    stats.update(
        {k: {'status': 'decoded', 'value': 20} for k in ('16:0', '17:0', '18:0', '333:0', '141:0', '105:0', '77:0')}
    )
    item = replace(facts(base, quality, name), stats=stats)
    merc = suffix.endswith('-merc')
    jewel = (
        facet()
        if merc
        else {
            'item_type': 'jewl',
            'stats_complete': True,
            'stats': {'93:0': {'status': 'decoded', 'value': 15}, '41:0': {'status': 'decoded', 'value': 30}},
        }
    )
    jewel = {**jewel, 'unit_id': 1000, 'position': 0}
    if suffix != 'goblin-toe':
        item = replace(item, sockets=1, socket_contents='filled', socket_items=[jewel])
    ctx = {'player_class': 'Assassin', **({'mercenary_type': 'Act 3 Fire'} if merc else {})}

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    result = evaluate()
    assert set(result.annotations) == wanted
    assert result.configurations[0]['role']['status'] == 'partial'
    for key in wanted:
        missing = replace(item, stats={k: v for k, v in stats.items() if k != key})
        expected = set() if suffix == 'goblin-toe' else wanted - {key}
        assert set(evaluate(missing).annotations) == expected
    for change in ({'name': 'Other'}, {'identified': False}, {'item_type': 'ring'}, {'rarity': 'magic'}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={}).annotations
    if merc:
        assert not evaluate(context={'mercenary_type': 'Act 3 Fire'}).annotations
        assert not evaluate(context={**ctx, 'player_class': 'Sorceress'}).annotations
        assert not evaluate(context={**ctx, 'mercenary_type': 'Act 3 Cold'}).annotations
        for eth in (False, True, None):
            assert set(evaluate(replace(item, ethereal=eth)).annotations) == wanted
        assert not evaluate(
            replace(item, socket_items=[{**facet(element='cold'), 'unit_id': 1000, 'position': 0}])
        ).annotations
    if suffix != 'goblin-toe':
        for change in ({'socket_items': []}, {'socket_contents': 'empty'}):
            assert not evaluate(replace(item, **change)).annotations
        split = [{**jewel, 'stats': {k: v for k, v in jewel['stats'].items() if k == key}} for key in jewel['stats']]
        assert not evaluate(replace(item, sockets=2, socket_items=split)).annotations
    else:
        unupgraded = replace(item, base_name='Light Plated Boots', base_code=facts('Light Plated Boots').base_code)
        assert not evaluate(unupgraded).annotations
        assert not evaluate(replace(item, ethereal=True)).annotations
    assert all(a['roll_quality'] == 'unassessed' for a in result.annotations.values())
