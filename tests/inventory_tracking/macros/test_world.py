import struct

import pytest

from inventory_tracking.builds.warlock.skills import CONSUME, HEX_PURGE, PSYCHIC_WARD, SUMMON_DEFILER
from inventory_tracking.input.keybindings import RECORD
from inventory_tracking.macros.skills import SWAP_WEAPONS, skill_keys
from inventory_tracking.macros.world import (
    PATH_RECORD,
    decode_slots,
    doors,
    grid_rows,
    has_room,
    local_player,
    missiles,
    monsters,
    next_name,
    unit_census,
    unit_stats,
)
from inventory_tracking.native.layout import LEVEL_AREA_ID, PATH_ROOM1, ROOM1_ROOM2, ROOM2_LEVEL
from tests.inventory_tracking.macros.fakes import SLOTS


def table(slots):
    return b''.join(struct.pack('<7I', 0xFFFFFFFF if s is None else s, 0xFFFFFFFF, 0, 4, 255, 0, 0) for s in slots)


def bindings(actions):
    return b'\x25\x00' + b''.join(RECORD.pack(action, code, 1) for action, code in actions.items())


def test_slots_decode_as_recorded_for_the_character():
    assert decode_slots(table(SLOTS)) == SLOTS


def test_a_table_of_something_else_is_rejected():
    with pytest.raises(ValueError, match='skill ids'):
        decode_slots(table((70000, *SLOTS[1:])))
    with pytest.raises(ValueError, match='Short'):
        decode_slots(b'\0' * 10)


def test_keys_come_from_the_slot_and_the_key_file():
    # The character's file, 2026-10-06: g action 18, q action 21, r action 48, 6 action 50.
    data = bindings({18: 0x47, 21: 0x51, 48: 0x52, 50: 0x36})
    assert skill_keys(SLOTS, data, (SUMMON_DEFILER, CONSUME, HEX_PURGE, PSYCHIC_WARD)) == {
        SUMMON_DEFILER: 'q',
        CONSUME: '6',
        HEX_PURGE: 'g',
        PSYCHIC_WARD: 'r',
    }


def test_a_skill_off_the_bar_or_on_a_modifier_combination_is_named():
    with pytest.raises(ValueError, match='Consume is not on a skill key'):
        skill_keys(tuple(s for s in SLOTS if s != CONSUME), bindings({}), (CONSUME,))
    with pytest.raises(ValueError, match='Summon Defiler has no key'):
        skill_keys(SLOTS, bindings({21: 0x1009}), (SUMMON_DEFILER,))


def test_a_skill_on_a_mouse_button_is_pressed_as_that_button():
    assert skill_keys(SLOTS, bindings({21: 0x102}), (SUMMON_DEFILER,)) == {SUMMON_DEFILER: 'Button9'}


@pytest.mark.parametrize(
    ('name', 'following'),
    [('cyber32', 'cyber33'), ('cyber98', 'cyber99'), ('cyber99', 'cyber1'), ('cyber287', 'cyber1'), ('7', '8')],
)
def test_next_game_name(name, following):
    assert next_name(name) == following


@pytest.mark.parametrize('name', ['pindle', 'Cyber32', 'cyber-3', ''])
def test_names_the_macro_cannot_continue(name):
    with pytest.raises(ValueError, match='number'):
        next_name(name)


def test_the_swap_key_is_read_from_the_key_file_not_assumed():
    # CybergrindAA, 2026-10-06: `c` on action 44; W, the game's default, is on another action there.
    assert skill_keys(SLOTS, bindings({44: 0x43, 46: 0x57}), (SWAP_WEAPONS,)) == {SWAP_WEAPONS: 'c'}
    with pytest.raises(ValueError, match='Swap Weapons has no key'):
        skill_keys(SLOTS, bindings({46: 0x57}), (SWAP_WEAPONS,))


TABLE = 0x100000
LEVEL, ROOM2, ROOM1 = 0x500000, 0x510000, 0x520000


class Memory:
    def __init__(self):
        self.blocks = {}

    def block(self, address, size):
        self.blocks[address] = bytearray(size)
        return self.blocks[address]

    def read(self, address, size):
        for start, data in self.blocks.items():
            if start <= address and address + size <= start + len(data):
                return bytes(data[address - start : address - start + size])
        raise ValueError(f'Unmapped or unreadable range at {address:#x}')


