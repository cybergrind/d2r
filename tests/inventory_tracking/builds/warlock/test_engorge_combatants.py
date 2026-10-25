"""Engorge for the demons it heals only (builds/warlock/pets.py PET_DEMONS_ONLY, casters.py ENGORGE_FOE_CORPSES,
2026-10-24; rca/2026-10-24/engorge-findings.md). Live 23:32:40-23:37:30 (session 20261024T200458Z-2054f483, take
20261024T203210Z-110, Bloody Foothills): the Act 5 Combatants (monstats 522, the player's alignment, no owner) were
watched as "bound Act 5 Combatant" pets; 30 "Engorge now" for them, "brought no heal" up to 29 in a row, the fight
pulled off them, while the Urdar and the Defiler stood at 126-128/128 with Engorge's state up. Engorge (skills.txt 379,
pettype demon) heals neither them nor takes their corpses: the 4 keys on one showed no engorge missile."""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import buffs as plan, casters, pets
from inventory_tracking.builds.warlock.buffs import BUFFS, engorge_first
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import ENGORGE
from inventory_tracking.game.layout import MINION_FLAG
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts
from inventory_tracking.native.layout import DEAD_MODES
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world


# The take's units (units.jsonl: txt, ally; life in 128ths as the frames read it at 23:35:22.2)
URDAR = Monster(1611177346, 189, 1, 4826.0, 5120.0, ally=True, life=127, max_life=230)  # the bound demon
DEFILER = Monster(1914112823, 744, 1, 4822.0, 5122.0, ally=True, life=128, max_life=230)
COMBATANTS = (
    Monster(618439270, 522, 1, 4836.0, 5124.0, ally=True, life=52, max_life=128),
    Monster(592646217, 522, 1, 4838.0, 5121.0, ally=True, life=9, max_life=128),
    Monster(2106028, 523, 1, 4840.0, 5126.0, ally=True, life=111, max_life=128),
)
# A Death Mauler of the tier 5 Herald's pack (monstats 529)
MAULER = Monster(2920393610, 529, 1, 4846.0, 5126.0, flags=MINION_FLAG, life=128, max_life=128, tier=5)
FIRST = next(row for row in BUFFS if row.skill == ENGORGE and row.due is engorge_first)


def words(*states: int) -> bytes:
    """State words (32 states to a little-endian word) with `states` set."""
    found = bytearray(32)
    for state in states:
        word, bit = divmod(state, 32)
        value = int.from_bytes(found[word * 4 : word * 4 + 4], 'little') | 1 << bit
        found[word * 4 : word * 4 + 4] = value.to_bytes(4, 'little')
    return bytes(found)


BUFFED, BARE = words(pets.ENGORGE_STATE), words()
# The take's state words: the Urdar and the Defiler with Engorge's state all along, the Combatants never
STATES = {URDAR.unit_id: BUFFED, DEFILER.unit_id: BUFFED} | {m.unit_id: BARE for m in COMBATANTS}


def reader(monster: Monster) -> bytes | None:
    return STATES.get(monster.unit_id)


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setattr(pets, 'PET_DEMONS_ONLY', True)
    monkeypatch.setattr(pets, 'ENGORGE_LEARNS', True)


@pytest.fixture
def off(monkeypatch):
    monkeypatch.setattr(pets, 'PET_DEMONS_ONLY', False)
    monkeypatch.setattr(pets, 'ENGORGE_LEARNS', True)


def look(*monsters):
    return replace(world(area=110, slots=HUNT_SLOTS), monsters=monsters)


SCENE = look(URDAR, DEFILER, *COMBATANTS, MAULER)


def test_engorge_heals_the_summons_and_demons_not_the_combatants():
    assert pets.heals(URDAR)
    assert pets.heals(DEFILER)
    assert not any(pets.heals(m) for m in COMBATANTS)


def test_on_the_combatants_are_no_pets_and_the_buff_reads_up(on):
    assert [m.unit_id for m in pets.pets(SCENE)] == [URDAR.unit_id, DEFILER.unit_id]
    assert pets.buffed(SCENE, reader) is True
    assert pets.bare(SCENE, reader) == frozenset()


