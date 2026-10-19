"""The controller-mode gaps closed (rca/2026-10-13/controller-gaps.md): Summon Defiler on B makes the Consume
upkeep and its re-summon castable by the pad, Consume is pressed only while the client's target names the
Defiler, the prebuff runs by the pad, and records 12-15 (no pad button) are cast by keyboard keys only after a
game's probe showed a key reaching its controller record (`KeyRoute`, `Pad key:`)."""

import logging
import struct
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock.buffs import BUFFS, consume_due, purge_shown
from inventory_tracking.builds.warlock.casters import consume as consume_defiler, engorge, renew_consume
from inventory_tracking.builds.warlock.skills import (
    BIND_DEMON,
    CONSUME,
    ENGORGE,
    HEX_PURGE,
    PSYCHIC_WARD,
    SUMMON_DEFILER,
)
from inventory_tracking.input.keybindings import RECORD as KEY_RECORD
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import Casting
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.game.layout import DEFILER_CLASS
from inventory_tracking.macros.game.records import Monster
from inventory_tracking.macros.pad import MONSTER_UNIT, KeyRoute, pad_slots, records
from inventory_tracking.macros.routines import prebuff, press_skill, run_macro
from inventory_tracking.macros.skills import slot_action
from tests.inventory_tracking.macros.fakes import SLOTS, character_of, player, world
from tests.inventory_tracking.macros.moves import ASPECT
from tests.inventory_tracking.macros.test_pad import BINDINGS, Controller, pad_of


# The table of 2026-10-13 late (config gamepad_bindings): Summon Defiler on B, Bind Demon and Engorge on 12 and 13.
GAPS = (*BINDINGS[:2], SUMMON_DEFILER, *BINDINGS[3:12], BIND_DEMON, ENGORGE, *BINDINGS[14:])
BOUND_DEMON = 361  # the Pit Lord the player binds (controller-gaps.md section 1)
# CybergrindAA's skill slots as its key file has them (2026-10-13): slot 6 mouse 5, 8 `W`, 12 `6`, 13 `7`, 14 KP_5.
SLOT_CODES = {0: 0x41, 6: 0x102, 7: 0x51, 8: 0x57, 12: 0x36, 13: 0x37, 14: 0x65, 15: 0x101}
KEY_SLOTS = {'a': 0, 'q': 7, 'w': 8, '6': 12, '7': 13}


def key_file() -> bytes:
    """A key file (input/keybindings.py layout) with the skill slots of SLOT_CODES, each its primary key."""
    rows = b''.join(KEY_RECORD.pack(slot_action(slot), code, 1) for slot, code in SLOT_CODES.items())
    return struct.pack('<H', 37) + rows


class Gaps(Controller):
    """The controller game with the table above: Summon Defiler on B puts a Defiler beside the character (the
    client's target names it), Consume takes the unit the client's target names; a keyboard skill key casts the
    controller record of its slot when `keys_reach` (as the client's code reads with Quick Cast on), else nothing."""

    def __init__(self, start=None, bindings=GAPS, keys_reach: bool = True) -> None:
        super().__init__(start or world(slots=SLOTS, player=player(consume=False, hex_purge=False)), bindings)
        self.keys_reach = keys_reach
        self.next_unit = 500
        self.keyed: list[tuple[str, int]] = []  # (key, skill of its record) per keyboard skill key
        self.game.keys.on_event = self.key
        self.effects[SUMMON_DEFILER] = self.summon
        self.effects[CONSUME] = self.consume
        self.effects[HEX_PURGE] = lambda: self.set_player(hex_purge=True)
        self.effects[ENGORGE] = lambda: None

    def set_player(self, **changes) -> None:
        w = self.game.world
        self.game.world = replace(w, player=replace(character_of(w), **changes))

    def summon(self) -> None:
        w, p = self.game.world, self.game.character
        defiler = Monster(self.next_unit, DEFILER_CLASS, 1, p.x + 2.0, p.y + 0.5, p.unit_id, ally=True)
        self.next_unit += 1
        self.game.world = replace(w, monsters=(*w.monsters, defiler))
        self.target = (MONSTER_UNIT, defiler.unit_id)

    def consume(self) -> None:
        w, held = self.game.world, self.target
        self.game.world = replace(w, monsters=tuple(m for m in w.monsters if (MONSTER_UNIT, m.unit_id) != held))
        self.set_player(consume=True)
        self.target = None

    def key(self, event) -> None:
        if event[0] != 'key' or event[1] not in KEY_SLOTS:
            return
        record = KEY_SLOTS[event[1]]
        skill = self.bindings[record]
        self.keyed.append((event[1], skill))
        if self.keys_reach and skill != -1:
            self.casts.append((skill, self.pad.left))
            effect = self.effects.get(skill)
            if effect is not None:
                effect()

    def run(self) -> Run:
        run = super().run()
        bound = records(self.bindings)
        run.keys.update(pad_of(run).keys([s for s in (SUMMON_DEFILER, CONSUME, PSYCHIC_WARD) if s in bound], key_file))
        return run


