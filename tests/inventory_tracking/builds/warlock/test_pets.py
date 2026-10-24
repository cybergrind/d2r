"""The pets watched and Engorged by their life (builds/warlock/pets.py, buffs.py `engorge_first`, casters.py `engorge`;
rca/2026-10-21/demon-lost-findings.md). The bound Urdar of the take 20261021T124057Z-22 went 128 -> 0 in 12 s against
a tier 5 Dark Archer Herald pack with one Engorge landed. Each item's switch off gives the old behaviour."""

import logging
from dataclasses import replace

import pytest

from inventory_tracking.builds.warlock import bind as binding, buffs as plan, casters, pets
from inventory_tracking.builds.warlock.buffs import (
    BUFFS,
    ENGORGE_DANGER_SECONDS,
    ENGORGE_HURT_SECONDS,
    ENGORGE_PACK_SECONDS,
    ENGORGE_UNHEALED_SECONDS,
    PET_UNHEALED,
    Rotation,
    danger_every,
    demon_hurt,
    engorge_first,
    engorged,
    heavy,
    pack_danger,
)
from inventory_tracking.builds.warlock.casters import ENGORGE_DANGER_RETRY, covers
from inventory_tracking.builds.warlock.echoing_strike.build import ECHOING_STRIKE_BUILD
from inventory_tracking.builds.warlock.skills import BIND_DEMON, ENGORGE
from inventory_tracking.game.layout import ITEM_UNIT, MINION_FLAG, MONSTER_UNIT, OBJECT_UNIT
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts, Casting, Tried
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, KEYS, Game, world


URDAR = Monster(2147553209, 189, 1, 5004.0, 5000.0, ally=True, life=128, max_life=230)  # the bound demon
DEFILER = Monster(1387530185, 744, 1, 4996.0, 5000.0, 1, ally=True, life=128, max_life=230)
# A Dark Archer of the tier 5 pack: cr_archer3, its Herald's minion (stat 367 tier 5)
ARCHER = Monster(4286120149, 162, 1, 5012.0, 5000.0, flags=MINION_FLAG, life=128, max_life=128, tier=5)
CORPSES = tuple((900 + i, 5006.0 + i, 5004.0) for i in range(5))
FIRST = next(row for row in BUFFS if row.skill == ENGORGE and row.due is engorge_first)
# The Urdar's life in the take every 0.2 s from t = 29.8 (15:41:27.1): the pack on it from 30.2, the one heal at 32.8,
# 128 -> 34 in 4 s, the cast at 39.6 that hit an object and healed nothing, dead at 42.8.
TAKE = (
    128, 128, 128, 112, 108, 105, 105, 106, 106, 106, 108, 108, 108, 103, 100, 128, 118, 110, 110, 104, 95, 84, 73, 73,
    73, 75, 75, 72, 65, 57, 52, 48, 44, 44, 44, 44, 37, 37, 37, 34, 34, 34, 35, 35, 35, 37, 37, 38, 38, 34, 34, 34, 35,
    35, 33, 33, 30, 30, 31, 16, 9, 6, 6, 6, 1, 0, 0,
)  # fmt: skip
START, STEP = 29.8, 0.2


def look(*monsters, slots=HUNT_SLOTS):
    return replace(world(area=22, slots=slots), monsters=monsters)


def facts(seen, now, cast_at, foes=()):
    return BuffFacts(seen, now, foes=foes, cast_at=cast_at, corpses=lambda: CORPSES)


def replay(due, *, keyed=True):
    """The take's Urdar replayed look by look (no heal follows a cast: the life is as it was); the clocks `due` held
    at, each taken as a cast (and told to the watch, `keyed`)."""
    cast_at: dict[tuple[int, int | None], float] = {}
    casts = []
    for i, life in enumerate(TAKE):
        now = round(START + i * STEP, 2)
        if due(facts(look(replace(URDAR, life=life)), now, cast_at)):
            casts.append(now)
            cast_at[ENGORGE, None] = now
            if keyed:
                pets.watch_of(cast_at).keyed(now)
    return casts


