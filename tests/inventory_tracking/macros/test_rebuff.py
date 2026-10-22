"""Battle Orders kept through a fight, and the forecast's auras, reach and danger looks (2026-10-22): the Fane's arena
(tests/.../arena/situations/fane_death.py; rca/2026-10-21/fane-death-sim-findings.md) found Battle Orders never renewed
in a strike bout, no aura in the forecast, landings within reach of Might-raised blows, and late looks that priced no
retreat in a walled corridor. The player: "probably we need to keep track of battle order and predict when it runs
off, retreat and rebuff"; "we must have top priority to no die ourselves and prevent loosing experience".

macros/cta.py REBUFF (`orders_look`, `cast_safe`, `expired_hold`); macros/safety.py ORDERS_PREDICT, REBUFF_RETREAT,
AURA_FORECAST, REACH_BAR, CLEAR_FOOTING, DANGER_LOOK; macros/pursuit.py REBUFF_FIRST; combat/survival.py READ_LAG."""

import math
from dataclasses import replace

import pytest

from inventory_tracking.combat import survival
from inventory_tracking.combat.harm import Hostile, Protection, kind_of, most_blow
from inventory_tracking.combat.survival import DrinkSettings, Pressure, Supply, drink
from inventory_tracking.game.records import Monster
from inventory_tracking.macros import cta, pursuit as p, safety as module
from inventory_tracking.macros.buffs import Buffs
from inventory_tracking.macros.build import BuffFacts, Casting
from inventory_tracking.macros.cta import (
    BATTLE_ORDERS,
    EXPIRED_WAIT,
    FIGHT_LEFT,
    ORDERS_CLEAR,
    ORDERS_FACTOR,
    ORDERS_LASTS,
    REBUFF_GRACE,
    ROWS,
    OrdersLook,
    call_to_arms,
    orders_look,
    track_of,
)
from inventory_tracking.models import PotionType
from tests.inventory_tracking.macros.fakes import BUILD, PREBUFF_SET, Game
from tests.inventory_tracking.macros.test_cta import CTA_SET, GONE, SHOWN, keys
from tests.inventory_tracking.macros.test_death_pricing import hostiles, later, snap
from tests.inventory_tracking.macros.test_herald_pricing import priced


NIGHT_LORD = 132
UNIQUE_NIGHT_LORD = 4206932652
MIGHT_UNIQUE = 120235824
NEAR = Monster(7, 19, 1, 5008.0, 5000.0, life=100, max_life=128)  # 8 from the character: within ORDERS_CLEAR
MID = Monster(9, 19, 1, 5012.0, 5000.0, life=100, max_life=128)  # 12 away: a fight, clear of ORDERS_CLEAR


def asked(foes=(), *, hurt=False, rebuffed=-math.inf, now=1000.0):
    return BuffFacts(SHOWN, now, tuple(foes), focused=lambda: True, cta=True, hurt=lambda: hurt, rebuffed=rebuffed)


def words(*states: int) -> bytes:
    """State words (game/layout.py STATE_RUN) with `states` set."""
    found = bytearray(32)
    for state in states:
        word, bit = divmod(state, 32)
        value = int.from_bytes(found[word * 4 : word * 4 + 4], 'little') | 1 << bit
        found[word * 4 : word * 4 + 4] = value.to_bytes(4, 'little')
    return bytes(found)


# -- Battle Orders: tracked, cast in place when safe, else after the retreat -----------------------------------------


def test_in_a_fight_it_is_cast_in_place_only_with_nothing_within_reach_and_not_hurt():
    renew = cta.renew_orders
    assert renew(asked([NEAR]), FIGHT_LEFT - 1.0) is None  # a hostile within ORDERS_CLEAR: the retreat first
    said = renew(asked([MID]), FIGHT_LEFT - 1.0)
    assert said is not None
    assert said.startswith('9 s left: cast in place')
    assert renew(asked([MID]), FIGHT_LEFT + 5.0) is None  # not due yet
    assert renew(asked([MID], hurt=True), FIGHT_LEFT - 1.0) is None  # hurt within HURT_SECONDS
    # The rebuff retreat's landing casts it, though just hurt
    landed = renew(asked([MID], hurt=True, rebuffed=1000.0 - REBUFF_GRACE / 2), FIGHT_LEFT - 1.0)
    assert landed is not None
    assert 'at the rebuff landing' in landed
    # Its age not known (a restart): cast at the first safe moment, in a fight too (the Fane: its first look was one)
    unknown = renew(asked([MID]), None)
    assert unknown is not None
    assert unknown.startswith('age not known: cast in place')