def demon(unit: int, x: float, y: float) -> Monster:
    return Monster(unit, BOUND_DEMON, 1, x, y, 1, ally=True)


# Summon Defiler on B: Consume's upkeep and its re-summon.


def test_with_summon_defiler_on_b_consume_is_due_in_controller_mode_and_not_without_it():
    for bindings, due in ((GAPS, True), (BINDINGS, False)):
        play = Gaps(bindings=bindings)
        run = play.run()
        seen = run.world()
        assert (SUMMON_DEFILER in seen.slots) is due
        assert consume_due(Buffs(run.build).facts(run, seen)) is due


def test_the_consume_upkeep_summons_consumes_the_defiler_and_summons_another_by_the_pad(caplog):
    play = Gaps()
    run = play.run()
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        renew_consume(run)
    assert play.pad.presses() == [('b',), ('lt', 'rt'), ('b',)]  # summon, Consume at the Defiler, summon again
    assert [skill for skill, _stick in play.casts] == [SUMMON_DEFILER, CONSUME, SUMMON_DEFILER]
    assert character_of(run.world()).consume
    assert [m.unit_id for m in run.world().monsters] == [501]  # the second Defiler stays out
    assert 'Pad consume: Summon Defiler toward' in caplog.text
    assert 'the Defiler (unit 500) landed at (+2.0, +0.5) from the character' in caplog.text
    assert 'consumed unit 500 (class 744, the Defiler); the state shown after' in caplog.text
    assert play.game.pressed() == []  # no keyboard skill key


def test_consume_is_not_pressed_when_the_clients_target_turns_to_the_bound_demon(caplog):
    play = Gaps()
    w = play.game.world
    defiler = Monster(500, DEFILER_CLASS, 1, 5002.0, 5000.5, 1, ally=True)
    pit_lord = demon(600, 4970.0, 5030.0)  # far off the Defiler: not in its way for the mouse mode's check
    play.game.world = replace(w, monsters=(defiler, pit_lord))
    run = play.run()
    held = iter([(MONSTER_UNIT, 500)])
    pad_of(run).controller = lambda: replace(play.state(), target=next(held, (MONSTER_UNIT, 600)))
    with caplog.at_level(logging.INFO, 'inventory_tracking'), pytest.raises(Abort):
        consume_defiler(run, defiler)
    assert ('lt', 'rt') not in play.pad.presses()  # the bound demon is never consumed
    assert {m.unit_id for m in run.world().monsters} == {500, 600}
    assert 'the client holds (1, 600) at the press: not cast' in caplog.text


def test_the_prebuff_runs_by_the_pad_with_every_skill_on_a_record():
    play = Gaps()
    run = play.run()
    pad_of(run).route.enabled = False  # the probe aside: the prebuff's own presses
    prebuff(run)
    assert play.pad.presses() == [('b',), ('lt', 'rt'), ('b',), ('lt', 'b'), ('lt', 'a')]
    assert play.game.pressed() == []


