"""Layer 2 of the loot design (inventory_tracking/loot/value.py): worth, tiers, the rolls that matter, copies."""

from dataclasses import replace

import pytest

from inventory_tracking.identify import service
from inventory_tracking.loot import value
from inventory_tracking.loot.facts import Owner
from inventory_tracking.loot.value import CollectionCopies, RollSpec, better_than, tier_of
from tests.inventory_tracking.loot.test_valuables import GOBLIN, facts_of


def test_value_ist_moved_to_the_loot_layers_and_the_old_import_still_works():
    assert service.value_ist is value.value_ist


@pytest.mark.parametrize(
    ('worth', 'verdict', 'tier'),
    [(1.0, 'slow', 'expensive'), (0.65, 'slow', 'cheap'), (0.2, 'sell', 'worthless'), (None, 'vendor', 'worthless'),
     (0.6, 'vendor', 'worthless'), (None, None, 'unknown'), (None, 'check', 'unknown')],
)  # fmt: skip
def test_the_tiers(worth, verdict, tier):
    assert tier_of(worth, verdict) == tier


def test_better_is_better_than_every_copy_and_a_tie_on_mixed_rolls_is_not():
    andy = {'base': 'Demonhead', 'code': 'usk', 'quality': 'unique', 'name': "Andariel's Visage"}
    specs = (RollSpec('0:0', 'Strength', 25, 30), RollSpec('60:0', 'Life stolen', 8, 10))
    new = facts_of({**andy, 'rolls': {'0:0': 30, '60:0': 8}})
    tie = facts_of({**andy, 'rolls': {'0:0': 25, '60:0': 10}}, 2, owner=Owner.PLAYER)
    worse = facts_of({**andy, 'rolls': {'0:0': 26, '60:0': 8}}, 3, owner=Owner.PLAYER)
    assert better_than(new, [worse], specs).better
    found = better_than(new, [worse, tie], specs)
    assert not found.better
    assert found.lines == ('Strength 30 vs 25, 26', 'Life stolen 8 vs 8, 10')
    eth = facts_of({**andy, 'ethereal': True, 'rolls': {'0:0': 25, '60:0': 8}}, 4, owner=Owner.PLAYER)
    assert better_than(new, [eth], specs).copies == 0  # another item


def test_the_rolls_that_matter_come_from_the_read_without_a_want():
    toe = facts_of({**GOBLIN, 'rolls': {'16:0': 50}})
    found = value.matters_for(toe, ())
    assert [(spec.key, spec.low, spec.high) for spec in found] == [('16:0', 50, 60)]


def test_owned_copies_cannot_be_told_without_a_read():
    facts = facts_of({**GOBLIN, 'rolls': {'16:0': 50}})
    assert CollectionCopies().copies(replace(facts, observation=None)) is None


def test_the_owned_bases_count_reads_the_collection_by_base_ethereal_and_sockets(tmp_path, monkeypatch):
    # The Spirit base Monarch's cap (build_wants.py SPIRIT_MONARCH_CAP, the player 2026-10-20 ~12:50): every open
    # placement of a white or superior base with the same sockets and ethereal flag, no runeword, online owners only
    import sqlite3

    from inventory_tracking.collection.store import SCHEMA

    database = tmp_path / 'collection.sqlite'
    with sqlite3.connect(database) as db:
        db.executescript(SCHEMA)
        rows = [  # fingerprint, rarity, ethereal, sockets, runeword, owner, gone
            ('a', 'normal', 0, 4, None, 'MSockB', None),
            ('b', 'superior', 0, 4, None, 'MSockC', None),
            ('c', 'normal', 0, 4, 'Spirit', 'CybergrindAA', None),  # a runeword: no base any more
            ('d', 'normal', 1, 4, None, 'MSockB', None),  # ethereal: another item
            ('e', 'normal', 0, 3, None, 'MSockB', None),  # 3os
            ('f', 'normal', 0, 4, None, 'MSockB', '2026-10-20'),  # gone
            ('g', 'normal', 0, 4, None, 'Warlock', None),  # an offline character's
        ]
        for fingerprint, rarity, ethereal, sockets, runeword, owner, gone in rows:
            db.execute(
                "INSERT INTO items VALUES (?, 'uit', 'Monarch', 'Monarch', ?, 1, ?, ?, NULL, '[]', ?, NULL, '[]', 0, "
                "NULL, 2, 3, '', '{}', 't', 't')",
                (fingerprint, rarity, ethereal, sockets, runeword),
            )
            db.execute(
                'INSERT INTO placements (fingerprint, owner, container, x, y, capture_id, seen_at, gone_at) '
                "VALUES (?, ?, 'stash', 0, 0, ?, 't', ?)",
                (fingerprint, owner, f'capture-{owner}', gone),
            )
    monkeypatch.setattr(value, 'offline_characters', lambda: frozenset(('Warlock',)))
    monkeypatch.setattr(value, '_COUNTS', {})
    plain = facts_of({'base': 'Monarch', 'code': 'uit', 'quality': 'normal', 'sockets': 4})
    assert value.owned_bases(plain, database) == 2
    assert value.owned_bases(replace(plain, ethereal=True), database) == 1
    assert value.owned_bases(replace(plain, quality=6), database) is None  # a rare: no base count
    assert value.owned_bases(plain, tmp_path / 'missing.sqlite') == 2  # counted a minute ago: reused
    monkeypatch.setattr(value, '_COUNTS', {})
    assert value.owned_bases(plain, tmp_path / 'missing.sqlite') is None  # no collection: the cap does not hold