# --- Item 1: Engorge on the pet's life and its fall (buffs.py PET_ENGORGE) ---


def test_the_urdars_fall_has_engorge_due_at_once_and_while_it_falls(caplog):
    caplog.set_level(logging.INFO)
    casts = replay(engorge_first)
    assert casts[0] == 30.4  # 128 -> 112 in 0.2 s: the pack's first arrows, the life still over 70%
    assert 'Macro: pet: bound Urdar 112/128, -16 in 0.2s: Engorge now' in caplog.text
    # 128 -> 34, then the tries that brought nothing (none heals in a replay: after PET_UNHEALED the slower cadence)
    falling = [at for at in casts if 33.0 <= at <= 39.8]
    assert falling == [33.2, 34.0, 34.6, 36.8, 39.0]
    # the old rule: the buff, then hurt under 70%, every ENGORGE_HURT_SECONDS
    old = replay(lambda f: plan.engorge_due(f), keyed=False)
    assert old == [29.8, 34.0, 38.2, 42.4]  # the buff at the first look, then hurt (84/128 at 34.0): 2 in the fall


def test_engorges_that_bring_no_heal_slow_to_unhealed_seconds_and_say_so(caplog):
    caplog.set_level(logging.INFO)
    cast_at: dict[tuple[int, int | None], float] = {}
    watch = pets.watch_of(cast_at)
    for i, life in enumerate(TAKE[:40]):  # the take's 37 -> 34 after the cast at 39.6: no heal
        watch.look(look(replace(URDAR, life=life)), round(START + i * STEP, 2), plan.ENGORGE_BELOW)
        if i in (30, 34, 38):
            watch.keyed(round(START + i * STEP, 2))
    assert watch.unhealed == 2
    assert 'Macro: pet: the Engorge 0.8s ago brought no heal (bound Urdar 44/128 -> 37/128): 2 in a row' in caplog.text
    watch.unhealed = PET_UNHEALED
    assert danger_every(watch) == ENGORGE_UNHEALED_SECONDS
    watch.unhealed = 0
    assert danger_every(watch) == ENGORGE_DANGER_SECONDS


def test_the_one_heal_of_the_take_is_judged_a_heal():
    cast_at: dict[tuple[int, int | None], float] = {}
    watch = pets.watch_of(cast_at)
    for i, life in enumerate(TAKE[:20]):  # 100 -> 128 at 32.8, the key at 32.6
        now = round(START + i * STEP, 2)
        watch.look(look(replace(URDAR, life=life)), now, plan.ENGORGE_BELOW)
        if now == 32.6:
            watch.unhealed = 3
            watch.keyed(now)
    assert watch.unhealed == 0


def test_the_buff_alone_stays_lazy_and_a_full_pet_has_no_first_engorge():
    cast_at: dict[tuple[int, int | None], float] = {(ENGORGE, None): 0.0}
    seen = look(URDAR, DEFILER)
    for now in (1.0, 5.0, 14.0):
        assert not engorge_first(facts(seen, now, cast_at))
    assert not plan.engorge_due(facts(seen, 14.0, cast_at))
    assert plan.engorge_due(facts(seen, 15.1, cast_at))  # ENGORGE_SECONDS, as before


def test_a_dead_pet_is_no_hurt_demon_to_engorge():
    # 15:41:43-50: the Urdar's corpse (0/128) kept Engorge "due for a hurt demon": four tries for nothing
    corpse = replace(URDAR, life=0, max_life=128)
    seen = look(corpse, DEFILER)
    assert engorged(seen) == [DEFILER]
    assert not demon_hurt(seen)


def test_without_pet_engorge_a_hurt_pet_waits_the_hurt_seconds(monkeypatch):
    monkeypatch.setattr(plan, 'PET_ENGORGE', False)
    monkeypatch.setattr(plan, 'ENGORGE_PACK_FIRST', False)
    assert replay(engorge_first) == []
    assert engorged(look(replace(URDAR, life=0, max_life=128))) != []  # the dead counted as before


# --- Item 2: a refused try again at once, with another corpse (casters.py ENGORGE_RETRY_AT_ONCE) ---