def test_the_prebuff_is_refused_naming_the_skill_on_no_record_and_a_new_game_needs_mouse_mode():
    run = Gaps(bindings=BINDINGS).run()
    with pytest.raises(Abort, match=r'Summon Defiler is on no pad record.*mouse mode casts it: click once'):
        pad_of(run).keys((SUMMON_DEFILER,), key_file)
    play = Gaps()
    play.game.world = replace(play.game.world, in_game=False, player=None)
    run = play.run()
    with pytest.raises(Abort, match='a new game needs mouse mode'):
        run_macro(run, lambda world, skills=None: {})
    assert play.pad.presses() == []


# Records 12-15 by keyboard key: the probe and the route.


def test_records_12_to_15_count_only_with_the_key_route_open():
    assert ENGORGE not in records(GAPS)
    assert records(GAPS, by_key=True)[ENGORGE] == 13
    assert ENGORGE not in pad_slots(GAPS, ())
    assert {BIND_DEMON, ENGORGE} <= set(pad_slots(GAPS, (), by_key=True))
    run = Gaps().run()
    with pytest.raises(Abort, match='Engorge is on record 13, reached by a key only, and no `Pad key:` probe'):
        pad_of(run).keys((ENGORGE,), key_file)


def test_the_probe_casts_hex_purge_by_its_slots_key_and_opens_the_route_for_the_session(caplog):
    play = Gaps()
    run = play.run()
    buffs = Buffs(run.build)
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert buffs.by_key(run, HEX_PURGE)
    assert play.keyed == [('w', HEX_PURGE)]  # keyboard slot 8: record 8
    assert play.pad.presses() == []  # not LT+B
    assert pad_of(run).route.ok is True
    assert 'Pad key: w (keyboard slot 8) in controller mode -> record 8 Hex: Purge: shown after' in caplog.text
    assert 'records 12-15 are cast by their keys in this session' in caplog.text
    # Once a game: the next cast of it is the record's button again.
    play.set_player(hex_purge=False)
    assert not buffs.by_key(run, HEX_PURGE)
    # The route open: Engorge (record 13) can be cast, by its slot's key `7`, never with LT held.
    assert ENGORGE in run.world().slots
    assert pad_of(run).keys((ENGORGE,), key_file) == {ENGORGE: 'key 7 (record 13)'}
    run.keys.update(pad_of(run).keys((ENGORGE,), key_file))
    pad_of(run).actuator.press('lt')  # LT left held by some act: a key would cast six records further on
    press_skill(run, ENGORGE)
    assert play.keyed[-1] == ('7', ENGORGE)
    assert 'lt' not in play.pad.down


def test_a_probe_that_shows_nothing_presses_the_record_and_keeps_the_route_shut(caplog):
    play = Gaps(keys_reach=False)
    run = play.run()
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert Buffs(run.build).by_key(run, HEX_PURGE)
    assert play.keyed == [('w', HEX_PURGE)]
    assert play.pad.presses() == [('lt', 'b')]  # the buff is cast all the same
    assert pad_of(run).route.ok is False
    assert 'not shown in 1.5s' in caplog.text
    assert 'pressing LT+B; records 12-15 stay unused' in caplog.text
    assert ENGORGE not in run.world().slots