def test_with_the_switch_off_a_fight_casts_it_only_with_its_age_known_unhurt(monkeypatch):
    monkeypatch.setattr(cta, 'REBUFF', False)
    assert cta.renew_orders(asked([NEAR]), FIGHT_LEFT - 1.0) is not None
    assert cta.renew_orders(asked([MID]), None) is None


def test_every_look_tracks_its_run_out_its_life_factor_and_why_it_is_due():
    play = Game(SHOWN)
    run = play.run()
    run.lasting = {BATTLE_ORDERS: run.clock() - ORDERS_LASTS + 30.0}
    looked = orders_look(run, SHOWN, [MID], hurt=False, max_life=2943, worn=True)
    assert looked is not None
    assert looked.shown
    assert looked.left == pytest.approx(30.0)
    assert looked.due is None  # 30 s left: not yet
    assert looked.factor == pytest.approx(ORDERS_FACTOR)  # not measured this game yet
    run.lasting[BATTLE_ORDERS] = run.clock() - ORDERS_LASTS + 6.0
    looked = orders_look(run, SHOWN, [MID], hurt=False, max_life=2943, worn=True)
    assert looked is not None
    assert looked.due == '6 s left'
    assert looked.safe
    assert not orders_look(run, SHOWN, [NEAR], hurt=False, max_life=2943, worn=True).safe  # type: ignore[union-attr]
    gone = orders_look(run, GONE, [NEAR], hurt=True, max_life=1896, worn=True)
    assert gone is not None
    assert gone.due == 'run out'
    assert track_of(run).expired_at == pytest.approx(run.clock())
    assert gone.factor == pytest.approx(2943 / 1896)  # measured: with it 2943, without 1896
    assert orders_look(run, GONE, [], hurt=False, max_life=1896, worn=False) is None  # no Call to Arms worn
    run.lasting = {}
    unknown = orders_look(run, SHOWN, [MID], hurt=False, max_life=2943, worn=True)
    assert unknown is not None
    assert unknown.due == 'its age is not known'


def expired_cast(play: Game, *, ago: float):
    run = play.run()
    track_of(run).shown, track_of(run).expired_at = False, run.clock() - ago
    [row] = ROWS
    return call_to_arms(Casting(run, row, Buffs(BUILD), run.world(), key_names=keys))


def test_after_a_run_out_in_the_pack_the_cast_waits_for_the_retreat_then_casts_where_it_stands(caplog):
    play = Game(replace(GONE, monsters=(NEAR,)))
    play.staff = None
    play.sets = [PREBUFF_SET, CTA_SET]
    with caplog.at_level('INFO'):
        tried = expired_cast(play, ago=0.4)
    assert not tried.cast
    assert 'F8' not in play.pressed()
    assert 'Macro: buff: Battle Orders: expired 0.4 s ago: a retreat first' in caplog.text
    play = Game(replace(GONE, monsters=(NEAR,)))
    play.staff = None
    play.sets = [PREBUFF_SET, CTA_SET]
    assert expired_cast(play, ago=EXPIRED_WAIT + 0.5).cast  # no retreat came: cast where it stands, as before
    play = Game(replace(GONE, monsters=(MID,)))
    play.staff = None
    play.sets = [PREBUFF_SET, CTA_SET]
    assert expired_cast(play, ago=0.4).cast  # clear of them: at once
    assert 'F8' in play.pressed()


# -- The safety: the life after it runs out, and the retreat to rebuff ------------------------------------------------


