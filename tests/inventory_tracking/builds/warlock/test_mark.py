"""Death Mark's row (builds/warlock/mark.py; rca/2026-10-14/death-mark.md): whom, when, and never what.

The player, 2026-10-14: "death mark is skill that forces daemons to attack and lowers enemy defence"; "a very
effective mechanism that allow to distract/re-aggro enemies". A mark at the start of each real fight on the
monster the demons should hold, again when it dies or its mark runs out, never on trash, never with no demon."""

from dataclasses import replace

from inventory_tracking.builds.warlock.mark import (
    MARK_AGAIN,
    MARK_DELAY,
    MARK_SECONDS,
    mark_due,
    mark_refusal,
    mark_said,
    target,
    worth_a_mark,
)
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.macros.build import BuffFacts, DrawPrice
from inventory_tracking.macros.game.records import Monster
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS, world


CHAMPION, SUPER_UNIQUE = 0x0C, 0x02
CHAOS = 108


def monster(unit, txt, x=5010.0, flags=0):
    return Monster(unit, txt, 1, x, 5000.0, 0xFFFFFFFF, flags, life=128, max_life=128)


def demon(unit=60):
    return Monster(unit, 361, 1, 4990.0, 5000.0, 0xFFFFFFFF, 0, ally=True, life=128, max_life=128)


DEMON = demon()


def facts(*foes, now=100.0, demons=(DEMON,), cast_at=None, draws=None):
    seen = world(CHAOS, slots=HUNT_SLOTS, monsters=(*foes, *demons))
    return BuffFacts(seen, now, tuple(foes), tuple(foes), cast_at=cast_at or {}, draws=draws)


def price(unit, life=0.0, gain=0.0, kappa=0.01):
    return DrawPrice(unit, life, life * kappa, gain, 1.0, 10.0)


SEAL_BOSS = monster(1, 312, flags=SUPER_UNIQUE | CHAMPION)  # a Venom Lord with the seal boss's flags
PACK = monster(2, 312, x=5012.0, flags=0x10)  # one of its minions
TRASH = replace(monster(3, 310, x=5008.0), life=64)  # a plain Doom Knight at half life: a cast or two kill it


def test_a_seal_boss_is_marked_at_the_start_of_its_fight_where_the_safety_prices_the_draw_worth_it():
    priced = {1: price(1, life=300.0), 2: price(2, life=50.0)}  # 3.0 s and 0.5 s of life against a 1.0 s cast
    asked = facts(SEAL_BOSS, PACK, draws=priced)
    assert mark_due(asked)
    assert target(asked) is SEAL_BOSS
    assert worth_a_mark(asked, SEAL_BOSS)
    said = mark_said(asked, SEAL_BOSS)
    assert said.startswith('Macro: mark: Death Mark on the elite 312 (1)')
    assert 'the safety prices it: saves 300 life' in said
    assert said.endswith('+2.00s')


def test_a_draw_the_safety_prices_below_its_cast_is_refused_and_said_once_with_the_price():
    asked = facts(SEAL_BOSS, draws={1: price(1, life=40.0)})
    assert target(asked) is SEAL_BOSS
    assert not worth_a_mark(asked, SEAL_BOSS)
    line = mark_refusal(asked, SEAL_BOSS)
    assert line is not None
    assert 'no Death Mark on the elite 312 (1)' in line
    assert 'the safety prices it' in line
    assert line.endswith('-0.60s')


def test_no_mark_on_trash_a_cast_or_two_kills_whatever_the_price():
    asked = facts(TRASH, draws={3: price(3, life=900.0)})
    assert not worth_a_mark(asked, TRASH)
    assert mark_refusal(asked, TRASH) is None  # a plain monster: nothing said
    nearly_dead = replace(TRASH, flags=CHAMPION, life=16)  # an elite with an eighth of its life left
    asked = facts(nearly_dead, draws={3: price(3, life=900.0)})
    assert not worth_a_mark(asked, nearly_dead)
    assert mark_refusal(asked, nearly_dead) is None  # no mark was in question: nothing said


def test_no_mark_without_a_demon_out():
    asked = facts(SEAL_BOSS, demons=(), draws={1: price(1, life=900.0)})
    assert not worth_a_mark(asked, SEAL_BOSS)
    assert "no demon of the character's is out" in (mark_refusal(asked, SEAL_BOSS) or '')
    merc = Monster(61, 338, 1, 4990.0, 5000.0, 0xFFFFFFFF, 0, ally=True)  # the mercenary is no demon
    assert not worth_a_mark(facts(SEAL_BOSS, demons=(merc,), draws={1: price(1, life=900.0)}), SEAL_BOSS)