def test_the_probe_waits_for_a_quiet_moment_and_the_state_off_and_needs_a_pressable_key(caplog):
    start = world(slots=SLOTS, player=player(consume=False, hex_purge=False))
    foe = Monster(77, 5, 1, 5010.0, 5000.0, 0xFFFFFFFF, life=10, max_life=10)
    play = Gaps(start=replace(start, monsters=(foe,)))
    run = play.run()
    shown = lambda: purge_shown(run.world())  # ruff: ignore[lambda-assignment]
    assert not pad_of(run).probe_key(HEX_PURGE, shown)  # a hostile 10 units off
    play.game.world = replace(play.game.world, monsters=())
    play.set_player(hex_purge=True)
    assert not pad_of(run).probe_key(HEX_PURGE, shown)  # on already: its appearing would say nothing
    assert play.keyed == []
    assert pad_of(run).route.probed == set()  # neither counts as this game's probe
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert not pad_of(run).probe_key(PSYCHIC_WARD, lambda: False)  # record 6: keyboard slot 6 is mouse 5
        assert not pad_of(run).probe_key(PSYCHIC_WARD, lambda: False)
    assert caplog.text.count('keyboard slot 6 has no key the macro can press') == 1
    play.set_player(hex_purge=False)
    pad_of(run).route.enabled = False  # config controller_key_route off
    assert not pad_of(run).probe_key(HEX_PURGE, shown)
    assert play.keyed == []


def test_the_route_is_the_sessions_and_a_later_failed_probe_shuts_it(caplog):
    route = KeyRoute()
    play = Gaps()
    run = play.run()
    pad_of(run).route = route
    assert pad_of(run).probe_key(HEX_PURGE, lambda: purge_shown(run.world()))
    assert route.open
    play2 = Gaps(start=world(slots=SLOTS, game_name='cyber33', player=player(hex_purge=False)), keys_reach=False)
    run2 = play2.run()
    pad_of(run2).route = route  # the next game of the same session
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        assert pad_of(run2).probe_key(HEX_PURGE, lambda: purge_shown(run2.world()))
    assert not route.open
    assert 'records 12-15 are no longer used in this session' in caplog.text
    assert route.probed == {'cyber32', 'cyber33'}


def test_engorge_by_its_key_on_the_corpse_the_clients_target_names_logs_the_target(caplog):
    play = Gaps()
    run = play.run()
    pad_of(run).route.ok = True
    run.corpses = lambda: ((900, 5005.0, 5000.0),)
    play.target = (MONSTER_UNIT, 900)
    row = next(row for row in BUFFS if row.skill == ENGORGE)
    buffs = Buffs(run.build)
    cast = Casting(run, row, buffs, run.world(), None, ASPECT, lambda w, skills: pad_of(run).keys(skills, key_file))
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        tried = engorge(cast)
    assert tried.cast
    assert play.keyed == [('7', ENGORGE)]
    assert play.pad.presses() == []
    assert 'Pad target: Engorge on the corpse 900 at (5005.0, 5000.0), 5.0 away, by key 7 (record 13)' in caplog.text
    assert "pressed with the client's target on it" in caplog.text


def test_keyboard_mode_casts_engorge_by_its_keyboard_slot_as_before():
    from tests.inventory_tracking.macros.fakes import Game

    game = Game(world(slots=SLOTS))
    run = game.run()
    press_skill(run, ENGORGE)
    assert game.pressed() == ['e']
    assert run.pad is None


def test_the_consume_renewal_is_held_off_in_controller_mode(caplog):
    """22:09:10-15 on 2026-10-14 (rca/2026-10-14/run-1904-findings.md §3.6): four Defilers summoned by the pad landed
    2.4-3.4 units from the character, whatever the heading asked (the controller's distance 2), each beside the bound
    demon, and no Consume was cast. The pad's stick lead turns a heading, not that distance: attack mode's renewal
    waits for keyboard mode, said, and presses nothing."""
    play = Gaps()
    run = play.run()
    buffs = Buffs(run.build)
    row = next(row for row in BUFFS if row.caster == 'consume')
    seen = run.world()
    with caplog.at_level(logging.INFO, 'inventory_tracking'):
        due = buffs.due(run, row, buffs.facts(run, seen))
        assert due is not None
        tried = buffs.cast(run, due, lambda world, skills: pad_of(run).keys(skills, key_file))
    assert not tried.cast
    assert play.pad.presses() == []
    assert 'Macro: Consume: not renewed by the pad (its Defiler lands at the feet, by the bound demon)' in caplog.text
