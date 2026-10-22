"""Death Mark's row (builds/warlock/mark.py; rca/2026-10-14/death-mark.md): whom, when, and never what.

The player, 2026-10-14: "death mark is skill that forces daemons to attack and lowers enemy defence"; "a very
effective mechanism that allow to distract/re-aggro enemies". A mark at the start of each real fight on the
monster the demons should hold, again when it dies or its mark runs out, never on trash, never with no demon."""

from dataclasses import replace

from inventory_tracking.builds.warlock import mark
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
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.build import BuffFacts, DrawPrice
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
    assert said is not None
    assert said.startswith('Macro: mark: Death Mark on the elite 312 (1)')
    assert 'the safety prices it: saves 300 life' in said
    assert said.endswith('+2.00s')


def test_a_draw_the_safety_prices_below_its_cast_is_refused_and_said_once_with_the_price(monkeypatch):
    monkeypatch.setattr(mark, 'MARK_LEADERS', False)  # the price rule for a leader: the switch off
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


def test_with_no_safety_price_the_builds_own_rule_marks_diablo_and_not_a_seal_boss(monkeypatch):
    monkeypatch.setattr(mark, 'MARK_LEADERS', False)  # the price rule for a leader: the switch off
    # The pursuit off: the demons' focus and the mark's points alone (mark.py `gain`) against the cast, one volley
    # of the strike; the demons' blows count from their first (`first_blow`, 1.64 s after the key), which a seal
    # boss of six or seven casts barely sees, Diablo's twenty do
    diablo = monster(9, 243)
    assert target(facts(diablo)) is diablo
    assert worth_a_mark(facts(diablo), diablo)
    assert "by the build's rule (no safety price)" in (mark_said(facts(diablo), diablo) or '')
    assert not worth_a_mark(facts(SEAL_BOSS), SEAL_BOSS)
    # The demons standing by him already: nothing gained by sending them
    beside = replace(demon(), x=diablo.x - 2.0)
    assert not worth_a_mark(facts(diablo, demons=(beside,)), diablo)


def test_a_plain_monster_is_not_marked_while_a_leader_of_the_same_fight_is_in_reach(monkeypatch):
    monkeypatch.setattr(mark, 'MARK_LEADERS', False)  # the price rule for a leader: the switch off
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


# The player, 2026-10-20 ~14:31: "we need to engage our daemon even for regular mobs when they do have magic immunity".
# An Unraveler (103) as the takes of 2026-10-20 read it: physical 33, magic 100, fire 20, lightning 20, cold 100,
# poison 50.
UNRAVELER_RESISTS = ((36, 33), (37, 100), (39, 20), (41, 20), (43, 100), (45, 50))
IMMUNE = replace(monster(7, 103, x=5014.0), resists=UNRAVELER_RESISTS)


def test_a_plain_monster_immune_to_magic_is_marked_whatever_its_life_and_said_once_why():
    from inventory_tracking.builds.warlock.mark import mark_told

    for draws in (None, {}, {7: price(7, life=0.0)}):  # no price, none for it, one that pays nothing
        asked = facts(IMMUNE, PACK, draws=draws)
        assert target(asked) is IMMUNE
        assert worth_a_mark(asked, IMMUNE)
    nearly_dead = replace(IMMUNE, life=4)  # trash by the strike's table: the rule does not hold for it
    assert worth_a_mark(facts(nearly_dead), nearly_dead)
    assert mark_said(facts(IMMUNE), IMMUNE) is None  # the cast's own line is the executor's; why is told once
    assert mark_told(facts(IMMUNE), IMMUNE) == (
        'Macro: mark: Death Mark on the monster 103 (7): immune to magic, cold '
        '(resists physical 33, magic 100, fire 20, lightning 20, cold 100, poison 50)'
    )
    assert mark_told(facts(PACK), PACK) is None