def test_no_new_mark_while_the_marked_one_lives_and_its_mark_lasts_then_one_when_it_dies_or_runs_out():
    priced = {1: price(1, life=300.0), 2: price(2, life=200.0)}
    marked = {(DEATH_MARK, None): 100.0, (DEATH_MARK, 1): 100.0}
    soon = facts(SEAL_BOSS, PACK, now=100.0 + MARK_DELAY + 0.1, cast_at=marked, draws={2: price(2, life=50.0)})
    assert mark_due(soon)
    assert target(soon) is None  # the boss is held: the pack is not worth moving the demons for
    # It died: the next fight's monster is marked once the skill's delay is over
    dead = facts(PACK, now=100.0 + MARK_DELAY + 0.1, cast_at=marked, draws=priced)
    assert target(dead) is PACK
    # Its mark ran out while it lives: marked again
    out = facts(SEAL_BOSS, PACK, now=100.0 + MARK_SECONDS + 0.1, cast_at=marked, draws=priced)
    assert target(out) is SEAL_BOSS
    # A mark moves to another the safety prices above nothing, no sooner than MARK_AGAIN after the last: another
    # pack's leader; a plain monster not while a leader of the fight is in reach (the marked one lives)
    other = monster(5, 362, x=5016.0, flags=CHAMPION)
    moved = facts(SEAL_BOSS, PACK, other, now=100.0 + MARK_AGAIN + 0.1, cast_at=marked, draws={5: price(5, life=200.0)})
    assert target(moved) is other
    assert target(replace(moved, now=100.0 + MARK_AGAIN - 0.1)) is None
    plain = facts(SEAL_BOSS, PACK, now=100.0 + MARK_AGAIN + 0.1, cast_at=marked, draws={2: price(2, life=200.0)})
    assert target(plain) is None


def test_with_no_safety_price_the_builds_own_rule_marks_diablo_and_not_a_seal_boss():
    # The pursuit off: the demons' focus and the mark's points alone (mark.py `gain`) against the cast, one volley
    # of the strike; the demons' blows count from their first (`first_blow`, 1.64 s after the key), which a seal
    # boss of six or seven casts barely sees, Diablo's twenty do
    diablo = monster(9, 243)
    assert target(facts(diablo)) is diablo
    assert worth_a_mark(facts(diablo), diablo)
    assert "by the build's rule (no safety price)" in mark_said(facts(diablo), diablo)
    assert not worth_a_mark(facts(SEAL_BOSS), SEAL_BOSS)
    # The demons standing by him already: nothing gained by sending them
    beside = replace(demon(), x=diablo.x - 2.0)
    assert not worth_a_mark(facts(diablo, demons=(beside,)), diablo)


def test_a_plain_monster_is_not_marked_while_a_leader_of_the_same_fight_is_in_reach():
    # 02:22:47-48 on 2026-10-14: two marks a second apart on a plain Venom Lord and a plain Doom Knight; the
    # player: the mark goes "on the leader / most dangerous monster", "a plain monster is not marked while an elite
    # of the same fight is in reach".
    plain = monster(4, 310, x=5006.0)
    asked = facts(SEAL_BOSS, plain, draws={4: price(4, life=400.0), 1: price(1, life=150.0)})
    assert target(asked) is SEAL_BOSS
    assert worth_a_mark(asked, SEAL_BOSS)
    # The leader's own price refused: the plain one is not marked in its place
    refused = facts(SEAL_BOSS, plain, draws={4: price(4, life=400.0), 1: price(1, life=10.0)})
    assert target(refused) is SEAL_BOSS
    assert not worth_a_mark(refused, SEAL_BOSS)
    # No leader in reach, or only one a cast or two kills: the plain one the price names
    assert target(facts(plain, draws={4: price(4, life=400.0)})) is plain
    weak = replace(SEAL_BOSS, life=8)
    assert target(facts(weak, plain, draws={4: price(4, life=400.0), 1: price(1, life=150.0)})) is plain


def test_a_plain_monster_is_marked_for_its_pack_only_when_the_fight_presses():
    # The player: "a pack big enough to hurt" is marked, "plain trash" is not; a plain monster's mark is the re-aggro
    # under pressure: holding without it over the life budget (`DrawPrice.pressed`, macros/safety.py)
    plain = monster(4, 310, x=5006.0)
    calm = facts(plain, draws={4: price(4, life=400.0)})
    assert target(calm) is plain
    assert not worth_a_mark(calm, plain)
    assert mark_refusal(calm, plain) is None  # a plain monster: nothing said
    pressed = facts(plain, draws={4: replace(price(4, life=400.0), pressed=True)})
    assert worth_a_mark(pressed, plain)
    assert not worth_a_mark(facts(plain), plain)  # with no safety price no pack is priced


# The Infector's seal boss of 06:08:23.4 to 27.04 on 2026-10-14 (rca/2026-10-14/run-0305-findings.md §2): unit
# 3610904851, an Infector of Souls (362) with flags 10, at about a third of its life when the fight resumed.
INFECTOR = Monster(3610904851, 362, 1, 5010.0, 5000.0, 0xFFFFFFFF, SUPER_UNIQUE | 0x08, life=42, max_life=128)


def test_a_seal_boss_dropped_from_the_mark_is_said_once_with_why(caplog):
    import logging

    from inventory_tracking.builds.warlock.buffs import BUFFS
    from inventory_tracking.macros.buffs import Buffs
    from inventory_tracking.macros.build import Build
    from tests.inventory_tracking.macros.fakes import Game

    row = next(row for row in BUFFS if row.skill == DEATH_MARK)
    asked = facts(INFECTOR, PACK, draws={2: price(2, life=10.0)})
    assert target(asked) is not INFECTOR  # no mark goes on it
    buffs = Buffs(Build(name='warlock', applies=lambda world: True, attack=None, movement=(), buffs=(row,)))
    run = Game(asked.world).run()
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        buffs.due(run, row, asked)
        buffs.due(run, row, asked)
    said = [r.getMessage() for r in caplog.records if r.getMessage().startswith('Macro: mark:')]
    infector = [line for line in said if '3610904851' in line]
    assert len(infector) == 1, said
    assert 'dropped from the mark: trash now' in infector[0]
    # a plain monster or a champion a cast or two kills is not named
    assert not any('(3)' in line for line in said)
