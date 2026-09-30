from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize('helmet', [False, True])
def test_specialist_priorities_require_the_complete_setup(helmet):
    bundle = build()
    rid = 'echoing-ubers-hellwarden' if helmet else 'smite-shared-treachery'
    role = next(p for p in bundle['profiles'] if p['id'] == rid)
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    assert len(configs) == 1
    values = (
        {'358:0': 5, '127:0': 1, '93:0': 20, '105:0': 20}
        if helmet
        else {'93:0': 45, '99:0': 20, '43:0': 30, '201:17103': 5}
    )
    wanted = set(values)
    if helmet:
        wanted.remove('93:0')  # Echoing Strike casts use FCR, not IAS.
    values.update({'16:0': 200, '198:17807': 25})
    item = replace(
        facts('Death Mask', 'unique', "Hellwarden's Will") if helmet else facts('Mage Plate', name='Treachery'),
        sockets=1 if helmet else 3,
        socket_contents='filled',
        runeword=None if helmet else 'Treachery',
        socket_items=[{'name': "Guardian's Light"}] if helmet else [],
        stats={k: {'status': 'decoded', 'value': v} for k, v in values.items()},
    )
    ctx = (
        {'player_class': 'Warlock', 'player_items': ['Sling', 'Renewed Black Cleft']}
        if helmet
        else {'player_class': 'Paladin', 'mercenary_type': 'Act 2 Might'}
    )

    def evaluate(candidate=item, context=ctx):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert set(evaluate().annotations) == wanted
    assert evaluate().configurations[0]['role']['status'] == 'partial'
    for change in ({'ethereal': True}, {'ethereal': None}, {'identified': False}, {'name': 'Other'}):
        assert not evaluate(replace(item, **change)).annotations
    assert not evaluate(context={}).annotations
    for key in wanted:
        observed = {k: v for k, v in item.stats.items() if k != key}
        assert set(evaluate(replace(item, stats=observed)).annotations) == (set() if helmet else wanted - {key})
    if helmet:
        without_ias = replace(item, stats={k: v for k, v in item.stats.items() if k != '93:0'})
        assert set(evaluate(without_ias).annotations) == wanted
        assert not evaluate(replace(item, socket_items=[])).annotations
        for names in (['Sling'], ['Renewed Black Cleft']):
            assert not evaluate(context={**ctx, 'player_items': names}).annotations
    else:
        assert not evaluate(context={**ctx, 'mercenary_type': 'Act 2 Prayer'}).annotations
        for change in ({'runeword': None}, {'socket_contents': 'empty'}, {'sockets': 2}):
            assert not evaluate(replace(item, **change)).annotations
    assert all(a['roll_quality'] == 'unassessed' for a in evaluate().annotations.values())