def character(memory, index, name, *, life=None, area=109, mode=1):
    """A player unit in bucket 1; `life` = (life, most life) in whole points, None for none readable."""
    unit_id = 128 * index + 1
    address, data, path, stats = (base + index * 0x400 for base in (0x200000, 0x300000, 0x400000, 0x600000))
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 0, 7, unit_id, mode)
    struct.pack_into('<QQQ', header, 0x10, data, 0, 0)
    struct.pack_into('<Q', header, 0x38, path)
    struct.pack_into('<Q', header, 0x88, stats)
    memory.block(data, 16)[: len(name)] = name.encode()
    struct.pack_into('<HHHH', memory.block(path, 0x28), 0, 0, 5000 + index, 0, 5000)
    struct.pack_into('<Q', memory.blocks[path], PATH_ROOM1, ROOM1)
    struct.pack_into('<Q', memory.block(ROOM1, 0x50), ROOM1_ROOM2, ROOM2)
    struct.pack_into('<Q', memory.block(ROOM2, 0xA0), ROOM2_LEVEL, LEVEL)
    struct.pack_into('<I', memory.block(LEVEL, 0x400), LEVEL_AREA_ID, area)
    full = [(0, 150), (12, 91)] if life is None else [(6, life[0] << 8), (7, life[1] << 8), (12, 91)]
    block = memory.block(stats, 0x100)
    struct.pack_into('<QQ', block, 0xE8, stats + 0x200, len(full))
    raw = memory.block(stats + 0x200, 0x100)
    for slot, (stat_id, value) in enumerate(full):
        struct.pack_into('<HHi', raw, slot * 8, 0, stat_id, value)
    return address


def chain(memory, units):
    heads = memory.block(TABLE, 1024)
    previous = 0
    for address in reversed(units):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 1 * 8, previous)


def test_the_character_is_found_beside_its_stash_tabs():
    # Shared stash tabs are player units named like the character with no life (collection/research.md R1).
    memory = Memory()
    chain(memory, [character(memory, 0, 'CybergrindAA', life=(900, 1200)), character(memory, 1, 'CybergrindAA')])
    player = local_player(memory.read, TABLE)
    assert player is not None
    assert (player.unit_id, player.name, player.area) == (1, 'CybergrindAA', 109)


def test_the_character_is_found_in_a_game_with_other_players():
    # 2026-10-08: with other players in the game the macro said "not in a game". Another player's
    # unit has a name of its own and no readable life (collection/research.md R3, `Caras`).
    memory = Memory()
    chain(
        memory,
        [
            character(memory, 0, 'Caras'),
            character(memory, 1, 'CybergrindAA', life=(900, 1200)),
            character(memory, 2, 'CybergrindAA'),
        ],
    )
    player = local_player(memory.read, TABLE)
    assert player is not None
    assert (player.unit_id, player.name) == (129, 'CybergrindAA')


def test_the_character_is_found_beside_the_corpse_it_left_on_the_level():
    # 2026-10-11, Tower Cellar Level 5: the corpse of an earlier death is a player unit named like the
    # character, dead (mode 17), without life and with the lower unit id; a take followed it for 1:56.
    memory = Memory()
    chain(
        memory,
        [
            character(memory, 0, 'CybergrindAA', mode=17),
            character(memory, 1, 'CybergrindAA', life=(1367, 1367)),
            character(memory, 2, 'CybergrindAA'),
        ],
    )
    player = local_player(memory.read, TABLE)
    assert player is not None
    assert (player.unit_id, player.mode) == (129, 1)


def test_the_dead_character_is_itself_not_an_older_corpse():
    memory = Memory()
    chain(
        memory,
        [character(memory, 0, 'CybergrindAA', mode=17), character(memory, 1, 'CybergrindAA', life=(0, 1367), mode=17)],
    )
    player = local_player(memory.read, TABLE)
    assert player is not None
    assert player.unit_id == 129


def test_no_character_when_none_or_several_have_life():
    memory = Memory()
    chain(memory, [character(memory, 0, 'Caras'), character(memory, 1, 'CybergrindAA')])
    assert local_player(memory.read, TABLE) is None
    memory = Memory()
    chain(memory, [character(memory, 0, 'Caras', life=(1, 1)), character(memory, 1, 'CybergrindAA', life=(2, 2))])
    assert local_player(memory.read, TABLE) is None


def monster(memory, index, txt_id, *, flags=0, alignment=0, owner=0xFFFFFFFF, mode=1):
    """A monster unit in bucket 2 with its type flags, owner and alignment stat."""
    unit_id = 128 * index + 2
    address, data, path, stats = (base + index * 0x400 for base in (0x700000, 0x800000, 0x900000, 0xA00000))
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 1, txt_id, unit_id, mode)
    struct.pack_into('<Q', header, 0x10, data)
    struct.pack_into('<Q', header, 0x38, path)
    struct.pack_into('<Q', header, 0x88, stats)
    block = memory.block(data, 0x80)
    block[0x1A] = flags
    struct.pack_into('<I', block, 84, owner)
    struct.pack_into('<HHHH', memory.block(path, 0x28), 0, 0, 5010 + index, 0, 5020)
    full = [(172, alignment)] if alignment else [(12, 85)]
    block = memory.block(stats, 0x100)
    struct.pack_into('<QQ', block, 0xE8, stats + 0x200, len(full))
    raw = memory.block(stats + 0x200, 0x100)
    for slot, (stat_id, value) in enumerate(full):
        struct.pack_into('<HHi', raw, slot * 8, 0, stat_id, value)
    return address


