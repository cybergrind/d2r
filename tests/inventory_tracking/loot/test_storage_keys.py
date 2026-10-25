"""The key stack's arrangement and the character's protected cells (loot/storage.py `keys_move`, `volatile_rows`,
`stash_stop`'s moves aside; macros/volatile.py). 2026-10-25 (game cybergg14, rca/2026-10-25/keys-protected-findings.md):
at 01:53:11 the keys were moved off the protected (2, 2) into the 2 x 4 block in columns 3-4, the only room the player
leaves the loop ("the loop's space is the 2x4 block in columns 3-4 only", the player, 2026-10-24); a picked Ring then
landed on the empty (2, 2) and was read as the player's, and at 02:06 the visit left the block taken and the loop
stopped by a Buriza-Do Kyanon (2 x 4) on the ground."""

import pytest

from inventory_tracking.game.records import Carried, Pack, Page, StashView
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot import storage
from inventory_tracking.loot.storage import BIG_BLOCK, KEY_CLASS, SURE_BLOCK, Holdings, keys_move, volatile_rows
from inventory_tracking.macros.volatile import cells_of, own_of


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


def at(unit: int, x: int, y: int, size: tuple[int, int] = (1, 1), txt: int | None = None) -> Carried:
    return Carried(unit, class_of('Small Charm') if txt is None else txt, x, y, size)


# CybergrindAA's inventory as the loop read it at 02:23:28 on 2026-10-25, the player's items only: every cell but the
# 2 x 4 block in columns 3-4 (and (2, 2), the keys' cell) is covered
PLAYERS = (
    at(1, 0, 0, (1, 3), class_of('Grand Charm')), at(2, 1, 0, (2, 2), storage.CUBE_CLASS), at(3, 5, 0), at(4, 6, 0),
    at(5, 7, 0), at(6, 8, 0), at(7, 9, 0, (1, 2), class_of('Tome of Identify')), at(8, 5, 1, (1, 3)),
    at(9, 6, 1, (1, 3)), at(10, 7, 1, (1, 3)), at(11, 8, 1, (1, 3)), at(12, 1, 2, (1, 2)), at(13, 9, 2, (1, 2)),
    at(14, 0, 3), at(15, 2, 3),
)  # fmt: skip
KEYS = at(20, 2, 2, txt=KEY_CLASS)
# The volatile store's protected cells for the character (runs/alt-d/volatile-cells.json, 2026-10-24 17:07)
PROTECTED = frozenset(c for item in (*PLAYERS, KEYS) for c in cells_of(item))
BOOTS = Carried(30, class_of('Chain Boots'), 3, 0, (2, 2))  # the loop's: Demon Stalker, dropped at 01:53:31
RING = Carried(31, class_of('Ring'), 4, 3, (1, 1))  # a small item of the loop's in the block


def test_the_protected_cells_are_every_cell_but_the_block_in_columns_three_and_four():
    rows = volatile_rows(Pack(()).inventory, PROTECTED)
    assert rows == ('###..#####',) * 4
    assert volatile_rows(Pack(()).inventory, frozenset()) == Pack(()).inventory  # none: the raw grid


def test_the_keys_on_a_protected_cell_never_move_into_the_loops_block():
    # 01:53:11: the cube's room asked for a Grand Charm (1 x 3); the raw grid's best was the keys (2, 2) -> (3, 3)
    pack = Pack((*PLAYERS, KEYS, BOOTS, RING))
    assert not pack.inventory.has_room(SURE_BLOCK)
    old = keys_move(pack)
    assert old is not None
    assert (old[0].x, old[0].y, old[1]) == (2, 2, (3, 3))  # the incident's move, the protected cells unknown

    assert keys_move(pack, BIG_BLOCK, PROTECTED) is None
    assert keys_move(pack, SURE_BLOCK, PROTECTED) is None


def test_the_keys_in_the_block_go_back_onto_the_free_protected_cell_they_left():
    # 02:06: the keys at (3, 3) in the block, (2, 2) empty (the Ring on it already dropped): only that frees the 2 x 4
    keys = at(20, 3, 3, txt=KEY_CLASS)
    pack = Pack((*PLAYERS, keys))
    assert not volatile_rows(pack.inventory, PROTECTED).has_room(BIG_BLOCK)

    move = keys_move(pack, BIG_BLOCK, PROTECTED)

    assert move == (keys, (2, 2))
    after = Pack((*PLAYERS, at(20, 2, 2, txt=KEY_CLASS)))
    assert volatile_rows(after.inventory, PROTECTED).has_room(BIG_BLOCK)


