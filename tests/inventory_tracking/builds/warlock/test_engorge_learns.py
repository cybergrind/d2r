"""Engorge learns from what its key did (builds/warlock/pets.py ENGORGE_LEARNS, 2026-10-23;
rca/2026-10-23/unraveler-findings.md): a corpse whose key showed nothing is not tried again, and the buff for its own
sake waits while every pet shows Engorge's state. Live 15:07:41-15:09:46 (take 20261023T120656Z-66): 27 keys, 20 on
the corpse 3426990368, the pets 128/128 with the state up."""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import buffs as plan, pets
from inventory_tracking.builds.warlock.buffs import BUFFS, ENGORGE_PACK_SECONDS, engorge_first
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import ENGORGE
from inventory_tracking.game.layout import MINION_FLAG, MONSTER_UNIT, OBJECT_UNIT
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world


PIT_LORD = Monster(3973222171, 361, 1, 5004.0, 5000.0, ally=True, life=128, max_life=230)  # the take's bound demon
DEFILER = Monster(497324665, 744, 1, 4996.0, 5000.0, ally=True, life=128, max_life=230)
# A Burning Dead of the tier 5 Unraveler Herald's pack (skeleton4 as the take's units read it: txt 3)
DEAD = Monster(3960048707, 3, 1, 5014.0, 5000.0, flags=MINION_FLAG, life=128, max_life=128, tier=5)
CORPSES = ((3426990368, 5008.0, 5006.0), (3960048707, 5009.0, 4990.0))
PACK_ROW = next(row for row in BUFFS if row.skill == ENGORGE and row.due is engorge_first)


def words(*states: int) -> bytes:
    """State words (32 states to a little-endian word) with `states` set."""
    found = bytearray(32)
    for state in states:
        word, bit = divmod(state, 32)
        value = int.from_bytes(found[word * 4 : word * 4 + 4], 'little') | 1 << bit
        found[word * 4 : word * 4 + 4] = value.to_bytes(4, 'little')
    return bytes(found)


BUFFED, BARE = words(pets.ENGORGE_STATE), words()


@pytest.fixture
def learns(monkeypatch):
    monkeypatch.setattr(pets, 'ENGORGE_LEARNS', True)


@pytest.fixture
def unlearned(monkeypatch):
    monkeypatch.setattr(pets, 'ENGORGE_LEARNS', False)


def look(*monsters):
    return replace(world(area=66, slots=HUNT_SLOTS), monsters=monsters)


def reader(state: dict[int, bytes]):
    return lambda monster: state.get(monster.unit_id)


def test_the_state_words_say_the_buff_on_every_pet_and_unread_says_nothing():
    seen = look(PIT_LORD, DEFILER)
    assert pets.buffed(seen, reader({PIT_LORD.unit_id: BUFFED, DEFILER.unit_id: BUFFED})) is True
    assert pets.buffed(seen, reader({PIT_LORD.unit_id: BUFFED, DEFILER.unit_id: BARE})) is False
    assert pets.buffed(seen, reader({PIT_LORD.unit_id: BUFFED})) is None  # the Defiler unread
    assert pets.buffed(seen, None) is None
    assert pets.buffed(look(DEAD), reader({})) is None  # no pet
    assert pets.bare(seen, reader({PIT_LORD.unit_id: BUFFED, DEFILER.unit_id: BARE})) == {DEFILER.unit_id}


def judged(life_after: int, *, before: int = 105, state: dict[int, bytes] | None = None, without=frozenset()):
    """A key on the take's corpse with the Pit Lord at `before`, the looks after it at `life_after`; the watch."""
    watch = pets.PetWatch()
    states = reader(state or {})
    watch.look(look(replace(PIT_LORD, life=before), DEFILER), 10.0, plan.ENGORGE_BELOW, states)
    watch.keyed(10.1, CORPSES[0][0], without)
    for now in (10.4, 10.7, 11.0):
        watch.look(look(replace(PIT_LORD, life=life_after), DEFILER), now, plan.ENGORGE_BELOW, states)
    return watch


def test_a_corpse_whose_key_brought_no_heal_is_refused_and_said(learns, caplog):
    caplog.set_level(logging.INFO)
    watch = judged(106)  # 15:08:50: "brought no heal (bound Pit Lord 105/128 -> 106/128)"
    assert watch.refused == {CORPSES[0][0]}
    assert 'the Engorge on the corpse 3426990368 0.9s ago showed nothing (no heal): not tried again' in caplog.text


def test_a_heal_keeps_the_corpse(learns):
    assert judged(128).refused == set()


def test_full_pets_judged_by_the_state_that_did_not_come_on(learns):
    off = {PIT_LORD.unit_id: BARE, DEFILER.unit_id: BARE}
    # 15:08:55-15:09:24: the state off on both pets, six keys on the corpse, still off
    stayed = judged(128, before=128, state=off, without=frozenset(off))
    assert stayed.refused == {CORPSES[0][0]}
    came = judged(128, before=128, state={PIT_LORD.unit_id: BUFFED, DEFILER.unit_id: BUFFED}, without=frozenset(off))
    assert came.refused == set()  # 15:09:37: the corpse 3960048707, the state on 0.66 s after


def test_nothing_that_could_show_is_no_verdict(learns):
    # full pets with the state up already: the key cannot be judged
    assert judged(128, before=128, state={PIT_LORD.unit_id: BUFFED, DEFILER.unit_id: BUFFED}).refused == set()