def test_monsters_carry_their_type_flags_and_whether_they_are_allies():
    memory = Memory()
    units = [
        monster(memory, 0, 19, flags=0x0C),  # a champion
        monster(memory, 1, 19, flags=0x10),  # a minion
        monster(memory, 2, 744, alignment=2),  # the character's own Defiler
        monster(memory, 3, 338, owner=1),  # the mercenary, owned
        monster(memory, 4, 19, mode=12),  # a corpse
    ]
    heads = memory.block(TABLE + 1024, 1024)
    previous = 0
    for address in reversed(units):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 2 * 8, previous)

    found = monsters(memory.read, TABLE)

    assert [(m.unit_id, m.flags, m.ally, m.owner, m.leader) for m in found] == [
        (2, 0x0C, False, 0xFFFFFFFF, True),
        (130, 0x10, False, 0xFFFFFFFF, False),
        (258, 0, True, 0xFFFFFFFF, False),
        (386, 0, False, 1, False),
    ]
    assert (found[0].x, found[0].y) == (5010.0, 5020.0)


def test_dead_monsters_are_read_on_request_with_their_stat_list_address():
    memory = Memory()
    units = [monster(memory, 0, 19), monster(memory, 4, 19, mode=12)]
    heads = memory.block(TABLE + 1024, 1024)
    previous = 0
    for address in reversed(units):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 2 * 8, previous)

    assert [m.unit_id for m in monsters(memory.read, TABLE)] == [2]
    found = monsters(memory.read, TABLE, dead=True)
    assert [(m.unit_id, m.mode) for m in found] == [(2, 1), (514, 12)]
    assert unit_stats(memory.read, found[0].stats_at) == {12: 85}
    assert unit_stats(memory.read, 0x1) == {}


def test_the_whole_path_record_is_read_on_request_and_its_absence_keeps_the_monster():
    memory = Memory()
    units = [monster(memory, 0, 19), monster(memory, 1, 19)]
    whole = memory.block(0x900000, PATH_RECORD)  # the first monster's record, readable to its end
    struct.pack_into('<HHHH', whole, 0, 0, 5010, 0, 5020)
    struct.pack_into('<HH', whole, 0x10, 5033, 5044)
    heads = memory.block(TABLE + 1024, 1024)
    struct.pack_into('<Q', memory.blocks[units[0]], 0x158, units[1])
    struct.pack_into('<Q', heads, 2 * 8, units[0])

    assert [m.path for m in monsters(memory.read, TABLE)] == [b'', b'']
    found = monsters(memory.read, TABLE, paths=True)
    assert [(m.unit_id, m.x, len(m.path)) for m in found] == [(2, 5010.0, PATH_RECORD), (130, 5011.0, 0)]
    assert struct.unpack_from('<HH', found[0].path, 0x10) == (5033, 5044)


def missile(memory, address, path, unit_id, slot):
    header = memory.block(address, 0x160)
    struct.pack_into('<IIII', header, 0, 3, 750, unit_id, 0)
    struct.pack_into('<Q', header, 0x38, path)
    struct.pack_into('<HH', header, 0xC4, 5012, 5030)
    memory.block(path, 0x30)[:4] = b'\x01\x02\x03\x04'
    struct.pack_into('<Q', memory.block(TABLE + slot * 1024, 1024), (unit_id % 128) * 8, address)


def test_missiles_are_dumped_raw_from_the_client_and_the_server_slots():
    memory = Memory()
    missile(memory, 0xB00000, 0xB10000, 3 + 128 * 2, 3)  # another unit's bolt
    missile(memory, 0xB20000, 0xB30000, 5, 9)  # the player's own blade: the server missile slot

    found = missiles(memory.read, TABLE)
    assert [(x['unit_id'], x['txt_id'], x['slot'], x['xy']) for x in found] == [
        (259, 750, 3, [5012, 5030]),
        (5, 750, 9, [5012, 5030]),
    ]
    assert found[0]['path'].startswith('01020304')
    assert len(found[0]['path']) == 0x60
    assert len(found[0]['record']) == 0x2C0


