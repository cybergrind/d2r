from dataclasses import replace

import pytest

from pricing.knowledge.assessment.build_profiles import build
from pricing.knowledge.assessment.profiles import assess_roles
from tests.pricing.knowledge.assessment.test_family_contracts import facts


@pytest.mark.parametrize(
    ('slug', 'name', 'base', 'quality', 'sockets', 'slot'),
    [
        ('rockstopper', 'Rockstopper', 'Sallet', 'unique', 0, 'Helmet'),
        ('undead-crown', 'Undead Crown', 'Crown', 'unique', 0, 'Helmet'),
        ('duriel', "Duriel's Shell", 'Cuirass', 'unique', 0, 'Body Armor'),
        ('bulwark', 'Bulwark', 'Crown', 'normal', 3, 'Helmet'),
        ('smoke', 'Smoke', 'Mage Plate', 'normal', 2, 'Body Armor'),
        ('treachery', 'Treachery', 'Mage Plate', 'normal', 3, 'Body Armor'),
    ],
)
def test_starter_merc_alternatives_preserve_stage_and_completed_recipe(slug, name, base, quality, sockets, slot):
    rule = next((p for p in build()['profiles'] if p['id'] == f'fissure-starter-merc-{slug}'), None)
    assert rule is not None
    item = facts(base, quality, name)
    if sockets:
        item = replace(item, runeword=name, sockets=sockets, socket_contents='filled')
    context = {'player_class': 'Druid'}
    role = assess_roles(item, [rule], context)[0]
    assert role['side'] == 'merc'
    assert rule['variant'] == 'Starter'
    assert rule['slot'] == slot
    assert role['rule_trace']['truth'] == 'true'
    assert role['status'] == 'partial'
    assert any('early' in c.lower() for c in role['missing'])
    assert 'price' not in role
    assert assess_roles(replace(item, ethereal=True), [rule], context)[0]['rule_trace']['truth'] == 'true'
    assert assess_roles(item, [rule], {'player_class': 'Sorceress'})[0]['status'] == 'failed'
    assert not assess_roles(replace(item, name='Unrelated item'), [rule], context)
    if sockets:
        unknown = assess_roles(replace(item, runeword=None), [rule], context)[0]
        assert unknown['rule_trace']['truth'] == 'unknown'
        for unmade in (replace(item, runeword='Other recipe'), replace(item, socket_contents='empty')):
            assert assess_roles(unmade, [rule], context)[0]['status'] == 'failed'
    else:
        assert not assess_roles(replace(item, rarity='rare'), [rule], context)