def test_an_immune_monster_comes_before_a_leader_and_after_a_herald():
    priced = {1: price(1, life=300.0), 7: price(7, life=10.0)}
    assert target(facts(SEAL_BOSS, IMMUNE, draws=priced)) is IMMUNE
    assert target(facts(SEAL_BOSS, IMMUNE)) is IMMUNE  # with no safety price too
    herald = monster(8, 103, x=5020.0, flags=0x08)
    herald = replace(herald, tier=3)
    assert target(facts(IMMUNE, herald, draws=priced)) is herald


def test_no_mark_on_an_immune_monster_without_a_demon_and_said_once_why():
    asked = facts(IMMUNE, demons=())
    assert target(asked) is IMMUNE
    assert not worth_a_mark(asked, IMMUNE)
    assert "no demon of the character's is out" in (mark_refusal(asked, IMMUNE) or '')


def test_a_monster_that_resists_magic_short_of_immunity_is_marked_as_before():
    resistant = replace(monster(7, 103, x=5014.0), resists=((36, 33), (37, 95)))
    calm = facts(resistant, draws={7: price(7, life=400.0)})
    assert target(calm) is resistant
    assert not worth_a_mark(calm, resistant)  # a plain monster, no pressure
    assert mark_refusal(calm, resistant) is None
    unread = monster(7, 103, x=5014.0)  # no resistances read: none known
    assert not worth_a_mark(facts(unread, draws={7: price(7, life=400.0)}), unread)


def test_the_immune_ones_mark_stays_on_it_while_it_lasts_and_is_laid_again_when_it_runs_out():
    marked = {(DEATH_MARK, None): 100.0, (DEATH_MARK, 7): 100.0}
    other = monster(5, 362, x=5016.0, flags=CHAMPION)
    later = 100.0 + MARK_AGAIN + 0.1
    # A leader the safety prices above nothing does not take the demons off it; one under pressure does
    assert target(facts(IMMUNE, other, now=later, cast_at=marked, draws={5: price(5, life=200.0)})) is None
    pressed = {5: replace(price(5, life=200.0), pressed=True)}
    assert target(facts(IMMUNE, other, now=later, cast_at=marked, draws=pressed)) is other
    assert target(facts(IMMUNE, other, now=later, cast_at=marked)) is None  # no price: none while a mark lasts
    # A second immune one waits for the first's mark to end
    second = replace(IMMUNE, unit_id=9, x=5004.0)
    assert target(facts(IMMUNE, second, now=later, cast_at=marked)) is None
    # Its mark ran out while it lives: laid again
    out = facts(IMMUNE, other, now=100.0 + MARK_SECONDS + 0.1, cast_at=marked, draws={5: price(5, life=200.0)})
    assert mark_due(out)
    assert target(out) is IMMUNE
    assert worth_a_mark(out, IMMUNE)


def test_the_safety_stops_an_immune_ones_mark_only_while_the_cast_costs_life_over_the_budget():
    costly = replace(price(7, life=-50.0), pressed=True)
    asked = facts(IMMUNE, draws={7: costly})
    assert not worth_a_mark(asked, IMMUNE)
    line = mark_refusal(asked, IMMUNE)
    assert line is not None
    assert 'immune to magic, cold' in line
    assert 'over the life budget' in line
    assert worth_a_mark(facts(IMMUNE, draws={7: price(7, life=-50.0)}), IMMUNE)  # no pressure: the cost is in budget


def test_mark_immune_off_marks_as_before(monkeypatch):
    monkeypatch.setattr(mark, 'MARK_IMMUNE', False)
    calm = facts(IMMUNE, draws={7: price(7, life=400.0)})
    assert not worth_a_mark(calm, IMMUNE)
    assert target(facts(SEAL_BOSS, IMMUNE, draws={1: price(1, life=300.0), 7: price(7, life=400.0)})) is SEAL_BOSS