def test_the_unit_census_says_what_hangs_off_each_slot():
    memory = Memory()
    for slot in range(12):
        memory.block(TABLE + slot * 1024, 1024)
    missile(memory, 0xB20000, 0xB30000, 5, 9)
    census = unit_census(memory.read, TABLE)
    assert census[9] == {'slot': 9, 'heads': 1, 'first': [3, 750, 5, 0], 'units': 1}
    assert census[3] == {'slot': 3, 'heads': 0}
    assert len(census) == 12


def test_door_objects_are_read_with_their_mode_and_static_position():
    memory = Memory()
    heads = memory.block(TABLE + 2 * 1024, 1024)
    units = []
    for index, (txt, mode) in enumerate(((15, 0), (16, 2), (139, 0))):  # a closed wooden door, an opened one, a chest
        unit_id = 128 * index + 5  # all in bucket 5, chained
        address, path = 0xC00000 + index * 0x400, 0xC10000 + index * 0x400
        header = memory.block(address, 0x160)
        struct.pack_into('<IIII', header, 0, 2, txt, unit_id, mode)
        struct.pack_into('<Q', header, 0x38, path)
        block = memory.block(path, 0x18)
        struct.pack_into('<II', block, 0x10, 7800 + index, 5600)
        units.append(address)
    previous = 0
    for address in reversed(units):
        struct.pack_into('<Q', memory.blocks[address], 0x158, previous)
        previous = address
    struct.pack_into('<Q', heads, 5 * 8, previous)

    found = doors(memory.read, TABLE)
    assert [(d.txt_id, d.mode, d.x, d.y, d.closed) for d in found] == [
        (15, 0, 7800.0, 5600.0, True),
        (16, 2, 7801.0, 5600.0, False),
    ]
    assert found[0].radius == 2.5  # 1 x 3 sub-tiles: half of 3, plus the slack


def hover_memory(records):
    from inventory_tracking.macros.world import HOVER_RVA, GameMemory

    memory = object.__new__(GameMemory)
    memory.base, memory.hover_raw = 0x1000, None
    reads = iter(records)

    def read(address, size):
        assert (address, size) == (0x1000 + HOVER_RVA - 4, 16)
        return struct.pack('<IIII', *next(reads))

    memory.read = read
    return memory


def test_a_hover_record_without_its_flag_is_a_leftover():
    # The record keeps the last unit after the pointer has left it: 43 of 130 clicks at the aim 14
    # pixels up walked the character to the ground under the label (logs up to 2026-10-11).
    # The Tower, 17:21 on 2026-10-11: 0x101 at the 5 aims that took the item, 0 at 7 that named an old one.
    memory = hover_memory([(0x101, 4, 77, 0x130013), (0, 4, 77, 0x130013), (0x101, 1, 5, 0x130013)])
    assert memory.hovered() == (4, 77)
    assert memory.hovered() is None
    assert memory.hover_note() == 'flag 0x0 type 4 id 77 tail 0x130013'
    assert memory.hovered() == (1, 5)


def test_what_the_marks_point_at_is_prized_and_the_rest_of_the_pickup_is_not():
    """user, 2026-10-12: a full inventory stops the pickup press only for what is "very valuable"."""
    from inventory_tracking.macros.world import prized

    assert prized('rune', marked=True)  # a rune from the marks' own minimum up
    assert not prized('rune', marked=False)  # the low runes the pickup takes besides
    assert prized('unique', marked=True)
    assert prized('material', marked=True)  # a material the marks point at
    assert not prized('material', marked=False)  # every ring and jewel, the gems the filter shows
    assert not prized('shown', marked=False)  # magic, rare and white equipment the loot filter shows


def test_a_unique_or_set_item_the_filter_shows_is_prized_and_magic_rare_or_white_gear_is_not():
    """The player, 2026-10-14 (rca/2026-10-14/run-1214-findings.md §3.1): the run walked past a Unique Plate Mail
    with the inventory full and the player fetched it by hand; the Magic Bone Knife stays as ruled on 2026-10-12."""
    from inventory_tracking.macros.world import NAMED, prized, shown_source

    unique, set_item, magic, rare, superior = 7, 5, 4, 6, 3  # ItemData quality (loot/shown.py RARITIES)
    assert shown_source(unique) == shown_source(set_item) == NAMED
    assert prized(NAMED, marked=False)
    assert {shown_source(quality) for quality in (magic, rare, superior)} == {'shown'}


