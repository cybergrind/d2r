from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_role_results
from pricing.knowledge.assessment.stat_bundle import configuration_from_row
from pricing.knowledge.assessment.stat_evaluation import StatsEvaluator
from tests.pricing.knowledge.assessment.roles.test_gem_payload import gemmed
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(('base', 'count'), [('Mask', 3), ('Gothic Plate', 4)])
def test_topaz_armor_find_requires_verified_payload_in_armor_not_shield_or_weapon(base, count):
    bundle = build()
    rid = 'fist-of-the-heavens-paladin-' + base.lower().replace(' ', '-') + '-topaz-find'
    roles = [r for r in bundle['profiles'] if r['id'] == rid]
    assert len(roles) == 1
    configs = [configuration_from_row(c) for c in bundle['stat_evaluation']['configurations'] if c['role_id'] == rid]
    item = replace(gemmed(base, count), stats={'80:0': {'status': 'decoded', 'value': count * 24}})

    def evaluate(candidate, klass='Paladin'):
        context = {'player_class': klass}
        return StatsEvaluator().evaluate(
            candidate, configs, context, role_outcomes=assess_role_results(candidate, roles, context)
        )

    assert set(evaluate(item).annotations) == {'80:0'}
    assert set(evaluate(replace(item, rarity='superior')).annotations) == {'80:0'}
    assert not evaluate(item, 'Sorceress').annotations
    unrelated = replace(item, base_code=facts('Mage Plate').base_code, runeword='Authority')
    assert not assess_role_results(unrelated, roles, {'player_class': 'Paladin'})
    assert not evaluate(replace(item, name='Fortitude', runeword='Fortitude')).annotations
    for patch in (
        {'base_code': facts('Monarch').base_code},
        {'ethereal': True},
        {'rarity': 'rare'},
        {'socket_items': item.socket_items[:-1]},
        {'socket_contents': 'empty'},
        {'stats': {'80:0': {'status': 'decoded', 'value': count * 24 - 1}}},
    ):
        assert not evaluate(replace(item, **patch)).annotations
