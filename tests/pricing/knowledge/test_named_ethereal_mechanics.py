import pytest

from pricing.knowledge.market import normalize_listing
from tests.pricing.knowledge.test_market import listing


def named(name, ethereal=None):
    raw = listing()
    raw['properties'] = [p for p in raw['properties'] if p['property_id'] not in (738, 797, 402, 934)]
    if ethereal is not None:
        raw['properties'].append({'property_id': 738, 'type': 'bool', 'bool': ethereal})
    return normalize_listing(raw, name=name, category='uniques', source='fixture')


@pytest.mark.parametrize('name', ['Ethereal Edge', 'Ghostflame', 'Shadow Killer', 'Wraith Flight'])
def test_forced_ethereal_unique_is_known_without_optional_listing_flag(name):
    row = named(name)
    assert row['ethereal'] is True
    assert '738' not in row['properties']
    assert row['facet_basis']['ethereal']['kind'] == 'unique_ethereal_mechanics'
    assert not named(name, True).get('mechanics_conflicts')
    assert named(name, False)['mechanics_conflicts']


@pytest.mark.parametrize('name', ['Stormshield', 'Crown of Ages', 'Wizardspike', "Butcher's Pupil"])
def test_inherent_indestructibility_without_forced_ethereal_excludes_random_ethereal(name):
    row = named(name)
    assert row['ethereal'] is False
    assert named(name, True)['mechanics_conflicts']
    assert not named(name, False).get('mechanics_conflicts')


def test_repairing_or_ordinary_unique_is_not_assumed_nonethereal():
    for name in ['Shaftstop', "Skullder's Ire", 'Unverified Unique']:
        assert named(name).get('ethereal') is None


def test_conflicting_or_incomplete_definition_variants_do_not_force_a_state():
    from pricing.knowledge.named_ethereal import intrinsic_ethereal

    forced = {'game_definition': {'prop1': 'ethereal', 'min1': 1, 'max1': 1}}
    indestructible = {'game_definition': {'prop1': 'indestruct', 'min1': 1, 'max1': 1}}
    assert intrinsic_ethereal([forced, indestructible]) is None
    assert intrinsic_ethereal([forced, {}]) is None
    assert intrinsic_ethereal([]) is None
    assert intrinsic_ethereal([{'game_definition': {'prop1': 'ethereal', 'min1': 0, 'max1': 1}}]) is None
