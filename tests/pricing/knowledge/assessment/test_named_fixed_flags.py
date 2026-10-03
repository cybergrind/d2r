from dataclasses import replace

import pytest

from pricing.knowledge.assessment.adapters.capture import normalize
from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.item_bank.models import Item


ITEM = Item(
    'Sacred Armor',
    'unique',
    "Tyrael's Might",
    (
        (31, 0, 1322),
        (16, 0, 120),
        (91, 0, -100),
        (152, 0, 1),
        (108, 0, 1),
        (121, 0, 50),
        (153, 0, 1),
        (96, 0, 20),
        (39, 0, 20),
        (41, 0, 20),
        (43, 0, 20),
        (45, 0, 20),
        (0, 0, 20),
    ),
    complete=True,
)


def test_fixed_rip_does_not_require_invented_market_mapping():
    contract, gaps = NamedHandler().contract(normalize(ITEM.capture()), 'armor')
    assert contract is not None, gaps


@pytest.mark.parametrize('value', [None, 0, 2])
def test_missing_or_conflicting_rip_cannot_be_assumed_from_name(value):
    stats = tuple((s, p, value if s == 108 else v) for s, p, v in ITEM.raw_stats if s != 108 or value is not None)
    contract, gaps = NamedHandler().contract(normalize(replace(ITEM, raw_stats=stats).capture()), 'armor')
    assert contract is None
    assert any('108:0' in gap for gap in gaps), gaps


@pytest.mark.parametrize(
    'change',
    [
        {'raw': True},
        {'value': True},
        {'status': 'unresolved'},
        {'market_property': 'unverified'},
        {'raw': 2},
        {'value': 0},
    ],
)
def test_rip_requires_verified_raw_decoding(change):
    from types import SimpleNamespace

    from pricing.knowledge.assessment.mechanics.named_flags import fixed_flag_keys

    row = {'raw': 1, 'value': 1, 'status': 'decoded', 'market_property': None, **change}
    keys, gaps = fixed_flag_keys(
        SimpleNamespace(stats={'108:0': row}), {'game_definition': {'prop1': 'rip', 'min1': 1, 'max1': 1}}
    )
    assert not keys
    assert gaps


def test_rip_is_not_consumed_for_an_unrelated_named_definition():
    from types import SimpleNamespace

    from pricing.knowledge.assessment.mechanics.named_flags import fixed_flag_keys

    assert fixed_flag_keys(
        SimpleNamespace(stats={'108:0': {'raw': 1, 'value': 1, 'status': 'decoded'}}),
        {'game_definition': {'prop1': 'nofreeze', 'min1': 1, 'max1': 1}},
    ) == (set(), [])


@pytest.mark.parametrize('depleted', [False, True])
def test_natures_peace_fixed_rip_and_rechargeable_oak_sage(depleted):
    from tests.pricing.knowledge.assessment.item_bank.cases.natures_peace_alternatives import ring

    contract, gaps = NamedHandler().contract(normalize(ring(depleted=depleted).capture()), 'jewelry')
    assert contract is not None, gaps


def test_indestructible_tyrael_cannot_be_naturally_ethereal():
    contract, gaps = NamedHandler().contract(normalize(replace(ITEM, ethereal=True).capture()), 'armor')
    assert contract is None
    assert any('ethereal' in gap.lower() for gap in gaps), gaps


@pytest.mark.parametrize('name', ['Ethereal Edge', 'Ghostflame', 'Shadow Killer', 'Wraith Flight'])
@pytest.mark.parametrize(('ethereal', 'valid'), [(True, True), (False, False), (None, False)])
def test_native_ethereal_exceptions_preserve_required_variant(name, ethereal, valid):
    from types import SimpleNamespace

    from pricing.knowledge.assessment.mechanics.named_flags import native_ethereal_gap
    from pricing.knowledge.definition_store import catalog

    gap = native_ethereal_gap(SimpleNamespace(ethereal=ethereal), catalog().named['unique', name])
    assert (gap is None) is valid


@pytest.mark.parametrize(
    'name',
    [
        "Butcher's Pupil",
        'The Gavel of Pain',
        'Stormshield',
        "Schaefer's Hammer",
        'The Cranium Basher',
        'Doombringer',
        'The Grandfather',
        'Wizardspike',
        'Stormspire',
        "Tyrael's Might",
        'Leviathan',
        'Steel Pillar',
        'Crown of Ages',
    ],
)
@pytest.mark.parametrize(('ethereal', 'valid'), [(True, False), (False, True), (None, False)])
def test_native_indestructible_excludes_random_ethereal(name, ethereal, valid):
    from types import SimpleNamespace

    from pricing.knowledge.assessment.mechanics.named_flags import native_ethereal_gap
    from pricing.knowledge.definition_store import catalog

    gap = native_ethereal_gap(SimpleNamespace(ethereal=ethereal), catalog().named['unique', name])
    assert (gap is None) is valid


def test_socket_granted_indestructibility_does_not_forbid_ethereal():
    from types import SimpleNamespace

    from pricing.knowledge.assessment.mechanics.named_flags import native_ethereal_gap
    from pricing.knowledge.definition_store import catalog

    facts = SimpleNamespace(ethereal=True, stats={'152:0': {'raw': 1, 'value': 1}})
    assert native_ethereal_gap(facts, catalog().named['unique', "The Reaper's Toll"]) is None


@pytest.mark.parametrize('name', ['Azurewrath', 'Lightsabre', 'Windforce', "Nature's Peace"])
@pytest.mark.parametrize(('ethereal', 'valid'), [(False, True), (True, False), (None, False)])
def test_unique_nondurable_original_base_cannot_roll_ethereal(name, ethereal, valid):
    from types import SimpleNamespace

    from pricing.knowledge.assessment.mechanics.named_flags import native_ethereal_gap
    from pricing.knowledge.definition_store import catalog

    assert (native_ethereal_gap(SimpleNamespace(ethereal=ethereal), catalog().named['unique', name]) is None) is valid


def test_upgraded_ethereal_ginthers_rift_uses_original_durability():
    from types import SimpleNamespace

    from pricing.knowledge.assessment.mechanics.named_flags import native_ethereal_gap
    from pricing.knowledge.definition_store import catalog

    definition = catalog().named['unique', "Ginther's Rift"]
    phase = catalog().named['unique', 'Lightsabre']['base_code']
    assert native_ethereal_gap(SimpleNamespace(ethereal=True, base_code=phase), definition) is None


def test_throwing_weapon_is_not_excluded_as_nondurable():
    from types import SimpleNamespace

    from pricing.knowledge.assessment.mechanics.named_flags import native_ethereal_gap
    from pricing.knowledge.definition_store import catalog

    assert native_ethereal_gap(SimpleNamespace(ethereal=True), catalog().named['unique', "Titan's Revenge"]) is None