def test_off_the_combatants_are_pets_as_before(off):
    assert {m.unit_id for m in pets.pets(SCENE)} == {URDAR.unit_id, DEFILER.unit_id} | {m.unit_id for m in COMBATANTS}
    assert pets.buffed(SCENE, reader) is False  # the Combatants never show the state


def keys_over(seconds: float = 20.0) -> tuple[list[float], pets.PetWatch]:
    """The first fight row over `seconds` of looks every 0.2 s of the take's scene, no heal ever showing: the clocks
    Engorge was due at, each a key told to the watch on a fresh corpse; the watch."""
    cast_at: dict[tuple[int, int | None], float] = {}
    keys: list[float] = []
    for i in range(int(seconds / 0.2)):
        now = round(100.0 + i * 0.2, 2)
        facts = BuffFacts(SCENE, now, foes=(MAULER,), cast_at=cast_at, corpses=lambda: (), states=reader)
        if engorge_first(facts):
            keys.append(now)
            cast_at[ENGORGE, None] = now
            pets.watch_of(cast_at).keyed(now, 7000 + i, pets.bare(SCENE, reader))
    return keys, pets.watch_of(cast_at)


def test_on_no_engorge_and_no_pull_for_the_combatants(on, caplog):
    caplog.set_level(logging.INFO)
    keys, watch = keys_over()
    assert keys == []  # the pets are full with the buff up: neither a danger nor the pack's buff is due
    assert watch.unhealed == 0
    assert watch.refused == set()
    assert pets.pull_wanted(watch, 120.0) is None
    assert 'Combatant' not in caplog.text


def test_off_the_combatants_draw_the_keys_the_no_heals_and_the_pull(off, caplog):
    caplog.set_level(logging.INFO)
    keys, watch = keys_over()
    assert len(keys) >= 10  # the 0.6 s, then 2 s danger cadence (buffs.py PET_UNHEALED)
    assert watch.unhealed >= plan.PET_UNHEALED
    assert len(watch.refused) >= 10  # a fresh corpse refused at every key
    assert 'bound Act 5 Combatant' in caplog.text
    assert 'brought no heal' in caplog.text


def cast_on(corpses):
    """The first fight row for a hurt Defiler cast in a fake game with a dead Combatant among the look's units, the
    hover record naming nothing; (tried, the keys pressed, the corpse keyed)."""
    lying = replace(COMBATANTS[0], mode=next(iter(DEAD_MODES)), life=0)
    play = Game(world(area=110, slots=HUNT_SLOTS))
    play.world = replace(play.world, monsters=(URDAR, replace(DEFILER, life=40), lying, MAULER))
    buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
    buffs.let_go = lambda: None
    run.corpses = lambda: corpses
    run.hovered = lambda: None
    play.clock.now = 50.0
    due = buffs.due(run, FIRST, buffs.facts(run, play.world, (MAULER,)))
    assert due is not None
    tried = buffs.cast(run, due, lambda w, skills: dict(KEYS), 1.8)
    trial = pets.watch_of(buffs.cast_at).trial
    return tried, play.pressed(), trial.corpse if trial is not None else None


# The Combatant's corpse nearest the character (5000, 5000 in the fake game), a Death Mauler's further
CORPSES = ((COMBATANTS[0].unit_id, 5004.0, 5002.0), (MAULER.unit_id + 1, 5009.0, 4996.0))


def test_on_the_key_goes_on_a_foes_corpse_not_the_combatants(on, monkeypatch):
    monkeypatch.setattr(casters, 'ENGORGE_FOE_CORPSES', True)
    tried, pressed, corpse = cast_on(CORPSES)
    assert tried.cast
    assert pressed == ['e']
    assert corpse == CORPSES[1][0]


def test_on_with_only_the_combatants_corpse_nothing_is_touched(on, monkeypatch):
    monkeypatch.setattr(casters, 'ENGORGE_FOE_CORPSES', True)
    tried, pressed, _ = cast_on(CORPSES[:1])
    assert not tried.cast
    assert not tried.touched
    assert pressed == []


def test_off_the_combatants_corpse_is_keyed_first_as_before(on, monkeypatch):
    monkeypatch.setattr(casters, 'ENGORGE_FOE_CORPSES', False)
    tried, pressed, corpse = cast_on(CORPSES)
    assert tried.cast
    assert pressed == ['e']
    assert corpse == CORPSES[0][0]