def demon_limb(ed: int, fire: int, leech: int, unit: int, owner: Owner = Owner.LOOP):
    """A read shaped as the identify watcher's: a weapon's ED is one row of two memory stats (17 and 18)."""
    from inventory_tracking.loot.facts import from_observation

    def ranged(name, stat, low, high, raw):
        return {'status': 'decoded', 'name': name, 'value': raw, 'memory_stat': {'id': stat, 'layer': 0, 'raw': raw},
                'roll_range': {'min': low, 'max': high, 'better': 'higher'}}  # fmt: skip

    rows = [
        ranged('fireresist', 39, 15, 20, fire),
        ranged('lifedrainmindam', 60, 7, 13, leech),
        {'status': 'decoded', 'name': 'item_damage_percent', 'value': ed,
         'memory_stats': [{'id': 17, 'layer': 0, 'raw': ed}, {'id': 18, 'layer': 0, 'raw': ed}],
         'roll_range': {'min': 180, 'max': 230, 'better': 'higher'}},
    ]  # fmt: skip
    observation = {
        'item': {'name': 'Demon Limb', 'base_name': 'Tyrant Club', 'base_code': '7sp', 'rarity': 'unique',
                 'identified': True, 'ethereal': False, 'sockets': 0},
        'source': {'unit_id': unit},
        'decoded_stats': rows,
    }  # fmt: skip
    return from_observation(observation, owner=owner, unit_id=unit, size=(1, 3))


def test_a_weapons_enhanced_damage_is_compared_and_a_mixed_copy_decided_by_score():
    # Q-M6-3 (the player, 2026-10-20 ~17:30, "as recommended"): Demon Limb at 17:09:07 (unit 467414000) against the
    # owned copy: fire res 18 vs 16 and ED 206 vs 200 better, life steal 8 vs 12 worse; scores 1.287 vs 1.433
    new, owned = demon_limb(206, 18, 8, 1), demon_limb(200, 16, 12, 2, Owner.PLAYER)
    matters = value.matters_for(new, ())
    assert {spec.key for spec in matters} == {'39:0', '60:0', '17:0'}
    assert round(value.score(new, matters), 3) == 1.287
    assert round(value.score(owned, matters), 3) == 1.433
    compared = better_than(new, [owned], matters)
    assert not compared.better
    assert compared.relations == ('mixed-not-better',)
    assert 'item_damage_percent 206 vs 200' in compared.said()
    better = demon_limb(228, 18, 12, 3)  # ED and fire res better, life steal equal: better
    assert better_than(better, [owned], value.matters_for(better, ())).better


def test_a_combined_stat_of_different_values_is_still_not_compared():
    from inventory_tracking.loot.facts import from_observation

    row = {'status': 'decoded', 'name': 'damage', 'value': 10,
           'memory_stats': [{'id': 21, 'layer': 0, 'raw': 10}, {'id': 22, 'layer': 0, 'raw': 20}],
           'roll_range': {'min': 5, 'max': 30, 'better': 'higher'}}  # fmt: skip
    observation = {'item': {'name': 'x', 'base_code': '7sp', 'rarity': 'unique', 'identified': True},
                   'source': {'unit_id': 1}, 'decoded_stats': [row]}  # fmt: skip
    assert value.matters_for(from_observation(observation, owner=Owner.LOOP), ()) == ()