def test_off_the_corpse_is_never_refused(unlearned):
    assert judged(106).refused == set()


def pack_facts(now, cast_at, states):
    foes = tuple(replace(DEAD, unit_id=DEAD.unit_id + i, x=DEAD.x + i % 4, y=DEAD.y + i // 4) for i in range(15))
    seen = look(PIT_LORD, DEFILER, *foes)
    return BuffFacts(seen, now, foes=foes, cast_at=cast_at, corpses=lambda: CORPSES, states=states)


def pack_keys(states, seconds=60.0):
    """The pack's Engorge over `seconds` of looks every 0.2 s with full pets: the clocks it was due at."""
    cast_at: dict[tuple[int, int | None], float] = {}
    keys = []
    for i in range(int(seconds / 0.2)):
        now = round(100.0 + i * 0.2, 2)
        if engorge_first(pack_facts(now, cast_at, states)):
            keys.append(now)
            cast_at[ENGORGE, None] = now
    return keys


def test_the_packs_engorge_waits_while_every_pet_shows_the_buff(learns):
    up = reader({PIT_LORD.unit_id: BUFFED, DEFILER.unit_id: BUFFED})
    assert pack_keys(up) == []
    one_bare = reader({PIT_LORD.unit_id: BUFFED, DEFILER.unit_id: BARE})
    assert len(pack_keys(one_bare)) == len(pack_keys(None))  # a pet without it: the pack's cadence as before
    assert len(pack_keys(None)) == pytest.approx(60.0 / ENGORGE_PACK_SECONDS, abs=1)  # unread: as before


def test_off_the_pack_cadence_goes_on_with_the_buff_up(unlearned):
    up = reader({PIT_LORD.unit_id: BUFFED, DEFILER.unit_id: BUFFED})
    assert len(pack_keys(up)) == pytest.approx(60.0 / ENGORGE_PACK_SECONDS, abs=1)  # the incident's 5.3 s keys


def test_the_lazy_buff_waits_while_every_pet_shows_it_and_a_hurt_one_still_gets_it(learns):
    cast_at: dict[tuple[int, int | None], float] = {(ENGORGE, None): 0.0}
    up = reader({PIT_LORD.unit_id: BUFFED, DEFILER.unit_id: BUFFED})
    facts = BuffFacts(look(PIT_LORD, DEFILER), 30.0, cast_at=cast_at, corpses=lambda: CORPSES, states=up)
    assert not plan.engorge_due(facts)
    hurt = replace(facts, world=look(replace(PIT_LORD, life=60), DEFILER))
    assert plan.engorge_due(hurt)


def cast_pack(corpses, *, refused=frozenset(), states=None, over=None):
    """The pack row asked and cast in a fake game, the hover record naming `over`; (tried, the keys pressed, the
    watch)."""
    play = Game(world(area=66, slots=HUNT_SLOTS))
    play.world = replace(play.world, monsters=(PIT_LORD, DEFILER, DEAD))
    buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
    buffs.let_go = lambda: None
    run.corpses = lambda: corpses
    run.hovered = lambda: over
    run.unit_states = states
    play.clock.now = 50.0
    watch = pets.watch_of(buffs.cast_at)
    watch.refused |= set(refused)
    due = buffs.due(run, PACK_ROW, buffs.facts(run, play.world, (DEAD,)))
    assert due is not None
    return buffs.cast(run, due, lambda w, skills: dict(KEYS), 1.8), play.pressed(), watch


def test_a_refused_corpse_is_not_tried_and_the_next_one_is(learns):
    tried, pressed, watch = cast_pack(CORPSES, refused={CORPSES[0][0]}, states=reader({}))
    assert tried.cast
    assert pressed == ['e']
    assert watch.trial is None or watch.trial.corpse == CORPSES[1][0]


def test_with_every_corpse_refused_nothing_is_touched(learns, caplog):
    caplog.set_level(logging.INFO)
    tried, pressed, _ = cast_pack(CORPSES[:1], refused={CORPSES[0][0]})
    assert not tried.cast
    assert not tried.touched
    assert pressed == []
    assert 'no Engorge: each of the 1 corpses in reach showed nothing before' in caplog.text


def test_off_a_refused_corpse_is_tried_as_before(unlearned):
    tried, pressed, _ = cast_pack(CORPSES[:1], refused={CORPSES[0][0]})
    assert tried.cast
    assert pressed == ['e']


def test_a_corpse_under_an_object_is_refused_for_good_and_one_under_a_monster_is_not(learns):
    # 16:09:12-16:10:28 (take 20261023T130907Z-67): 50 tries on three corpses under objects (type 2)
    tried, pressed, watch = cast_pack(CORPSES, over=(OBJECT_UNIT, 2707226882))
    assert not tried.cast
    assert pressed == []
    assert watch.refused == {unit for unit, _, _ in CORPSES}
    _, _, watch = cast_pack(CORPSES, over=(MONSTER_UNIT, DEAD.unit_id))
    assert watch.refused == set()  # a live monster walks off the corpse


def test_off_a_corpse_under_an_object_is_tried_again(unlearned):
    _, _, watch = cast_pack(CORPSES, over=(OBJECT_UNIT, 2707226882))
    assert watch.refused == set()