def test_the_executor_says_the_immune_ones_line_at_its_first_mark_only(caplog):
    import logging

    from inventory_tracking.builds.warlock.buffs import BUFFS
    from inventory_tracking.macros.buffs import Buffs
    from inventory_tracking.macros.build import Build

    row = next(row for row in BUFFS if row.skill == DEATH_MARK)
    assert row.told is not None
    asked = facts(IMMUNE, PACK)
    buffs = Buffs(Build(name='warlock', applies=lambda world: True, attack=None, movement=(), buffs=(row,)))
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        for _ in range(2):
            buffs.tell_once(row, IMMUNE, row.told(asked, IMMUNE))
    told = [r.getMessage() for r in caplog.records if 'immune to' in r.getMessage()]
    assert len(told) == 1
    assert told[0].startswith('Macro: mark: Death Mark on the monster 103 (7): immune to magic')


# The player, 2026-10-20 ~15:03: "we were fighting against pack with uniq leader, but we focused rest of the pack, not
# leader and never death marked the leader so our daemon was still all the time" (Spider Forest, game 3 of the session
# of 11:55Z; rca/2026-10-20/leader-not-marked-findings.md). The character's demons: the Defiler (744) and a bound Urdar
# (189, flags 8, an ally), which data/damage.json does not measure.
DEFILER = Monster(70, 744, 1, 4990.0, 5000.0, 0xFFFFFFFF, 0, ally=True, life=128, max_life=128)
URDAR = Monster(71, 189, 1, 4991.0, 5000.0, 0xFFFFFFFF, 0x08, ally=True, life=128, max_life=128)
HULK = Monster(3898117827, 127, 1, 5014.0, 5000.0, 0xFFFFFFFF, 0x08, life=128, max_life=128)  # the unique Thorned Hulk
FETISH = Monster(1156325300, 397, 1, 5015.0, 5000.0, 0xFFFFFFFF, 0x08, life=128, max_life=128)  # the unique Fetish
# The safety's price of 15:01:23.869: "saves -0 life over 1.9s (-0.00s at the price of life) and 0.14s of the fight,
# against the cast's 0.37s: -0.24s"
HULK_PRICE = DrawPrice(HULK.unit_id, -0.1, -0.001, 0.14, 0.37, 1.9)


SPIDER_FOREST = 76


def spider_forest(*foes, demons=(DEFILER, URDAR), **changes):
    seen = world(SPIDER_FOREST, slots=HUNT_SLOTS, monsters=(*foes, *demons))
    asked = BuffFacts(seen, 100.0, tuple(foes), tuple(foes), draws={HULK.unit_id: HULK_PRICE})
    return replace(asked, **changes)


def test_an_unmeasured_bound_demon_strikes_at_the_measured_ones_rate_by_its_damage(monkeypatch):
    from inventory_tracking.builds.warlock.echoing_strike.damage import companion_table
    from inventory_tracking.combat.mechanics.tables import points_of
    from inventory_tracking.combat.policy import Foe, Observation

    pit_lord = companion_table()[361][1]
    assert mark.demon_rate(361) == pit_lord
    assert mark.demon_rate(744) == companion_table()[744][1]
    assert mark.demon_rate(338) == companion_table()[338][1]  # the mercenary as measured; never sent (`sends`)
    assert mark.demon_rate(189) == pit_lord * 115 / 130  # monstats A1 90-140 against the Pit Lord's 100-160
    seen = Observation((0.0, 0.0), {1: Foe(127, (10.0, 0.0), points_of(127, 76), True)})
    # The game's price had the Defiler's blows alone: 0.14 s; with the Urdar's the mark pays for its cast
    assert round(mark.gain(seen, 1, [744]), 2) == 0.14
    assert mark.gain(seen, 1, [744, 189]) > mark.MARK_CAST_SECONDS
    monkeypatch.setattr(mark, 'PRICE_ANY_DEMON', False)
    assert mark.demon_rate(189) == 0.0
    assert round(mark.gain(seen, 1, [744, 189]), 2) == 0.14