class Strike:
    def __init__(self):
        self.released = 0

    def __call__(self):
        self.released += 1


def engorge_in_danger(over, *, pet=None, corpses=CORPSES):
    """The first row asked and cast for a pet in danger with the record naming `over` at every corpse; (tried, the
    records read, releases, buffs, the clock)."""
    play = Game(world(area=22, slots=HUNT_SLOTS))
    play.world = replace(play.world, monsters=(pet or replace(URDAR, life=34), ARCHER))
    buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
    strike = Strike()
    buffs.let_go = strike
    reads = []

    def hovered():
        reads.append(strike.released)
        return over

    run.corpses = lambda: corpses
    run.hovered = hovered
    play.clock.now = 50.0
    due = buffs.due(run, FIRST, buffs.facts(run, play.world))
    assert due is not None
    tried = buffs.cast(run, due, lambda w, skills: dict(KEYS), 1.8)
    return tried, reads, strike.released, buffs, play


def test_for_a_pet_in_danger_the_strike_is_let_go_four_corpses_looked_at_and_the_next_try_soon():
    # 15:41:34.1: two corpses refused ("under the pointer a live monster"), the next look 2.5 s later
    tried, reads, released, buffs, play = engorge_in_danger((MONSTER_UNIT, ARCHER.unit_id))
    assert not tried.cast
    assert len(reads) == casters.ENGORGE_DANGER_LOOKS
    assert reads[0] >= 1  # the strike let go before the first record was read
    assert released >= 1
    assert Rotation(buffs).engorged_at == pytest.approx(play.clock.now - ENGORGE_DANGER_SECONDS + ENGORGE_DANGER_RETRY)


def test_a_corpse_out_of_the_usual_reach_is_used_for_a_pet_in_danger():
    far = ((990, 4976.0, 4997.0),)  # 24.2 units off on the screen: past ENGORGE_REACH 20, within the danger's 30
    tried, _, _, _, play = engorge_in_danger(None, corpses=far)
    assert tried.cast
    assert play.pressed() == ['e']


def test_an_object_under_the_pointer_keeps_engorge_off_the_corpse(monkeypatch):
    # 15:41:36.6: the key went with (2, 2707226882) under the pointer, and the Urdar's life went 37 -> 34
    assert covers((OBJECT_UNIT, 2707226882), set())
    assert covers((ITEM_UNIT, 1), set())
    assert not covers(None, set())
    tried, _, _, _, play = engorge_in_danger((OBJECT_UNIT, 2707226882))
    assert not tried.cast
    assert play.pressed() == []
    monkeypatch.setattr(casters, 'ENGORGE_RETRY_AT_ONCE', False)
    assert not covers((OBJECT_UNIT, 2707226882), set())


def test_without_retry_at_once_two_corpses_and_the_old_retry(monkeypatch):
    monkeypatch.setattr(casters, 'ENGORGE_RETRY_AT_ONCE', False)
    _, reads, released, buffs, play = engorge_in_danger((MONSTER_UNIT, ARCHER.unit_id))
    assert len(reads) == casters.ENGORGE_LOOKS
    assert released == 0
    assert Rotation(buffs).engorged_at == pytest.approx(play.clock.now - ENGORGE_HURT_SECONDS + casters.ENGORGE_RETRY)


# --- Item 3: the pack's danger first (buffs.py ENGORGE_PACK_FIRST) ---