def due_look(left: float | None = 5.0, *, safe: bool = False) -> OrdersLook:
    return OrdersLook(True, left, ORDERS_FACTOR, cta.due_now(True, left), safe)


def test_with_it_ending_the_look_prices_the_life_it_will_have_after():
    safety = module.Safety()
    safety.orders = due_look(5.0, safe=True)  # due, and safe: no rebuff retreat, only the life after
    _, decision = priced('death-fane-walk', safety)
    life = snap('death-fane-walk')['player']['life']
    assert decision['life'] == pytest.approx(life / ORDERS_FACTOR, abs=1.0)
    safety = module.Safety()
    safety.orders = OrdersLook(True, 60.0, ORDERS_FACTOR, None, True)  # a minute left: the life of the moment
    _, decision = priced('death-fane-walk', safety)
    assert decision['life'] == pytest.approx(life, abs=1.0)


@pytest.mark.parametrize(
    ('name', 'reason', 'clear'),
    [
        ('death-fane-walk', p.REBUFF_SAID, module.REBUFF_CLEAR),
        # Every act vetoed there, the rebuff's too: the jump clearest of the hostiles, its landing the cast's
        ('death-fane-vetoed', f'retreating: {p.VETOED_AWAY}', ORDERS_CLEAR),
    ],
)
def test_due_and_not_safe_the_look_jumps_clear_of_every_hostile_to_cast_it(name: str, reason: str, clear: float):
    safety = module.Safety()
    safety.orders = due_look(5.0)
    act, _ = priced(name, safety)
    assert isinstance(act, p.Move)
    assert act.reason.startswith(reason)
    assert act.step.skill is not None
    assert min(math.dist(act.step.spot, at) for at in hostiles(snap(name))) >= clear
    assert math.isfinite(safety.rebuffed_at)  # its landing casts it (cta.py REBUFF_GRACE)
    assert safety.rebuff_hops[0] == 1


def test_with_the_switches_off_no_rebuff_retreat_is_priced(monkeypatch):
    monkeypatch.setattr(module, 'REBUFF_RETREAT', False)
    safety = module.Safety()
    safety.orders = due_look(5.0)
    act, _ = priced('death-fane-walk', safety)
    assert not (isinstance(act, p.Move) and act.reason.startswith(p.REBUFF_SAID))


# -- The auras --------------------------------------------------------------------------------------------------------


def test_an_aura_holder_s_state_words_name_its_aura():
    assert module.auras_of(words(33)) == (98,)  # might -> Might
    assert module.auras_of(words(28, 42, 44)) == (113, 123)  # the Fane Herald's: Concentration, Conviction
    assert module.auras_of(b'') == ()
    assert module.auras_of(None) == ()


def test_might_at_its_level_on_the_monsters_raises_the_physical_points_of_all_within_its_range():
    # Might 16 (the takes' stat 351 of the Fane's Might unique): +190% within 16 + 2 x 15 = 46
    holder = ((0.0, 0.0), (98,))
    assert module.raised((10.0, 0.0), (holder,)) == pytest.approx(2.9)
    assert module.raised((45.0, 0.0), (holder,)) == pytest.approx(2.9)
    assert module.raised((47.0, 0.0), (holder,)) == pytest.approx(1.0)
    # Two holders of Might count once; Concentration adds its own +285%
    assert module.raised((1.0, 0.0), (holder, ((2.0, 0.0), (98,)))) == pytest.approx(2.9)
    assert module.raised((1.0, 0.0), (holder, ((2.0, 0.0), (113,)))) == pytest.approx(1 + 1.9 + 2.85)
    assert module.raised((1.0, 0.0), (((0.0, 0.0), (123,)),)) == pytest.approx(1.0)  # Conviction: the resistances