def test_a_unique_leader_in_reach_is_marked_whatever_the_price_with_a_demon_to_send(monkeypatch):
    monkeypatch.setattr(mark, 'MARK_LEADERS', True)  # on since 2026-10-20 ("pack leader/herald first")
    asked = spider_forest(HULK, PACK)
    assert target(asked) is HULK
    assert worth_a_mark(asked, HULK)  # -0.24 s by the price, marked: "on the leader"
    assert mark_refusal(asked, HULK) is None
    # Only a life cost while holding is over the budget stops it
    costly = DrawPrice(HULK.unit_id, -80.0, -0.8, 0.14, 0.37, 1.9, pressed=True)
    pressed = spider_forest(HULK, PACK, draws={HULK.unit_id: costly})
    assert not worth_a_mark(pressed, HULK)
    assert 'over the life budget' in (mark_refusal(pressed, HULK) or '')
    # Unpriced (a third leader of the look) or with no safety price at all: marked too
    assert worth_a_mark(spider_forest(HULK, draws={}), HULK)
    assert target(spider_forest(HULK, draws=None)) is HULK
    assert worth_a_mark(spider_forest(HULK, draws=None), HULK)
    # Never with no demon out, nor when every demon strikes it already
    assert not worth_a_mark(spider_forest(HULK, demons=()), HULK)
    beside = (replace(DEFILER, x=HULK.x - 2.0), replace(URDAR, x=HULK.x + 2.0))
    by_it = spider_forest(HULK, demons=beside)
    assert not worth_a_mark(by_it, HULK)
    assert 'the demons stand by it already' in (mark_refusal(by_it, HULK) or '')
    # Of two leaders, the one the demons are not striking already
    far = replace(HULK, unit_id=5, x=5030.0)
    assert target(replace(by_it, foes=(HULK, far), reachable=(HULK, far))) is far


def test_a_leader_comes_after_a_herald_and_an_immune_one_and_takes_the_mark_off_plain_monsters(monkeypatch):
    monkeypatch.setattr(mark, 'MARK_LEADERS', True)  # on since 2026-10-20 ("pack leader/herald first")
    herald = replace(monster(8, 103, x=5020.0, flags=0x08), tier=3)
    assert target(spider_forest(HULK, herald)) is herald
    assert target(spider_forest(HULK, IMMUNE)) is IMMUNE
    # A mark lasting on a plain monster (a re-aggro under pressure) moves to the leader, MARK_AGAIN after
    plain = monster(4, 310, x=5006.0)
    marked = {(DEATH_MARK, None): 100.0, (DEATH_MARK, 4): 100.0}
    assert target(spider_forest(HULK, plain, now=100.0 + MARK_AGAIN + 0.1, cast_at=marked)) is HULK
    assert target(spider_forest(HULK, plain, now=100.0 + MARK_AGAIN - 0.1, cast_at=marked)) is None
    # A lasting mark on another leader stays (a move needs a price above nothing, as before)
    other = replace(HULK, unit_id=5, x=5008.0)
    on_other = {(DEATH_MARK, None): 100.0, (DEATH_MARK, 5): 100.0}
    assert target(spider_forest(HULK, other, now=100.0 + MARK_AGAIN + 0.1, cast_at=on_other)) is None
    # A boss before a leader; of two leaders the better priced, then the nearer
    priced = {HULK.unit_id: HULK_PRICE, 5: DrawPrice(5, 100.0, 1.0, 0.1, 0.37, 1.9)}
    assert target(spider_forest(HULK, other, draws=priced)) is other
    assert target(spider_forest(HULK, other, draws={})) is other  # 6 units nearer than the Hulk
    assert target(spider_forest(HULK, SEAL_BOSS, draws={})) is SEAL_BOSS


def test_mark_leaders_off_leaves_a_leader_to_the_price(monkeypatch):
    monkeypatch.setattr(mark, 'MARK_LEADERS', False)
    asked = spider_forest(HULK, PACK)
    assert target(asked) is HULK
    assert not worth_a_mark(asked, HULK)
    assert (mark_refusal(asked, HULK) or '').endswith('-0.23s')


