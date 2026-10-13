"""Damage pricing contracts independent of the loop and its keys."""


def test_fire_passes_a_physical_guard_and_weapon_sets_change_the_price():
    from inventory_tracking.combat.harm import Hostile, Look, Protection, harm
    from inventory_tracking.combat.sim.guard import GuardRule

    guarded = Protection(resists=(('fire', 75.0),), guard=GuardRule(185, ('physical',)), pool=185)
    seen = Look((Hostile(1, 362, (8.0, 0.0)),), battle=guarded, travel=Protection())
    battle = harm(seen, (0.0, 0.0), 2.0, 'battle')
    travel = harm(seen, (0.0, 0.0), 2.0, 'travel')
    assert battle.mean > 0
    assert travel.mean > battle.mean * 2
    assert battle.worst >= battle.mean
    assert battle.by[0][0] == 1


def test_nearest_companion_and_awareness_change_exposure():
    from dataclasses import replace

    from inventory_tracking.combat.harm import Hostile, Look, harm

    seen = Look((Hostile(1, 310, (2.0, 0.0)),))
    alone = harm(seen, (0.0, 0.0), 1.0, 'battle')
    diverted = harm(replace(seen, companions=((2.0, 1.0),)), (0.0, 0.0), 1.0, 'battle')
    assert alone.mean > diverted.mean
    assert harm(seen, (100.0, 0.0), 1.0, 'battle').worst == 0
    assert harm(seen, (0.0, 0.0), 0.0, 'battle').worst == 0


def test_budget_is_life_above_floor_shrunk_by_pressure_never_future_healing():
    from inventory_tracking.combat.harm import SafetySettings, budget
    from inventory_tracking.combat.survival import CALM, Pressure

    settings = SafetySettings()
    assert budget(1000, 1000, CALM, settings) == 350
    assert budget(300, 1000, CALM, settings) == 0
    assert 0 < budget(1000, 1000, Pressure(1, 0.2, 0.2, 0.2), settings) < 350
    assert budget(1000, 1000, CALM, settings, insisting=100) <= 600


def test_rollout_veto_is_deterministic_and_independent_of_budget():
    from inventory_tracking.combat.harm import Hostile, Look, harm, veto

    seen = Look(tuple(Hostile(i, 362, (2.0, float(i % 3))) for i in range(20)), life=100)
    first = harm(seen, (0.0, 0.0), 2.0, 'travel')
    assert first == harm(seen, (0.0, 0.0), 2.0, 'travel')
    assert veto(first, seen.life) is not None


def test_unknown_boss_is_not_free_and_exploding_corpses_bar_a_close_stand():
    from inventory_tracking.combat.harm import Hostile, Look, harm, veto

    unknown = harm(Look((Hostile(1, 99999, (1.0, 0.0)),)), (0.0, 0.0), 1.0, 'battle')
    assert unknown.worst > 500
    doll = harm(Look((Hostile(2, 216, (2.0, 0.0)),)), (0.0, 0.0), 0.12, 'battle')
    assert veto(doll, 1783) is not None


def test_trajectory_shares_the_attack_clock_and_can_leave_a_forbidden_stand():
    from inventory_tracking.combat.harm import Hostile, Look, harm_path, veto

    seen = Look((Hostile(1, 362, (5.0, 0.0)),))
    split = harm_path(seen, (((0.0, 0.0), 0.2, 'battle'),) * 3)
    whole = harm_path(seen, (((0.0, 0.0), 0.6, 'battle'),))
    assert split.worst <= whole.worst * 1.2
    assert veto(split, 500) is None
    dolls = Look((Hostile(2, 216, (2.0, 0.0)),))
    escape = harm_path(dolls, (((0.0, 0.0), 0.12, 'battle'), ((25.0, 0.0), 0.36, 'battle')))
    assert escape.barred is None