def test_a_grid_reads_as_rows_and_the_cubes_three_by_four_has_no_room_for_a_grand_charm_in_two_cells():
    # The Horadric Cube's grid (rca/2026-10-13/pickup-cube.md §3: grid 5, 3x4) as the inventory's is read
    taken = 0x1000
    cells = [taken, 0, taken, 0, 0, taken, taken, taken, taken, taken, taken, taken]
    rows = grid_rows({'width': 3, 'height': 4, 'cells': cells})
    assert rows == ('#.#', '..#', '###', '###')
    assert has_room(rows, (1, 2))
    assert not has_room(rows, (1, 3))  # a Grand Charm
    assert grid_rows(None) is None  # no cube


def test_an_item_the_character_carried_and_the_player_put_down_is_left_for_the_game_where_it_lies(caplog):
    """The Superior Crystal Sword of 00:28:24-31 on 2026-10-14 (rca/2026-10-14/run-0025-findings.md §3): taken by
    the run (unit 490846825), looked at and put down by the player with the same unit id, back in view later with new
    unit ids at the same place (1237984317, 3010135405), and after Diablo the loot step named it again: "Inventory
    full: Superior Crystal Sword left on the ground", 71 away. A ground item whose unit id the character carried this
    game is the player's put down: out of every drop the macro reads (`choose`, the side drops, the stay-by, the
    warning), by its class and place for the rest of the game."""
    from dataclasses import replace

    from inventory_tracking.macros.world import VALUABLE, Drop, Loot, PutDown

    game = ('cyber32', 7)
    sword = Drop(490846825, 7771.0, 5358.0, 'Superior Crystal Sword', VALUABLE, (2, 3), prized=False)
    belt = Drop(612, 7799.0, 5293.0, 'Magic Light Belt', VALUABLE, (2, 1), prized=False)
    memory = PutDown()
    assert memory.see(Loot((), game=game, carried=frozenset({sword.unit_id}))).drops == ()  # in the inventory
    classes = ((sword.unit_id, 29), (belt.unit_id, 345))
    with caplog.at_level('INFO'):
        assert memory.see(Loot((sword, belt), game=game, classes=classes)).drops == (belt,)  # the same unit
    assert caplog.text.count('Macro: put down:') == 1
    again = replace(sword, unit_id=1237984317)  # back in view with a new unit id at the same place
    assert memory.see(Loot((again, belt), game=game, classes=((again.unit_id, 29),))).drops == (belt,)
    assert memory.at(again.x + 0.5, again.y, 29)
    assert memory.at(again.x, again.y)  # a mark of no known class (the HUD's) at that place
    other = replace(sword, unit_id=5)  # another item where the sword lies
    assert memory.see(Loot((other,), game=game, classes=((5, 30),))).drops == (other,)
    assert memory.see(Loot((again,), game=None)).drops == (again,)  # an unread game: as read
    assert memory.see(Loot((again,), game=('cyber33', 7))).drops == (again,)  # the next game forgets
    assert not memory.at(again.x, again.y)


def test_an_item_picked_up_between_a_looks_drops_and_its_grids_is_not_put_down(caplog):
    """The Amulet Diablo dropped, 06:08:58.668 on 2026-10-14 (rca/2026-10-14/run-0305-findings.md §5.3): the macro
    clicked it at 58.05 and had it 0.61 s later; one `Loot` read it on the ground (the drops are read first) and in
    the inventory (the grids last), and the memory said "put down" for the macro's own pickup. A drop counts as put
    down only when an earlier look had it carried."""
    from inventory_tracking.macros.world import VALUABLE, Drop, Loot, PutDown

    game = ('cbyer9', 7)
    amulet = Drop(2285477250, 7793.0, 5296.0, 'Amulet', VALUABLE, (1, 1), prized=False)
    classes = ((amulet.unit_id, 520),)
    memory = PutDown()
    with caplog.at_level('INFO'):
        assert memory.see(Loot((amulet,), game=game, classes=classes)).drops == (amulet,)  # on the ground
        picked = Loot((amulet,), game=game, classes=classes, carried=frozenset({amulet.unit_id}))
        assert memory.see(picked).drops == (amulet,)  # picked up during the look: not the player's put down
        assert memory.see(Loot((), game=game, carried=frozenset({amulet.unit_id}))).drops == ()
    assert 'Macro: put down:' not in caplog.text
    assert not memory.at(amulet.x, amulet.y)
    # the player's put down after it is still told: the same unit back on the ground
    assert memory.see(Loot((amulet,), game=game, classes=classes)).drops == ()
    assert memory.at(amulet.x, amulet.y, 520)


def test_the_carried_items_are_the_item_pointers_of_the_characters_grids():
    from inventory_tracking.macros.world import held_items

    grids = {0: {'width': 2, 'height': 1, 'cells': [0x1000, 0]}, 5: {'width': 1, 'height': 2, 'cells': [0, 0x2000]}}
    assert held_items(grids) == frozenset({0x1000, 0x2000})
    assert held_items({}) == frozenset()