def test_a_leader_the_mark_passes_over_is_said_once_with_why(caplog, monkeypatch):
    monkeypatch.setattr(mark, 'MARK_LEADERS', True)  # on since 2026-10-20 ("pack leader/herald first")
    # 15:01:12.9-13.8: the unique Fetish 397 (1156325300) in reach a second, killed by one cast: trash by the
    # strike's table (1.85 casts), so never marked, and nothing said
    import logging

    from inventory_tracking.builds.warlock.buffs import BUFFS
    from inventory_tracking.builds.warlock.mark import mark_passed
    from inventory_tracking.macros.buffs import Buffs
    from inventory_tracking.macros.build import Build
    from tests.inventory_tracking.macros.fakes import Game

    passed = {m.unit_id: line for m, line in mark_passed(spider_forest(FETISH, PACK))}
    assert passed[FETISH.unit_id] == (
        'Macro: mark: no Death Mark on the elite 397 (1156325300), 128/128: trash: 1.8 casts of the strike kill it '
        '(a mark needs more than 2)'
    )
    # A leader passed while the mark lasts on another, with its price; the one chosen is not named (its refusal is)
    other = replace(HULK, unit_id=5, x=5008.0)
    on_other = {(DEATH_MARK, None): 100.0, (DEATH_MARK, 5): 100.0}
    held = spider_forest(HULK, other, now=101.0, cast_at=on_other)
    lines = {m.unit_id: line for m, line in mark_passed(held)}
    assert 'the mark lasts on the elite 127 (5) (11.3s left); the safety prices it: saves' in lines[HULK.unit_id]
    assert 5 not in lines
    assert not mark_passed(spider_forest(HULK, PACK))  # the Hulk is the one chosen: nothing passed
    two = {m.unit_id: line for m, line in mark_passed(spider_forest(HULK, other, draws={}))}
    assert two == {
        HULK.unit_id: 'Macro: mark: no Death Mark on the elite 127 (3898117827), 128/128: the mark goes on '
        'the elite 127 (5) first'
    }
    # Through the executor: once a monster
    row = next(row for row in BUFFS if row.skill == DEATH_MARK)
    buffs = Buffs(Build(name='warlock', applies=lambda world: True, attack=None, movement=(), buffs=(row,)))
    asked = spider_forest(FETISH, PACK)
    run = Game(asked.world).run()
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        buffs.due(run, row, asked)
        buffs.due(run, row, asked)
    said = [r.getMessage() for r in caplog.records if '1156325300' in r.getMessage()]
    assert len(said) == 1, said
    assert 'trash: 1.8 casts' in said[0]


def test_say_passed_off_names_bosses_only(monkeypatch):
    from inventory_tracking.builds.warlock.mark import mark_passed

    monkeypatch.setattr(mark, 'SAY_PASSED', False)
    assert not mark_passed(spider_forest(FETISH, PACK))


# The player, 2026-10-20 ~18:45: "ok, recast. pack leader/herald first"
# (rca/2026-10-20/mark-recast-leaders-findings.md).
# A marked monster's state words as the recorder read them (take 20261020T101827Z-111, a txt 453 with stat 34 -33 and
# stat 31 -540): state 212 is bit 20 of the seventh word.
MARKED_WORDS = bytes.fromhex('0000000008000000000000000002000000000000000000200000100000000000')


def test_the_mark_shows_by_state_212_in_the_monsters_state_words():
    from inventory_tracking.builds.warlock.mark import MARK_STATE, mark_shows, state_on

    assert MARK_STATE == 212
    assert mark_shows(MARKED_WORDS)
    assert not mark_shows(bytes(32))
    unmarked = bytearray(MARKED_WORDS)
    unmarked[26] &= ~0x10
    assert not mark_shows(bytes(unmarked))
    assert state_on(MARKED_WORDS, 212)
    assert not state_on(MARKED_WORDS, 211)
    assert not mark_shows(MARKED_WORDS[:24])  # short: not read as shown