def test_poison_event_identity_is_independent_of_path_slice_duration():
    from inventory_tracking.combat.harm import Hostile, Look, Protection, SafetySettings, exposure
    from inventory_tracking.combat.sim import casters

    # Use the same indexed family as the simulator rather than a guessed item/type code.
    from inventory_tracking.terror.danger import table

    txt = next(txt for txt in table().monsters if casters.mind_of(txt) == casters.OBLIVION_KNIGHT)
    seen = Look((Hostile(1, txt, (20.0, 0.0)),))
    whole, _, _ = exposure(seen, (0.0, 0.0), 1.5, Protection(), SafetySettings())
    part, _, _ = exposure(seen, (0.0, 0.0), 0.5, Protection(), SafetySettings())
    assert any(k == 'poison' for e in whole for k, _, _ in e.parts)
    assert [e.parts for e in whole] == [e.parts for e in part]


def test_the_characters_own_kills_end_a_hostiles_blows_and_the_rollouts_draw_their_pace():
    from inventory_tracking.combat.harm import Hostile, Look, SafetySettings, harm, veto

    pack = Look(tuple(Hostile(i, 310, (2.0, float(i % 3))) for i in range(8)), life=1500)
    alone = harm(pack, (0.0, 0.0), 1.5, 'battle')
    killed = harm(pack, (0.0, 0.0), 1.5, 'battle', deaths=dict.fromkeys(range(8), 0.36))
    # The measured spread (`strike_spread`: median 1.78 times the forecast, a tail to 20, 7.5% never) leaves a
    # share of the blows: credit, not a promise
    assert killed.mean < alone.mean * 0.75
    # A rollout may draw kills that never come (`strike_never`): the tail keeps more than the mean
    never = SafetySettings(strike_never=100.0)
    unkilled = harm(pack, (0.0, 0.0), 1.5, 'battle', never, dict.fromkeys(range(8), 0.36))
    assert abs(unkilled.mean - alone.mean) < alone.mean * 0.1  # the same blows, another draw of the rolls
    assert killed == harm(pack, (0.0, 0.0), 1.5, 'battle', deaths=dict.fromkeys(range(8), 0.36))  # deterministic
    assert veto(killed, pack.life) is None or veto(alone, pack.life) is not None


def test_a_guard_shown_up_stuns_its_melee_strikers_and_never_a_boss():
    from dataclasses import replace

    from inventory_tracking.combat.harm import Hostile, Look, Protection, harm
    from inventory_tracking.combat.sim.guard import GuardRule

    rule = GuardRule(185, ('physical',), stun=72)
    knights = tuple(Hostile(i, 310, (2.0, float(i))) for i in range(3))
    bare = Look(knights, battle=Protection(resists=(('fire', 75.0),)))
    guarded = replace(bare, battle=replace(bare.battle, guard=rule, pool=1e6))
    assert harm(guarded, (0.0, 0.0), 3.0, 'battle').mean < harm(bare, (0.0, 0.0), 3.0, 'battle').mean / 2
    boss = (Hostile(9, 243, (2.0, 0.0)),)  # monstats `boss` 1: never stunned (combat/sim/guard.py)
    no_pool = replace(guarded, hostiles=boss, battle=replace(guarded.battle, pool=0.0))
    assert (
        harm(no_pool, (0.0, 0.0), 3.0, 'battle').mean
        == harm(replace(bare, hostiles=boss), (0.0, 0.0), 3.0, 'battle').mean
    )


def test_an_unread_ordinary_type_is_priced_by_the_simulators_fit_and_an_unread_boss_conservatively():
    from inventory_tracking.combat.harm import Hostile, Look, harm

    # 311 Abyss Knight: an AI no rule of sim/casters.py reads, a type the threat table calls ranged.
    # River of Flame, 2026-10-13 21:11: 0 life lost in 106 s while the factor-3 stand-in priced each at 200+.
    knight = harm(Look((Hostile(1, 311, (10.0, 0.0), active=True),)), (0.0, 0.0), 0.72, 'battle')
    assert knight.mean < 20
    assert 311 in knight.stand_ins
    diablo = harm(Look((Hostile(2, 243, (2.0, 0.0), active=True),)), (0.0, 0.0), 0.72, 'battle')
    assert diablo.mean > 100
