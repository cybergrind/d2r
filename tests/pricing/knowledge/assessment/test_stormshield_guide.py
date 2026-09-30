from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'index', 'cls', 'rune'),
    [
        ('berserk-barbarian', 4, 'Barbarian', 'Shael Rune'),
        ('lightning-fury-amazon-guide', 3, 'Amazon', None),
        ('lightning-sorceress', 3, 'Sorceress', 'Shael Rune'),
        ('meteor-sorceress', 4, 'Sorceress', 'Um Rune'),
    ],
)
def test_stormshield_softcore_roles_keep_socket_requirements_and_defensive_stats(slug, index, cls, rune):
    bundle = build()
    rid = f'{slug}-{index}-stormshield'
    role = next((r for r in bundle['profiles'] if r['id'] == rid), None)
    assert role is not None
    children = []
    if rune:
        base = next(b for b in metadata()['bases'].values() if b['name'] == rune)
        children = [{'name': rune, 'base_code': base['code'], 'item_type': base['type'], 'unit_id': 10, 'position': 0}]
    item = replace(
        facts('Monarch', 'unique', 'Stormshield'),
        sockets=1 if rune else 0,
        socket_contents='filled' if rune else 'empty',
        socket_items=children,
        stats={
            k: {'status': 'decoded', 'value': v}
            for k, v in [('36:0', 35), ('102:0', 35), ('20:0', 25), ('41:0', 25), ('43:0', 60), ('0:0', 30)]
        },
    )
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    context = {'player_class': cls}

    def evaluate(candidate):
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, [role], context)
        )

    assert evaluate(item).annotations['36:0']['desirability'] == 'desirable'
    assert len(evaluate(item).annotations) == 6
    for changes in [{'rarity': 'rare'}, {'identified': None}, {'base_code': facts('Kite Shield').base_code}]:
        assert not evaluate(replace(item, **changes)).annotations
    if rune:
        assert not evaluate(replace(item, sockets=0, socket_contents='empty', socket_items=[])).annotations
    else:
        assert 'alternative' in role['source']['review']