def test_a_white_daggers_sockets_and_staff_mods_are_read_off_the_ground_and_said():
    # The player, 18:56 on 2026-10-17: "we need good staff mod and we need 3os" (macros/pickmode.py `void_base`)
    from inventory_tracking.items.identity import ITEM_DATA_SIZE
    from inventory_tracking.macros.world import BASE_ROLLS_SEEN, FULL_STATS, VALUABLE, Drop, Rolls, rolled, rolls

    BASE_ROLLS_SEEN.clear()
    stats_at, array = 0x1000, 0x2000
    # (layer, stat id, value): 3 sockets, +3 Abyss (skill 402 in stat 107's layer), a durability that is not a skill
    entries = [(0, 194, 3), (402, 107, 3), (0, 72, 24)]
    data_at = 0x3000
    memory = {
        stats_at + FULL_STATS: struct.pack('<QQ', array, len(entries)),
        array: b''.join(struct.pack('<HHi', *entry) for entry in entries),
        data_at: bytes(ITEM_DATA_SIZE),
    }

    def read(address: int, size: int) -> bytes:
        return memory[address][:size]

    kriss = Drop(7, 0.0, 0.0, 'Kriss', VALUABLE, source='shown', txt=41, quality=2)
    found = rolled(read, kriss, {'unit_id': 7, 'stats_pointer': stats_at, 'data_pointer': data_at})
    assert found.rolls == Rolls(3, ((402, 3),))
    assert rolls(found) == ' 3os +3 Abyss'
    rare = Drop(8, 0.0, 0.0, 'Kriss', VALUABLE, source='shown', txt=41, quality=6)
    assert rolled(read, rare, {'unit_id': 8, 'stats_pointer': stats_at, 'data_pointer': data_at}) == rare  # identified
    assert rolls(kriss) == ''


def test_enigmas_teleport_is_the_characters_own_and_the_staff_on_the_swap_is_left_alone(monkeypatch):
    # The live capture of 22:26 on 2026-10-17: Enigma on the body (location 3) gives (97, 54, 1), "+1 to Teleport";
    # Naj's Puzzler, an Elder Staff (class 261), on the swap (11) holds 69/69 Teleport charges, (204, 54 << 6 | 11)
    from inventory_tracking.macros import world

    enigma, staff = (
        {'unit_id': 1, 'txt_id': 373, 'stats_pointer': 100},
        {'unit_id': 2, 'txt_id': 261, 'stats_pointer': 200},
    )
    offset = world.TELEPORT_STATS
    assert offset is not None
    stats = {
        100 + offset: [{'id': 31, 'layer': 0, 'raw': 1005}, {'id': 97, 'layer': 54, 'raw': 1}],
        200 + offset: [{'id': 204, 'layer': 54 << 6 | 11, 'raw': 69 << 8 | 69}],
    }
    reads = []

    def read_stats(read, address):
        reads.append(address)
        return stats[address]

    def location(spot: int) -> bytes:
        data = bytearray(0x60)
        data[world.ITEM_BODY_LOCATION] = spot
        return bytes(data)

    monkeypatch.setattr(world, 'read_stats', read_stats)
    memory = object.__new__(world.GameMemory)
    memory.worn_held, memory.worn_skills_of = None, frozenset()
    worn = [(staff, location(11))]
    monkeypatch.setattr(memory, '_equipped', lambda: iter(worn))
    assert memory.teleport() == world.Teleport(69, 69, in_hand=False)  # the staff alone: its charges, swapped in
    assert memory.own_teleport() is False
    worn.append((enigma, location(3)))
    assert memory.own_teleport() is True
    assert memory.teleport() is None  # Teleport of its own: no swap, no charge (movement.py OwnTeleport)
    before = len(reads)
    assert memory.teleport() is None
    assert len(reads) == before  # the same items worn: their stats are not read again
    # A +Teleport item on the other set is not the character's while that set is not in hand
    worn[:] = [(staff, location(11)), (enigma, location(12))]
    assert memory.own_teleport() is False


