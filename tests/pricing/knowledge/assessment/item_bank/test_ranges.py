"""A factory must preserve the evidence gates used by real captures."""

from dataclasses import replace

import pytest
from dirty_equals import IsPartialDict

from tests.pricing.knowledge.assessment.item_bank.cases.named import SHAKO


@pytest.mark.parametrize(
    'changes',
    [
        {'ethereal': None},
        {'ethereal': True},
        {'owned_stats': None},
        {'owned_stats': ((31, 0, 98),)},
        {'identified': False},
    ],
)
def test_unproven_defense_is_not_ranked(changes):
    capture = replace(SHAKO, **changes).capture()
    defense = next(row for row in capture['decoded_stats'] if row.get('memory_stat', {}).get('id') == 31)
    assert 'roll_range' not in defense
    assert 'roll_quality' not in defense


@pytest.mark.parametrize(('value', 'quality'), [(141, 'perfect'), (98, 'low')])
def test_proven_defense_uses_native_range_and_rank(value, quality):
    item = replace(
        SHAKO,
        raw_stats=tuple((stat, layer, value if stat == 31 else raw) for stat, layer, raw in SHAKO.raw_stats),
        owned_stats=((31, 0, value),),
    )
    defense = next(row for row in item.capture()['decoded_stats'] if row.get('memory_stat', {}).get('id') == 31)
    assert defense == IsPartialDict(
        roll_range=IsPartialDict(min=98, max=141, scope='unmodified non-ethereal base defense'),
        roll_quality=quality,
    )


@pytest.mark.parametrize('table_id', [None, 326])
def test_ambiguous_or_foreign_named_identity_is_not_guessed(table_id):
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    with pytest.raises(ValueError, match='unambiguous native identity'):
        Item('Phase Blade', 'unique', 'Azurewrath', named_table_id=table_id).capture()


def test_explicit_active_azurewrath_preserves_its_aura_range():
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    item = Item('Phase Blade', 'unique', 'Azurewrath', ((151, 119, 13),), named_table_id=301)
    aura = item.capture()['decoded_stats'][0]
    assert aura == IsPartialDict(
        roll_range=IsPartialDict(min=10, max=13),
        roll_quality='perfect',
    )


def test_complete_ordinary_bane_capture_selects_its_damage_range():
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    item = Item('Short Staff', 'unique', 'Bane Ash', ((17, 0, 55), (18, 0, 55), (93, 0, 20)), complete=True)
    damage = next(row for row in item.capture()['decoded_stats'] if row.get('name') == 'item_damage_percent')
    assert damage == IsPartialDict(roll_range=IsPartialDict(min=50, max=60))


@pytest.mark.parametrize(
    'changes',
    [
        {'complete': False},
        {'sockets': 1},
        {'sockets': None},
        {'socket_contents': 'unknown'},
    ],
)
def test_bane_factory_does_not_prove_version_without_clean_unsocketed_capture(changes):
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    item = Item('Short Staff', 'unique', 'Bane Ash', ((17, 0, 55), (18, 0, 55), (93, 0, 20)), complete=True)
    damage = next(
        row for row in replace(item, **changes).capture()['decoded_stats'] if row.get('name') == 'item_damage_percent'
    )
    assert 'roll_range' not in damage


@pytest.mark.parametrize(
    ('rarity', 'value', 'bounds', 'rank'),
    [
        ('magic', 3, (1, 3), 'perfect'),
        ('rare', 1, (1, 3), 'low'),
        ('low_quality', 1, (1, 1), None),
    ],
)
def test_constructed_staffmods_follow_production_ranges(rarity, value, bounds, rank):
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    row = Item('Dream Spirit', rarity, raw_stats=((107, 234, value),)).capture()['decoded_stats'][0]
    assert row['text'] == f'+{value} ({bounds[0]}-{bounds[1]}) to Fissure (Druid Only)'
    assert row.get('roll_quality') == rank
    assert 'roll_tier' not in row


def test_constructed_runeword_staffmod_total_is_not_ranked():
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    row = Item('Dream Spirit', 'normal', raw_stats=((107, 234, 3),), runeword='Metamorphosis').capture()[
        'decoded_stats'
    ][0]
    assert 'staffmod range: 1-3; total contributions unverified' in row['text']
    assert 'roll_quality' not in row


def test_constructed_unidentified_staffmod_has_no_range_claim():
    from tests.pricing.knowledge.assessment.item_bank.models import Item

    row = Item('Dream Spirit', 'magic', raw_stats=((107, 234, 3),), identified=False).capture()['decoded_stats'][0]
    assert 'staffmod_range' not in row
    assert 'roll_range' not in row
