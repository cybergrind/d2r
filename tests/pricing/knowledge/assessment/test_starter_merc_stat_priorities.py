from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


CASES = [
    ('rockstopper', 'Rockstopper', 'Sallet', 'unique', 0, ['39:0', '41:0', '43:0', '36:0', '99:0']),
    ('undead-crown', 'Undead Crown', 'Crown', 'unique', 0, ['60:0', '45:0']),
    ('duriel', "Duriel's Shell", 'Cuirass', 'unique', 0, ['153:0', '39:0', '41:0', '43:0', '45:0', '216:0', '0:0']),
    ('bulwark', 'Bulwark', 'Crown', 'normal', 3, ['60:0', '36:0', '76:0', '99:0']),
    ('smoke', 'Smoke', 'Leather Armor', 'normal', 2, ['39:0', '41:0', '43:0', '45:0', '99:0']),
    ('treachery', 'Treachery', 'Mage Plate', 'normal', 3, ['93:0', '99:0', '43:0', '201:17103']),
]


@pytest.mark.parametrize(('suffix', 'name', 'base', 'quality', 'sockets', 'keys'), CASES)
def test_starter_mercenary_priorities_are_native_conditional_and_observed(suffix, name, base, quality, sockets, keys):
    bundle = build()
    rid = 'fissure-starter-merc-' + suffix
    role = next(p for p in bundle['profiles'] if p['id'] == rid)
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    stats = {k: {'status': 'decoded', 'value': 5} for k in keys}
    if suffix == 'rockstopper':
        stats['3:0'] = {'status': 'decoded', 'value': 15}
    stats['16:0'] = {'status': 'decoded', 'value': 200}
    # Venom is a different trigger; never substitute it for Fade.
    stats['198:17807'] = {'status': 'decoded', 'value': 25}
    item = replace(facts(base, quality, name), stats=stats)
    if sockets:
        item = replace(item, runeword=name, sockets=sockets, socket_contents='filled')
    context = {'player_class': 'Druid'}
    if suffix in ('treachery', 'undead-crown', 'bulwark'):
        context['mercenary_type'] = 'Act 2 Prayer'

    def evaluate(candidate=item, ctx=context):
        return StatsEvaluator().evaluate(
            candidate, configs, ctx, role_outcomes=assess_role_results(candidate, [role], ctx)
        )

    if suffix == 'treachery':
        for merc in (None, 'Act 3 Fire'):
            assert '93:0' not in evaluate(ctx={'player_class': 'Druid', 'mercenary_type': merc}).annotations
        for merc in ('Act 1 Cold', 'Act 2 Might', 'Act 2 Holy Freeze', 'Act 2 Thorns'):
            assert '93:0' in evaluate(ctx={'player_class': 'Druid', 'mercenary_type': merc}).annotations

    if suffix in ('undead-crown', 'bulwark'):
        for merc in (None, 'Act 3 Fire', 'Act 3 Cold', 'Act 3 Lightning'):
            result = evaluate(ctx={'player_class': 'Druid', 'mercenary_type': merc})
            assert '60:0' not in result.annotations
            assert set(result.annotations) == set(keys) - {'60:0'}
        for merc in ('Act 1 Cold', 'Act 1 Fire', 'Act 2 Might', 'Act 2 Holy Freeze', 'Act 2 Thorns'):
            assert '60:0' in evaluate(ctx={'player_class': 'Druid', 'mercenary_type': merc}).annotations

    result = evaluate()
    assert set(result.annotations) == set(keys)
    assert result.configurations[0]['role']['status'] == 'partial'
    for key in keys:
        assert set(evaluate(replace(item, stats={k: v for k, v in stats.items() if k != key})).annotations) == set(
            keys
        ) - {key}
    for eth in (False, True, None):
        assert set(evaluate(replace(item, ethereal=eth)).annotations) == set(keys)
    for changes in ({'name': 'Other'}, {'item_type': 'weap'}, {'identified': False}, {'rarity': 'magic'}):
        assert not evaluate(replace(item, **changes)).annotations
    for ctx in ({}, {'player_class': 'Barbarian'}):
        assert not evaluate(ctx=ctx).annotations
    if sockets:
        assert set(evaluate(replace(item, rarity='superior')).annotations) == set(keys)
        for changes in ({'runeword': None}, {'sockets': 0}, {'socket_contents': 'empty'}, {'socket_contents': None}):
            assert not evaluate(replace(item, **changes)).annotations
    assert all(r['roll_quality'] == 'unassessed' for r in result.annotations.values())
    demand = bundle['guide_demand']['summaries'][name]
    assert 'fissure-druid' in demand['alternative_builds']
    assert demand['grade'] == 'Pending'