def test_without_a_damagepercent_read_each_holder_s_aura_is_read_once_and_an_unread_one_is_none():
    m = Monster(MIGHT_UNIQUE, 47, 1, 5000.0, 5000.0, flags=8, life=100, max_life=128, modifiers=(9, 30, 6))
    near = Monster(5, NIGHT_LORD, 1, 5010.0, 5000.0, life=100, max_life=128)
    reads: list[int] = []

    def states_of(monster: Monster) -> bytes | None:
        reads.append(monster.unit_id)
        return words(33)

    safety = module.Safety()
    assert safety.aura_holders((m, near)) == ()  # no reader: no aura known
    safety.states_of = states_of
    assert safety.aura_holders((m, near)) == (((5000.0, 5000.0), (98,)),)
    assert safety.aura_holders((m, near)) == (((5000.0, 5000.0), (98,)),)
    assert reads == [MIGHT_UNIQUE]  # once a unit
    blank = module.Safety()
    blank.states_of = lambda _: words()
    assert blank.aura_holders((m,)) == ()  # read, none shown: none known


def test_where_the_look_reads_each_hostile_s_own_aura_that_one_alone_raises_it():
    # stats 350/351 (game/records.py `Monster.aura`): the Fane's Might unique's neighbours showed Might 16 at first
    # sight; a later curse shows in its place, and the aura seen is kept for the unit
    safety = module.Safety()
    under = Monster(5, NIGHT_LORD, 1, 5010.0, 5000.0, life=100, max_life=128, aura=(98, 16))
    assert safety.unit_raise(under) == pytest.approx(2.9)
    assert safety.unit_raise(replace(under, aura=(391, 20))) == pytest.approx(2.9)  # cursed since: kept
    assert safety.unit_raise(Monster(6, NIGHT_LORD, 1, 0.0, 0.0, aura=(123, 12))) == pytest.approx(1.0)  # Conviction
    assert safety.unit_raise(Monster(8, NIGHT_LORD, 1, 0.0, 0.0)) == pytest.approx(1.0)
    # Two damage auras seen on one unit add up, as the game's damagepercent does
    assert safety.unit_raise(replace(under, aura=(113, 16))) == pytest.approx(1 + 1.9 + 2.85)
    # The game's own sum read (stat 25): taken as it is
    assert safety.unit_raise(replace(under, damage_percent=475)) == pytest.approx(5.75)


def test_the_unique_night_lord_s_most_blow_beside_might_is_over_the_life_without_battle_orders():
    # Its table most (386 at its monstats level; the arena's terror zone 96: 452) x Might 2.9 x Amplify Damage 1.82
    # (physical resistance -82) + as much fire x 0.91 (fire 9 after Hell's 100)
    fane = Protection(resists=(('physical', -82.0), ('fire', 9.0)))
    hostile = Hostile(UNIQUE_NIGHT_LORD, NIGHT_LORD, (0.0, 0.0), 8, (7, 5, 9), raised=2.9)
    most = kind_of(NIGHT_LORD, None, 8, (7, 5, 9), 0)[1].damage[1]
    blow, _ = most_blow(hostile, fane)
    assert blow == pytest.approx(most * 2.9 * 1.82 + most * 0.91, rel=0.01)
    assert blow > 1896
    plain, _ = most_blow(replace(hostile, raised=1.0), fane)
    assert plain == pytest.approx(most * 2.73, rel=0.01)  # no aura: 1054 here, 1235 at level 96 (findings §2)
    assert most_blow(replace(hostile, level=96), fane)[0] == pytest.approx(452.35 * (2.9 * 1.82 + 0.91), rel=0.01)


# -- Reach, footing and the danger look -------------------------------------------------------------------------------


def test_a_move_ending_within_reach_of_blows_that_take_the_life_is_barred():
    found = snap('death-fane-walk')
    life = found['player']['life']
    safety = module.Safety()
    safety.states_of = lambda m: words(42) if m.unit_id == 4193434304 else words(33)  # the Herald's Concentration
    _, decision = priced('death-fane-walk', safety)
    barred = [c for c in decision['candidates'] if (c['veto'] or '').startswith(module.REACH_SAID)]
    assert barred, [c['veto'] for c in decision['candidates']]
    assert all(f'of {life}' in c['veto'] for c in barred)


