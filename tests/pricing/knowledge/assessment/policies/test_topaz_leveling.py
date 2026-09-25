from dataclasses import replace

import pytest

from inventory_tracking.items.metadata import metadata
from pricing.knowledge.assessment.policies.leveling import assess_leveling
from tests.pricing.knowledge.assessment.test_family_contracts import facts


def topaz_armor(base='Cap', quality='normal'):
    gem = next(b for b in metadata()['bases'].values() if b['name'] == 'Chipped Topaz')
    return replace(
        facts(base, quality),
        sockets=2,
        socket_contents='filled',
        filled_sockets=1,
        empty_sockets=1,
        socket_items=[{'base_code': gem['code'], 'name': gem['name'], 'unit_id': 1, 'position': 0}],
        stats={'80:0': {'status': 'decoded', 'value': 9}},
    )


@pytest.mark.parametrize('base', ['Cap', 'Quilted Armor'])
@pytest.mark.parametrize('quality', ['normal', 'superior', 'magic', 'rare', 'crafted'])
def test_topaz_socket_leveling_uses_observed_payload_and_preserves_conditions(base, quality):
    uses = assess_leveling(topaz_armor(base, quality))
    assert len(uses) == 1
    assert uses[0]['source']['locator'] == '/generic_patterns/1'
    assert uses[0]['status'] == 'conditional'
    assert uses[0]['requirements_fit']['status'] == 'unknown'
    assert 'Stealth' in uses[0]['conditions'][0]


@pytest.mark.parametrize(
    'change',
    [
        {'socket_items': []},
        {'socket_contents': 'empty'},
        {'sockets': 0},
        {'stats': {}},
        {'gaps': ['Duplicate native stat 80:0.']},
        {'ethereal': True},
        {'runeword': 'Stealth'},
        {'item_type': 'swor'},
        {'identified': False},
    ],
)
def test_unverified_or_inapplicable_topaz_setup_does_not_claim_leveling_use(change):
    assert not assess_leveling(replace(topaz_armor(), **change))


def test_gem_display_name_cannot_substitute_for_topaz_identity():
    ruby = next(b for b in metadata()['bases'].values() if b['name'] == 'Ruby')
    item = replace(topaz_armor(), socket_items=[{'base_code': ruby['code'], 'name': 'Chipped Topaz'}])
    assert not assess_leveling(item)


def test_topaz_bonus_requires_complete_unique_links_and_sufficient_observed_total():
    item = topaz_armor()
    child = item.socket_items[0]
    for changed in (
        replace(item, filled_sockets=None, empty_sockets=None),
        replace(item, socket_items=[{k: v for k, v in child.items() if k != 'unit_id'}]),
        replace(item, socket_items=[{**child, 'position': 1}]),
        replace(item, filled_sockets=2, empty_sockets=0, socket_items=[child, {**child, 'position': 1}]),
        replace(item, stats={'80:0': {'status': 'decoded', 'value': 8}}),
    ):
        assert not assess_leveling(changed)
    two = replace(item, filled_sockets=2, empty_sockets=0, socket_items=[child, {**child, 'unit_id': 2, 'position': 1}])
    assert not assess_leveling(two)  # two chipped topazes require at least 18 MF
    assert assess_leveling(replace(two, stats={'80:0': {'status': 'decoded', 'value': 18}}))
