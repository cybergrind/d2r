from dataclasses import replace

import pytest

from pricing.knowledge.assessment.handlers.named import NamedHandler
from tests.pricing.knowledge.assessment.test_family_contracts import facts, scalar_properties


def shaftstop(ed):
    return replace(
        facts('Mesh Armor', 'unique', 'Shaftstop'),
        stats={
            f'{stat}:0': {'status': 'decoded', 'value': value}
            for stat, value in [(16, ed), (31, 650), (32, 250), (36, 30), (7, 60)]
        },
        properties={'425': ed},
    )


@pytest.mark.parametrize('ed', [180, 200, 220])
def test_named_armor_accepts_possible_enhanced_defense(ed):
    contract, gaps = NamedHandler().contract(shaftstop(ed), 'armor')
    assert contract is not None, gaps


@pytest.mark.parametrize('ed', [179, 221, 200.5, True, float('nan'), float('inf')])
def test_named_armor_rejects_impossible_enhanced_defense(ed):
    contract, gaps = NamedHandler().contract(shaftstop(ed), 'armor')
    assert contract is None
    assert any('16:0' in gap and 'range' in gap for gap in gaps)


def test_total_defense_is_not_mistaken_for_flat_defense_roll():
    # Kira adds 50-120 defense; the Tiara's base defense is part of stat31.
    item = replace(
        facts('Tiara', 'unique', "Kira's Guardian"),
        stats={
            f'{stat}:0': {'status': 'decoded', 'value': value}
            for stat, value in [(31, 170), (39, 70), (41, 70), (43, 70), (45, 70), (153, 1), (99, 20)]
        },
    )
    item = replace(item, properties=scalar_properties(item.stats))
    contract, gaps = NamedHandler().contract(item, 'helm')
    assert contract is not None, gaps
    assert contract.properties['1855'] == 170


@pytest.mark.parametrize(('ed', 'accepted'), [(275, True), (325, True), (274, False), (326, False)])
def test_set_enhanced_defense_uses_its_own_definition(ed, accepted):
    item = replace(
        facts('Quilted Armor', 'set', 'Arctic Furs'),
        stats={
            f'{stat}:0': {'status': 'decoded', 'value': value}
            for stat, value in [(16, ed), (31, 49), (39, 10), (41, 10), (43, 10), (45, 10)]
        },
    )
    item = replace(item, properties=scalar_properties(item.stats))
    contract, gaps = NamedHandler().contract(item, 'armor')
    assert (contract is not None) is accepted, gaps
    if not accepted:
        assert any('16:0' in gap and '275-325' in gap for gap in gaps)


@pytest.mark.parametrize(('gold', 'accepted'), [(80, True), (100, True), (79, False), (101, False)])
def test_crown_gold_find_roll_is_bounded_independently(gold, accepted):
    item = replace(
        facts('Grand Crown', 'unique', 'Crown of Thieves'),
        stats={
            f'{stat}:0': {'status': 'decoded', 'value': value}
            for stat, value in [(31, 300), (2, 25), (60, 12), (7, 50), (9, 35), (39, 33), (16, 200), (79, gold)]
        },
    )
    item = replace(item, properties=scalar_properties(item.stats))
    contract, gaps = NamedHandler().contract(item, 'helm')
    assert (contract is not None) is accepted, gaps
    if not accepted:
        assert any('79:0' in gap and '80-100' in gap for gap in gaps)