def test_the_death_mark_row_is_checked_and_cast_again_twice_at_most():
    from inventory_tracking.builds.warlock.buffs import BUFFS
    from inventory_tracking.builds.warlock.mark import MARK_RECASTS, MARK_SHOWS, mark_shows

    row = next(row for row in BUFFS if row.skill == DEATH_MARK)
    assert row.shows is mark_shows
    assert row.shows_within == MARK_SHOWS == 0.8  # the latest of 283 marks that took showed 0.80 s after the key
    assert row.recasts == MARK_RECASTS == 2


def test_a_mark_that_did_not_take_on_a_leader_goes_on_it_again_through_the_executor(caplog):
    import logging

    from inventory_tracking.builds.warlock.buffs import BUFFS
    from inventory_tracking.macros.buffs import Buffs
    from inventory_tracking.macros.build import Build
    from tests.inventory_tracking.macros.fakes import WINDOW, Game

    row = next(row for row in BUFFS if row.skill == DEATH_MARK)
    buffs = Buffs(Build(name='warlock', applies=lambda world: True, attack=None, movement=(), buffs=(row,)))
    play = Game(spider_forest(HULK, PACK).world)
    run = play.run()
    shown: dict[int, bytes] = {}
    run.unit_states = lambda m: shown.get(m.unit_id, bytes(32))

    def ask(after: float):
        play.clock.now += after
        return buffs.due(run, row, replace(spider_forest(HULK, PACK), cast_at=buffs.cast_at))

    keys = []
    with caplog.at_level(logging.INFO, logger='inventory_tracking'):
        for _ in range(4):
            due = ask(1.0)
            if due is None:
                break
            assert due.target is HULK
            assert buffs.cast(run, due, lambda world, skills: {DEATH_MARK: 'd'}, WINDOW[2] / WINDOW[3]).cast
            keys.append(play.clock.now)
        assert len(keys) == 3  # the first and two again
        lines = [r.getMessage() for r in caplog.records if 'did not take' in r.getMessage()]
        assert [line.rsplit(': ', 1)[-1] for line in lines] == [
            'cast again (try 2)', 'cast again (try 3)', 'not cast again on it while the last would last'
        ]  # fmt: skip
        assert lines[0].startswith('Macro: buff: Death Mark on the elite 127 (3898117827), 128/128 did not take')
        # A mark that shows ends the watch: none again on it
        buffs.missed.clear()
        buffs.cast_at.clear()
        due = ask(1.0)
        assert due is not None
        buffs.cast(run, due, lambda world, skills: {DEATH_MARK: 'd'}, WINDOW[2] / WINDOW[3])
        shown[HULK.unit_id] = MARKED_WORDS
        assert ask(0.5) is None
        assert ask(1.0) is None
        assert buffs.watching == {}


def test_a_packs_leader_is_marked_before_its_minions_whatever_their_price_and_a_herald_and_immune_one_first():
    assert mark.MARK_LEADERS  # on since 2026-10-20
    priced = {PACK.unit_id: DrawPrice(PACK.unit_id, 300.0, 3.0, 0.0, 0.37, 1.9, pressed=True), HULK.unit_id: HULK_PRICE}
    asked = spider_forest(HULK, PACK, draws=priced)
    assert target(asked) is HULK
    assert worth_a_mark(asked, HULK)
    herald = replace(monster(8, 103, x=5020.0, flags=0x08), tier=3)
    assert target(spider_forest(HULK, PACK, herald, draws=priced)) is herald
    assert target(spider_forest(HULK, PACK, IMMUNE, draws=priced)) is IMMUNE
    # Life low: the leader's mark is stopped only where the cast costs life while holding is over the budget
    costly = {**priced, HULK.unit_id: DrawPrice(HULK.unit_id, -80.0, -0.8, 0.14, 0.37, 1.9, pressed=True)}
    assert not worth_a_mark(spider_forest(HULK, PACK, draws=costly), HULK)