def test_standing_within_reach_of_blows_that_take_the_life_is_no_fight_out():
    # death-fane-walk, 23:35:32.6: 1613 of 2943, the Cursed, Extra Strong, Fire Enchanted Night Lord minion 2.7 away
    # and the Herald's Flesh Hunters about; the take's next frames took 324 + 804, then the life
    act, decision = priced('death-fane-walk')
    holds = [c for c in decision['candidates'] if c['act'] == 'Hold']
    assert holds
    assert all((c['veto'] or '').startswith(module.REACH_SAID) for c in holds)
    assert not isinstance(act, p.Hold)


def test_with_the_reach_bar_off_no_move_is_barred_for_reach(monkeypatch):
    monkeypatch.setattr(module, 'REACH_BAR', False)
    safety = module.Safety()
    safety.states_of = lambda m: words(42) if m.unit_id == 4193434304 else words(33)
    _, decision = priced('death-fane-walk', safety)
    assert not [c for c in decision['candidates'] if (c['veto'] or '').startswith(module.REACH_SAID)]


def test_the_clear_places_asked_are_on_footing_only():
    here, hostiles_at = (0.0, 0.0), [(5.0, 0.0)]
    every = module.clearest(here, hostiles_at)
    assert every
    west = module.clearest(here, hostiles_at, lambda spot: spot[1] > 0)  # the south a wall
    assert west
    assert all(spot[1] > 0 for spot in west)
    assert module.clearest(here, hostiles_at, lambda spot: False) == []


def lapped(lap: float = 0.02):
    """A look's timer `lap` s a reading (fane_death.py `late_timer`): late at the fifth with `look_seconds` 0.08."""
    calls = [0]

    def timer() -> float:
        calls[0] += 1
        return calls[0] * lap

    return timer


def asked_places(name: str, monkeypatch, *, danger: bool, alarmed: bool = False) -> int:
    monkeypatch.setattr(module, 'DANGER_LOOK', danger)
    safety = module.Safety(timer=lapped())
    safety.alarmed = alarmed
    _, decision = priced(name, safety)
    return len(decision['candidates'])


def test_a_look_under_its_floor_or_just_after_a_rejuvenation_takes_the_danger_look_s_time(monkeypatch):
    # death-fane-walk: the life 1613 of 2943, under the 65% floor
    assert asked_places('death-fane-walk', monkeypatch, danger=True) > asked_places(
        'death-fane-walk', monkeypatch, danger=False
    )
    # herald-spiders-in-pack, over its budget (306): only a rejuvenation just drunk gives it the time
    calm = asked_places('herald-spiders-in-pack', monkeypatch, danger=True)
    assert asked_places('herald-spiders-in-pack', monkeypatch, danger=True, alarmed=True) > calm
    assert asked_places('herald-spiders-in-pack', monkeypatch, danger=False, alarmed=True) == calm


def test_the_emergency_rule_looks_the_life_read_s_lag_further_ahead(monkeypatch):
    # 52% now, 13% within the worst second: 1.5 s ahead 32.5% (over `danger` 30), 1.9 s ahead 27.3% (under)
    felt = Pressure(0.52, 0.3, 0.1, 0.13)
    supply = Supply(4, 4)
    monkeypatch.setattr(survival, 'READ_LAG', False)
    assert drink(felt, supply, {}, DrinkSettings()) != PotionType.REJUVENATION
    monkeypatch.setattr(survival, 'READ_LAG', True)
    assert drink(felt, supply, {}, DrinkSettings()) == PotionType.REJUVENATION


def test_with_every_fix_of_today_off_the_old_looks_price_as_before(monkeypatch):
    later(monkeypatch, False)
    safety = module.Safety()
    safety.orders = due_look(5.0)
    act, decision = priced('death-fane-walk', safety)
    life = snap('death-fane-walk')['player']['life']
    assert decision['life'] == pytest.approx(life, abs=1.0)
    assert not (isinstance(act, p.Move) and act.reason.startswith(p.REBUFF_SAID))