def test_the_slings_town_portal_is_a_worn_skill_and_an_unreadable_look_keeps_the_last_read(monkeypatch):
    # uniqueitems.txt Sling (a Ring, `rin`): `oskill` "Townportal O Skill" 1, item_nonclassskill (97) with skill 411 its
    # layer, as Enigma's Teleport is (97, 54, 1); the player, 2026-10-18: the Sling in place of the tome
    from inventory_tracking.macros import world
    from inventory_tracking.macros.skills import SLING_TOWN_PORTAL

    sling, enigma = (
        {'unit_id': 1, 'txt_id': 537, 'stats_pointer': 100},
        {'unit_id': 2, 'txt_id': 373, 'stats_pointer': 200},
    )
    offset = world.TELEPORT_STATS
    assert offset is not None
    stats = {
        100 + offset: [{'id': 105, 'layer': 0, 'raw': 10}, {'id': 97, 'layer': SLING_TOWN_PORTAL, 'raw': 1}],
        200 + offset: [{'id': 97, 'layer': 54, 'raw': 1}],
    }
    monkeypatch.setattr(world, 'read_stats', lambda read, address: stats[address])

    def location(spot: int) -> bytes:
        data = bytearray(0x60)
        data[world.ITEM_BODY_LOCATION] = spot
        return bytes(data)

    memory = object.__new__(world.GameMemory)
    memory.worn_held, memory.worn_skills_of = None, frozenset()
    worn: list = []
    unreadable = []

    def equipped():
        if unreadable:
            raise OSError('short read')
        return iter(worn)

    monkeypatch.setattr(memory, '_equipped', equipped)
    unreadable.append(True)
    assert memory.worn_skills() is None  # never read: not known
    unreadable.clear()
    assert memory.worn_skills() == frozenset()
    worn[:] = [(sling, location(7)), (enigma, location(3))]  # a ring finger, the body
    assert memory.worn_skills() == {SLING_TOWN_PORTAL, 54}
    assert memory.own_teleport() is True
    unreadable.append(True)
    assert memory.worn_skills() == {SLING_TOWN_PORTAL, 54}  # the last read: the Sling is not taken off by a lost read
    assert memory.own_teleport() is None
    unreadable.clear()
    worn[:] = [(enigma, location(3))]
    assert memory.worn_skills() == {54}


def test_the_most_worn_item_is_the_least_share_of_its_durability_with_the_ethereal_and_indestructible_aside():
    # The live capture of 22:26 on 2026-10-17: Enigma (Mage Plate, class 373) at 33 of 60, Spirit at 86 of 86
    from inventory_tracking.items.identity import ETHEREAL_FLAG
    from inventory_tracking.macros.world import Wear, least_worn

    def lasting(now: int, most: int) -> list[dict]:
        return [{'id': 72, 'layer': 0, 'raw': now}, {'id': 73, 'layer': 0, 'raw': most}]

    enigma, spirit = (373, 0, lasting(33, 60)), (447, 0, lasting(86, 86))
    assert least_worn([spirit, enigma]) == Wear(373, 33, 60)
    assert least_worn([spirit, (100, ETHEREAL_FLAG, lasting(1, 50)), enigma]) == Wear(373, 33, 60)  # no vendor mends it
    assert least_worn([(200, 0, [{'id': 31, 'layer': 0, 'raw': 99}])]) is None  # indestructible: no durability
    assert least_worn([]) is None


def test_a_call_to_arms_in_either_set_is_read_from_the_worn_items(monkeypatch):
    # CybergrindAA's swap since 22:58 on 2026-10-17: the Call to Arms (a Flail, class 21) at location 11
    from inventory_tracking.macros import world

    offset = world.TELEPORT_STATS
    assert offset is not None
    cta, hoto = {'unit_id': 1, 'txt_id': 21, 'stats_pointer': 100}, {'unit_id': 2, 'txt_id': 21, 'stats_pointer': 200}
    stats = {100 + offset: [{'id': 97, 'layer': 149, 'raw': 4}], 200 + offset: [{'id': 127, 'layer': 0, 'raw': 3}]}
    monkeypatch.setattr(world, 'read_stats', lambda read, address: stats[address])

    def location(spot: int) -> bytes:
        data = bytearray(0x60)
        data[world.ITEM_BODY_LOCATION] = spot
        return bytes(data)

    memory = object.__new__(world.GameMemory)
    memory.orders_of, memory.cta_seen = {}, None
    worn = [(hoto, location(4)), (cta, location(11))]
    monkeypatch.setattr(memory, '_equipped', lambda: iter(worn))
    assert memory.cta() is True
    memory.cta_seen = None
    worn[1] = (cta, location(4))  # swapped in: still worn
    worn[0] = (hoto, location(11))
    assert memory.cta() is True
    assert memory.hands() == (world.CTA_CODE,)  # the set in hand reads it as the Call to Arms, not `fla`
    memory.cta_seen = None
    worn[:] = [(hoto, location(4))]
    assert memory.cta() is False


def stash_owner(unit_id: int, order: int, stats=()) -> dict:
    """A player unit as `GameMemory.stash_view` reads it: its name and full stats (collection/capture.py)."""
    return {
        'unit_id': unit_id,
        'type': 0,
        'details': {'name': 'CybergrindAA', 'full_stats': [{'id': s, 'layer': 0, 'raw': 1} for s in stats]},
        'order': order,
    }