def pack(count, tier=5):
    return tuple(
        replace(ARCHER, unit_id=ARCHER.unit_id + i, x=5010.0 + i % 5, y=4998.0 + i // 5, tier=tier)
        for i in range(count)
    )


def test_a_tier_5_dark_archer_pack_has_engorge_first_at_the_fights_start_and_kept_up(caplog):
    caplog.set_level(logging.INFO)
    foes = pack(15)
    seen = look(URDAR, *foes)
    cast_at: dict[tuple[int, int | None], float] = {}
    assert pack_danger(facts(seen, 10.0, cast_at, foes)) == 'a tier 5 Herald pack (15 Dark Archer)'
    assert engorge_first(facts(seen, 10.0, cast_at, foes))  # the full Urdar: for the buff, first
    assert 'Macro: pet: bound Urdar 128/128 by a tier 5 Herald pack (15 Dark Archer): Engorge first' in caplog.text
    cast_at[ENGORGE, None] = 10.0
    assert not engorge_first(facts(seen, 10.0 + ENGORGE_PACK_SECONDS, cast_at, foes))
    assert engorge_first(facts(seen, 10.1 + ENGORGE_PACK_SECONDS, cast_at, foes))
    assert not engorge_first(facts(look(URDAR), 30.0, cast_at))  # the pack dead: lazy again


def test_dark_archers_rank_as_heavy_hitters_by_the_danger_table():
    # terror/data/threats.json: Dark Archer ranged, 0.9 physical; ten of them, no Herald, within 20 of the pet
    ten = pack(10, tier=0)
    assert heavy(ten) >= plan.PET_HEAVY
    assert heavy(pack(3, tier=0)) < plan.PET_HEAVY
    assert heavy(pack(1)) > heavy(pack(1, tier=0))  # a Herald's minion of tier 5 hits harder
    why = pack_danger(facts(look(URDAR, *ten), 1.0, {}, ten))
    assert why is not None
    assert why.startswith('heavy hitters (10 Dark Archer, threat ')
    far = tuple(replace(m, x=m.x + 40.0) for m in ten)
    assert pack_danger(facts(look(URDAR, *far), 1.0, {}, far)) is None


def test_without_pack_first_a_full_pet_by_the_pack_waits_the_lazy_buff(monkeypatch):
    monkeypatch.setattr(plan, 'ENGORGE_PACK_FIRST', False)
    foes = pack(15)
    assert not engorge_first(facts(look(URDAR, *foes), 10.0, {}, foes))


# --- Item 4: monitoring (pets.py PET_LINES) ---


def test_the_urdars_loss_is_said_once_and_a_consumed_defiler_is_not(caplog):
    caplog.set_level(logging.INFO)
    replay(engorge_first)
    lost = [r.getMessage() for r in caplog.records if 'lost at' in r.getMessage()]
    assert len(lost) == 1
    assert lost[0].startswith('Macro: pet: bound Urdar (2147553209) lost at 0/128, 1/128 before; the last Engorge ')
    caplog.clear()
    cast_at: dict[tuple[int, int | None], float] = {}
    watch = pets.watch_of(cast_at)
    watch.look(look(DEFILER), 1.0, plan.ENGORGE_BELOW)
    watch.look(look(replace(DEFILER, life=0, mode=0)), 1.04, plan.ENGORGE_BELOW)  # 128 -> 0: Consume took it
    assert 'lost at' not in caplog.text
    hurt = replace(DEFILER, unit_id=1077230691, life=6)
    watch.look(look(hurt), 2.0, plan.ENGORGE_BELOW)
    watch.look(look(replace(hurt, life=0)), 2.2, plan.ENGORGE_BELOW)
    assert 'Macro: pet: Defiler (1077230691) lost at 0/128, 6/128 before' in caplog.text


def test_without_the_lines_nothing_is_said(monkeypatch, caplog):
    monkeypatch.setattr(pets, 'PET_LINES', False)
    caplog.set_level(logging.INFO)
    replay(engorge_first)
    assert 'Macro: pet:' not in caplog.text


# --- Item 5: the pull off the bound demon (pets.py PET_PULL; the player, 2026-10-21 ~16:30: "Yes, pull it out") ---


def test_the_pull_comes_only_with_engorge_failing_and_the_demon_low():
    cast_at: dict[tuple[int, int | None], float] = {}
    watch = pets.watch_of(cast_at)
    watch.look(look(replace(URDAR, life=34)), 1.0, plan.ENGORGE_BELOW)
    watch.keyed(1.0)
    assert pets.pull_wanted(watch, 1.0) is None  # an Engorge just keyed
    watch.unhealed = pets.PULL_UNHEALED
    assert pets.pull_wanted(watch, 1.0) == 'bound Urdar at 34/128, 2 Engorges with no heal'
    watch.unhealed = 0
    watch.look(look(replace(URDAR, life=34)), 2.6, plan.ENGORGE_BELOW)
    assert pets.pull_wanted(watch, 2.6) == 'bound Urdar at 34/128, no Engorge for 1.6s'
    watch.look(look(replace(URDAR, life=73)), 2.8, plan.ENGORGE_BELOW)
    assert pets.pull_wanted(watch, 2.8) is None  # 57%: no pull


def test_a_pull_asked_has_the_pack_hop_priced_with_the_pack_on_the_demons(monkeypatch):
    # the fixture herald-t5-held: the pack on the demons, no hop priced (test_herald_pack.py; its Mana Burn members
    # take the burner's hop, `burn_back`); a pull asked for the bound demon's sake makes the same look price the hop
    # back (macros/safety.py `pack_back`, `burn_back`)
    from inventory_tracking.combat import pack as herald_pack
    from tests.inventory_tracking.macros.test_herald_pricing import NOW, priced

    monkeypatch.setattr(herald_pack, 'PULL', herald_pack.Pull())
    _, decision = priced('herald-t5-held')
    assert not [c for c in decision['candidates'] if c['why'].startswith(herald_pack.BACK_SAID)]
    herald_pack.ask_pull('bound Urdar at 34/128, no Engorge for 5.0s', NOW + pets.PULL_HOLD)
    _, decision = priced('herald-t5-held')
    hops = [c for c in decision['candidates'] if c['why'].startswith(herald_pack.BACK_SAID)]
    assert hops
    assert hops[0]['why'] == f'{herald_pack.BACK_SAID}: bound Urdar at 34/128, no Engorge for 5.0s'
    assert herald_pack.pulled(NOW + pets.PULL_HOLD + 0.1) is None  # the ask lapses: asked again at every look


def test_the_first_row_asks_the_pull_for_the_take_s_urdar(monkeypatch, caplog):
    from inventory_tracking.combat import pack as herald_pack

    monkeypatch.setattr(pets, 'PET_PULL', True)
    monkeypatch.setattr(herald_pack, 'PULL', herald_pack.Pull())
    caplog.set_level(logging.INFO)
    cast_at: dict[tuple[int, int | None], float] = {(ENGORGE, None): 32.6}  # the one heal's key, 15:41:29.96
    asked = []
    for i, life in enumerate(TAKE[:50]):
        now = round(START + i * STEP, 2)
        engorge_first(facts(look(replace(URDAR, life=life)), now, cast_at))
        if herald_pack.pulled(now) is not None and not asked:
            asked.append((now, life))
    # under 30% (38.4/128) at 37/128, 15:41:34.3 in the take, its danger 6.6 s old with no Engorge told: asked at once
    assert asked == [(37.0, 37)]
    assert 'the fight pulled off it (the pack hop asked)' in caplog.text


# --- Item 6: Bind Demon on what it can bind; binds that bring none given up (casters.py BIND_GIVE_UP) ---


def test_dark_archers_are_demons_bind_demon_may_take():
    # monstats cr_archer3 (*hcIdx 162) demon 1 (combat/data/tables.json); a Herald's minion, no leader
    assert binding.bindable(ARCHER)
    assert not binding.bindable(replace(ARCHER, txt_id=2))  # Bone Warrior: undead, monstats demon empty
    assert not binding.bindable(replace(ARCHER, life=0, mode=12))


def test_the_macros_never_cast_bind_demon_the_player_binds_it(caplog):
    # the player, 2026-10-21 ~16:30: "I will do bind daemon myself. you don't use bind daemon anywhere for now"
    assert binding.BIND_DEMON_CASTS is False
    foes = pack(15)
    seen = replace(look(*foes), slots=(*HUNT_SLOTS, BIND_DEMON))
    assert not binding.bind_due(BuffFacts(seen, 50.0, foes=foes, reachable=foes))
    play = Game(look(ARCHER))
    run = play.run()
    row = next(row for row in BUFFS if row.skill == BIND_DEMON)
    cast = Casting(run, row, Shared(run), play.world, ARCHER, 1.8, lambda w, skills: dict(KEYS))  # pyrefly: ignore[bad-argument-type]  # a fake executor
    tried = casters.bind(cast)
    assert (tried.cast, tried.touched, play.pressed()) == (False, False, [])
    assert not [row for row in BUFFS if row.skill == BIND_DEMON and row.phase != 'fight']  # no other row casts it


class Shared:
    """An executor whose shared cast always goes."""

    def __init__(self, run):
        self.run = run

    def shared(self, cast):
        return Tried(self.run.clock(), cast=True)


def test_two_binds_that_brought_no_demon_are_followed_by_a_pause(caplog, monkeypatch):
    monkeypatch.setattr(binding, 'BIND_DEMON_CASTS', True)  # as built, before the player's ruling
    # 15:41:41.9, 46.1, 49.8: three Bind Demons on Dark Archers, no demon bound
    caplog.set_level(logging.INFO)
    play = Game(look(ARCHER))
    run = play.run()
    row = next(row for row in BUFFS if row.skill == BIND_DEMON)
    executor = Shared(run)
    cast = Casting(run, row, executor, play.world, ARCHER, 1.8, lambda w, skills: dict(KEYS))  # pyrefly: ignore[bad-argument-type]  # a fake executor
    tried = []
    for at in (41.9, 46.1, 49.8):
        play.clock.now = at
        tried.append(casters.bind(cast))
    assert [t.cast for t in tried] == [True, True, False]
    assert tried[2].at == pytest.approx(49.8 - binding.BIND_RETRY + casters.BIND_PAUSE)
    assert 'Macro: bind: 2 Bind Demon casts in 8s brought no demon: none for 30s' in caplog.text


def test_without_give_up_every_bind_goes(monkeypatch):
    monkeypatch.setattr(binding, 'BIND_DEMON_CASTS', True)
    monkeypatch.setattr(casters, 'BIND_GIVE_UP', False)
    play = Game(look(ARCHER))
    run = play.run()
    row = next(row for row in BUFFS if row.skill == BIND_DEMON)
    cast = Casting(run, row, Shared(run), play.world, ARCHER, 1.8, lambda w, skills: dict(KEYS))  # pyrefly: ignore[bad-argument-type]  # a fake executor
    for at in (41.9, 46.1, 49.8):
        play.clock.now = at
        assert casters.bind(cast).cast


# --- Item 7: a Consume that took the standing Defiler beside the one aimed at (casters.py CONSUME_ANY_DEFILER) ---


STANDING = Monster(1387530185, 744, 1, 5010.0, 5000.0, 0xFFFFFFFF, ally=True, life=128, max_life=230)
FRESH = Monster(1077230691, 744, 1, 5011.0, 4999.0, 0xFFFFFFFF, ally=True, life=128, max_life=128)


def test_a_consume_that_took_the_standing_defiler_is_a_consume(caplog):
    # 15:41:25.44: the key at the new Defiler took the old one 1.4 units off; "not seen in 2.5s", again in 20 s
    caplog.set_level(logging.INFO)
    play = Game(world(monsters=(STANDING, FRESH)))
    play.consume_takes = STANDING.unit_id
    casters.consume(play.run(), FRESH)
    assert play.character.consume
    assert [m.unit_id for m in play.world.monsters if m.txt_id == 744] == [FRESH.unit_id]
    assert 'Macro: Consume took the Defiler 1387530185 standing beside the one aimed at (1077230691)' in caplog.text


def test_without_any_defiler_the_same_consume_is_judged_not_seen(monkeypatch):
    monkeypatch.setattr(casters, 'CONSUME_ANY_DEFILER', False)
    play = Game(world(monsters=(STANDING, FRESH)))
    play.consume_takes = STANDING.unit_id
    with pytest.raises(Abort, match=r'not seen in 2\.5s'):
        casters.consume(play.run(), FRESH)


# --- In the hunt: a hurt demon under the held strike ---


def test_in_the_hunt_a_hurt_demon_unhealed_gets_engorge_often_then_slower(monkeypatch):
    from tests.inventory_tracking.macros.test_hunt import engorging, foe, game, hunter

    demon = Monster(50, 744, 1, 5003.0, 5003.0, 1, life=38, max_life=230)  # 30%, and the fakes never heal it
    # The cadence on one corpse that never heals: with pets.py ENGORGE_LEARNS that corpse is refused after its first
    # key (test_engorge_learns.py), so the old cadence is measured without it
    monkeypatch.setattr(pets, 'ENGORGE_LEARNS', False)

    def engorges():
        play = game(foe(10, 5008.0, 5000.0), foe(11, 5009.0, 5001.0), foe(12, 5009.0, 4999.0), demon)
        play.toughness.update({10: 10**6, 11: 10**6, 12: 10**6})
        engorging(play, hunter(play), [(91, 5006.0, 5004.0)], until=6.0)
        return len(play.engorges)

    now = engorges()
    monkeypatch.setattr(plan, 'PET_ENGORGE', False)
    before = engorges()
    # at the fight's start and ENGORGE_HURT_SECONDS later; the fakes count presses, and a key they did not keep after
    # the strike's release (macros/buffs.py QUICK_SETTLE) is pressed again (routines.press_through)
    assert 2 <= before <= 3
    # PET_UNHEALED at ENGORGE_DANGER_SECONDS, then one every ENGORGE_UNHEALED_SECONDS
    assert now >= PET_UNHEALED + 1


def test_the_packs_engorge_lets_the_strike_go_and_is_asked_again_by_its_own_cadence():
    # live 16:16:39-42: the pack's tries refused three times in 3 s under the held strike's record on a live Fallen
    play = Game(world(area=22, slots=HUNT_SLOTS))
    foes = pack(15)
    play.world = replace(play.world, monsters=(URDAR, *foes))
    buffs, run = Buffs(ECHOING_STRIKE_BUILD), play.run()
    strike = Strike()
    buffs.let_go = strike
    reads = []
    run.corpses = lambda: CORPSES
    run.hovered = lambda: reads.append(strike.released) or (MONSTER_UNIT, ARCHER.unit_id)
    play.clock.now = 50.0
    due = buffs.due(run, FIRST, buffs.facts(run, play.world, foes=foes))
    assert due is not None
    tried = buffs.cast(run, due, lambda w, skills: dict(KEYS), 1.8)
    assert not tried.cast
    assert reads[0] >= 1  # let go before the record was read
    assert Rotation(buffs).engorged_at == pytest.approx(play.clock.now - ENGORGE_PACK_SECONDS + casters.ENGORGE_RETRY)


def test_no_pull_while_the_bound_demon_is_out_with_the_character(monkeypatch):
    # 21:05:50-52: "bound Act 5 Combatant at 31/128, 20 Engorges with no heal", 4 pull hops in 2 s with the demon
    # taken along each time (pets.py PULL_ONCE_OUT)
    from inventory_tracking.combat import pack as herald_pack

    watch = pets.watch_of({})
    by_me = look(replace(URDAR, life=34))  # 4 from the character at (5000, 5000)
    watch.look(by_me, 1.0, plan.ENGORGE_BELOW)
    watch.unhealed = pets.PULL_UNHEALED
    assert pets.pull_wanted(watch, 1.0) is not None
    herald_pack.hopped(0.5, 14.0)  # the pull's hop landed 0.5 s ago, the demon taken along
    assert pets.pull(watch, 1.0, by_me) is None
    assert herald_pack.pulled(1.0) is None
    held_off = look(replace(URDAR, life=34, x=5014.0))  # 14 off, the pack on it
    watch.look(held_off, 1.1, plan.ENGORGE_BELOW)
    assert pets.pull(watch, 1.1, held_off) == 'bound Urdar at 34/128, 2 Engorges with no heal'
    watch.look(by_me, 4.0, plan.ENGORGE_BELOW)
    watch.unhealed = pets.PULL_UNHEALED
    assert pets.pull(watch, 4.0, by_me) is not None  # PULL_REST past the landing: asked again
    herald_pack.hopped(3.9, 14.0)
    monkeypatch.setattr(pets, 'PULL_ONCE_OUT', False)
    assert pets.pull(watch, 4.0, by_me) is not None  # as played: asked again at once