def test_a_free_protected_cell_is_never_taken_for_a_larger_block_alone():
    # The keys at (3, 3) with a loop item in the block too: no move frees the 2 x 4, so none onto (2, 2)
    keys = at(20, 3, 3, txt=KEY_CLASS)
    pack = Pack((*PLAYERS, keys, at(31, 4, 0, txt=class_of('Ring'))))

    move = keys_move(pack, BIG_BLOCK, PROTECTED)

    assert move is None or move[1] not in PROTECTED


def test_a_cell_of_a_larger_hole_the_player_left_is_never_taken_by_the_keys():
    # The player took out the Grand Charm at (0, 0) by hand: its three cells are free and protected; the keys in the
    # block stay there rather than take a cell the charm may come back to
    keys = at(20, 3, 3, txt=KEY_CLASS)
    pack = Pack((*[i for i in PLAYERS if i.unit_id != 1], at(16, 2, 2, txt=class_of('Ring')), keys))

    assert keys_move(pack, BIG_BLOCK, PROTECTED) is None


def test_with_the_switch_off_the_keys_go_only_onto_volatile_cells(monkeypatch):
    monkeypatch.setattr(storage, 'KEYS_ONTO_PROTECTED', False)
    keys = at(20, 3, 3, txt=KEY_CLASS)

    assert keys_move(Pack((*PLAYERS, keys)), BIG_BLOCK, PROTECTED) is None


@pytest.mark.parametrize('protect_keys', [False, True])
def test_a_key_stack_on_a_volatile_cell_still_makes_the_block(protect_keys):
    # The player, 19:10 on 2026-10-17: "move key two cells left to make continuous 2x4 space". Columns 4-9 taken by
    # the player's, the keys in the middle of the free columns 0-3: moved within the volatile cells
    rest = Carried(30, 600, 4, 0, (6, 4))
    stack = Carried(32, KEY_CLASS, 1, 1, (1, 1))
    protected = frozenset(cells_of(rest)) | (frozenset({(0, 0)}) if protect_keys else frozenset())

    move = keys_move(Pack((rest, stack)), BIG_BLOCK, protected)

    assert move is not None
    assert move[0] is stack
    assert move[1] not in protected
    left = Pack((rest, Carried(32, KEY_CLASS, *move[1], (1, 1)))).inventory
    assert volatile_rows(left, protected).has_room(BIG_BLOCK)


def test_the_stash_stop_never_moves_aside_a_key_stack_on_the_players_cells():
    # `stash_stop`'s moves aside (step iv) take the keys as movable: a Belt (2 x 1) out of the cube found its block
    # over (2, 2) and (3, 2) once the keys went to (3, 3), and landed half on the protected cell, the player's from then
    # on. The player's keys (on a protected cell: `own`) stay; the belt waits in the cube. The other keepers have no
    # page (the stash full), so they stay in the block
    boots, charm = BOOTS, Carried(32, class_of('Large Charm'), 4, 2, (1, 2))  # the loop's keepers, no page for them
    belt = Carried(33, class_of('Belt'), 0, 0, (2, 1))
    pack = Pack((*PLAYERS, KEYS, boots, charm), ('##.', '###', '###', '###'), frozenset({belt.unit_id}), (belt,))
    own = own_of(pack, PROTECTED)
    assert (KEY_CLASS, 2, 2) in own
    page = ('.' * 2 + '#' * 8,) + ('#' * 10,) * 9  # room for the belt alone
    view = StashView(tuple(Page(index, page if index == 3 else ('#' * 10,) * 10) for index in range(6)))
    old = storage.stash_stop(Holdings(pack, own - {(KEY_CLASS, 2, 2)}), view)
    assert [(item.unit_id, cell) for item, cell in old.shuffles] == [(KEYS.unit_id, (3, 3))]  # as before the fix

    stop = storage.stash_stop(Holdings(pack, own), view)

    assert stop.shuffles == ()
    assert stop.waits == (belt,)  # in the cube until the loop's own room frees a block
