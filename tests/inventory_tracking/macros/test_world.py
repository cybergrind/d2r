import struct

import pytest

from inventory_tracking.input.keybindings import RECORD
from inventory_tracking.macros.skills import CONSUME, HEX_PURGE, PSYCHIC_WARD, SUMMON_DEFILER, skill_keys
from inventory_tracking.macros.world import decode_slots, next_name
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


def test_a_skill_off_the_bar_or_on_a_mouse_button_is_named():
    with pytest.raises(ValueError, match='Consume is not on a skill key'):
        skill_keys(tuple(s for s in SLOTS if s != CONSUME), bindings({}), (CONSUME,))
    with pytest.raises(ValueError, match='Summon Defiler has no key'):
        skill_keys(SLOTS, bindings({21: 0x102}), (SUMMON_DEFILER,))


@pytest.mark.parametrize(('name', 'following'), [('cyber32', 'cyber33'), ('cyber99', 'cyber100'), ('7', '8')])
def test_next_game_name(name, following):
    assert next_name(name) == following


@pytest.mark.parametrize('name', ['pindle', 'Cyber32', 'cyber-3', ''])
def test_names_the_macro_cannot_continue(name):
    with pytest.raises(ValueError, match='number'):
        next_name(name)