def stash_grid(cells: dict[int, int]) -> dict:
    """A 10 x 10 grid whose cells (index -> item address) hold items."""
    return {'width': 10, 'height': 10, 'cells': [cells.get(i, 0) for i in range(100)]}


def test_the_stash_view_orders_the_shared_pages_and_drops_the_resource_tabs_owner():
    # collection/research.md R1: the shared owners ordered by +0xD8 (1105634203 -> 1227, ..., 2719888953 -> 1314), the
    # empty sixth unit (order 1329) owns the Gems, Materials and Runes tabs; the stacks are owner-less page-4 units
    from inventory_tracking.macros.world import NO_OWNER, stash_view_of

    main = stash_owner(1, 1226, stats=(6, 7, 12))
    shared = [stash_owner(u, o) for u, o in ((50, 1314), (10, 1227), (30, 1289), (20, 1268), (40, 1308), (60, 1329))]
    party = stash_owner(70, 1000, stats=(6, 7, 12))  # another player's character: a level and a life
    grids = {
        1: {6: stash_grid({0: 0xA0})},
        10: {6: stash_grid(dict.fromkeys(range(100), 176))},  # full
        20: {6: stash_grid({})},
        30: {6: stash_grid({})},
        40: {6: stash_grid({})},
        50: {6: stash_grid({5: 0xC0, 6: 0xC0})},
        60: {6: stash_grid({})},
        70: {6: stash_grid({})},
    }
    items = [
        {'unit_id': 900, 'address': 0xA0, 'txt_id': 537, 'mode': 0, 'owner': 1, 'page': 4},
        {'unit_id': 901, 'address': 0xB0, 'txt_id': 363, 'mode': 0, 'owner': 10, 'page': 4},
        {'unit_id': 902, 'address': 0xC0, 'txt_id': 620, 'mode': 0, 'owner': 50, 'page': 4},
        {'unit_id': 903, 'address': 0xD0, 'txt_id': 631, 'mode': 0, 'owner': NO_OWNER, 'page': 4, 'count': 99},
        {'unit_id': 904, 'address': 0xD8, 'txt_id': 639, 'mode': 0, 'owner': NO_OWNER, 'page': 4, 'count': 25},
        {'unit_id': 905, 'address': 0xE0, 'txt_id': 585, 'mode': 3, 'owner': NO_OWNER, 'page': 0},  # on the ground
    ]

    view = stash_view_of(main, [*shared, party], grids, items)

    assert view is not None
    assert [page.owner for page in view.pages] == [1, 10, 20, 30, 40, 50]
    assert [page.free for page in view.pages] == [99, 0, 100, 100, 100, 98]
    assert view.page_of(902) == 5
    assert view.page_of(900) == 0
    assert view.page_of(903) is None
    assert view.stacks == ((631, 99), (639, 25))
    assert view.full() == {631}
    assert view.room(639) == 74
    assert view.room(585) == 99  # a class not held: an empty stack
    assert view.said() == 'pages free 0:99 1:0 2:100 3:100 4:100 5:98; full stacks Tal Rune'
    # A shared page missing: no view (the pages' numbers would be told wrong)
    assert stash_view_of(main, shared[1:], grids, items) is None
    # A shared page emptied (the player's mules, 20:18 on 2026-10-18) has no grid allocated: an empty page, not no view
    emptied = {**grids, 50: {}}
    again = stash_view_of(main, [*shared, party], emptied, [i for i in items if i['unit_id'] != 902])
    assert again is not None
    assert [page.free for page in again.pages] == [99, 0, 100, 100, 100, 100]
    assert again.full() == {631}


def test_an_items_tree_and_class_skills_are_read_off_their_layers():
    # 08:17 on 2026-10-19: Wraithra Clasp, +2 to Summoning Skills (188 on the tree's layer), read on layer 0 alone had
    # no skills and was sold; keepers.py keeps a rare amulet with +2 skills
    from inventory_tracking.macros.keepers import amulet_keeper
    from inventory_tracking.macros.world import Carried, item_values

    read = [
        {'id': 188, 'layer': 41, 'raw': 2},  # +2 to a skill tree
        {'id': 83, 'layer': 7, 'raw': 1},  # +1 to a class's skills
        {'id': 0, 'layer': 0, 'raw': 18},  # strength
        {'id': 34, 'layer': 0, 'raw': 3},  # damage reduced
    ]
    values = item_values(read)
    assert values == {188: 2, 83: 1, 0: 18, 34: 3}
    amulet = Carried(1, 535, 0, 0, (1, 1), quality=6)
    assert amulet_keeper(amulet, values) == '+2 skills'
