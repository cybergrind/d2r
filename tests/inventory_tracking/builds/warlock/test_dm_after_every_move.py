"""R1, the mark after every move in a hard fight (2026-10-24, rca/2026-10-24/dm-latency-findings.md §10): combat/pack.py
`hard_fight` and DM_AFTER_EVERY_MOVE, builds/warlock/mark.py `move_reason` / `move_target`, replayed on take
20261024T171736Z-71's frames (20:18:41.615: a Blade Warp of 15 put both demons 0.1 off the character, idle, with a
tier 5 Herald pack 11.6-23 off and the last Death Mark key 1.45 s before, on 2144188474), and macros/travel.py
JUMP_LANDING_UNPRICED (the same Blade Warp's landing taken for "did not move" at 20:18:41.312)."""

import math
from dataclasses import replace
from types import SimpleNamespace

import pytest

from inventory_tracking.builds.warlock import mark
from inventory_tracking.builds.warlock.skills import DEATH_MARK
from inventory_tracking.combat import pack
from inventory_tracking.game.records import Monster
from inventory_tracking.macros.build import BuffFacts, DrawPrice


PLAYER = 809342382
NOBODY = 0xFFFFFFFF
REACH = 22.08  # echoing_strike REACH


def monster(unit, txt, x, y, flags, tier, life, *, mode=1, ally=False, mods=()):
    return Monster(
        unit, txt, mode, x, y, NOBODY, flags, ally=ally, life=life, max_life=128, tier=tier, modifiers=tuple(mods)
    )


# Take 20261024T171736Z-71, the frame at 20:18:41.615 (the live hostiles within 32; the character landed at
# (22621.55, 12692.63) by the Blade Warp keyed at 40.876, the move "did not move" at 41.312)
HERE = (22621.55, 12692.63)
FOES = (
    monster(3019681667, 3, 22609.92, 12712.95, 16, 5, 38, mode=2),
    monster(1072086045, 3, 22612.5, 12709.5, 16, 5, 18, mode=4),
    monster(2144188474, 3, 22616.5, 12706.78, 16, 5, 37, mode=4),  # marked 1.45 s before
    monster(256883134, 3, 22606.5, 12702.5, 16, 5, 6, mode=5),
    monster(713889227, 187, 22597.1, 12705.58, 0, 0, 128, mode=2),
    monster(128433375, 3, 22617.5, 12704.5, 16, 5, 13),
    monster(3744964841, 3, 22612.5, 12703.5, 8, 5, 92, mode=5),  # the Herald (unique, tier 5), 14.1 off
    monster(2480127599, 3, 22615.5, 12702.5, 16, 5, 13),
    monster(1027581688, 3, 22615.5, 12705.5, 16, 5, 3, mode=3),
)
IMPACT = 0.65  # seconds from the warp's key to its move (take -71: key 40.876, the move at 41.53)
DEMONS = (
    monster(1000251762, 744, 22621.5, 12692.5, 0, 0, 127, mode=8, ally=True),  # the War Defiler, 0.1 off
    monster(1231039863, 189, 22621.5, 12692.5, 8, 0, 125, ally=True),  # the bound demon, 0.1 off
)
NOW = 1000.0
LAST_KEY = 1.45  # seconds since the Death Mark key on 2144188474 (40.165)


def facts_of(monkeypatch, *, foes=FOES, demons=DEMONS, last=LAST_KEY, hop_ago=None, hop=15.0, draws=None):
    """The look at 41.615: `hop_ago` s since a jump of `hop` landed (None: the warp unregistered, the last hop long
    before, as live); the mark's last key `last` s before, on 2144188474."""
    player = SimpleNamespace(unit_id=PLAYER, x=HERE[0], y=HERE[1], area=71, mode=1)
    world = SimpleNamespace(player=player, monsters=foes + demons, slots={DEATH_MARK: 'd'})
    reachable = tuple(m for m in foes if math.dist(HERE, (m.x, m.y)) <= REACH)
    cast_at = {(DEATH_MARK, 2144188474): NOW - last, (DEATH_MARK, None): NOW - last}
    monkeypatch.setattr(pack.HOP, 'at', NOW - (hop_ago if hop_ago is not None else 30.0))
    monkeypatch.setattr(pack.HOP, 'units', hop)
    monkeypatch.setattr(mark.DESIGNATION, 'unit', 2144188474)
    monkeypatch.setattr(mark.DESIGNATION, 'reason', "the tier 5 Herald pack's member (the pack's order)")
    monkeypatch.setattr(mark.DESIGNATION, 'rank', mark.PACK_RANK)
    return BuffFacts(world=world, now=NOW, foes=foes, reachable=reachable, cast_at=cast_at, draws=draws)  # type: ignore[arg-type]


def trash(foes):
    """The same bodies as a regular fight: no tier, no elite flags."""
    return tuple(replace(m, flags=0, tier=0) for m in foes)


# -- hard_fight: each side --


def test_a_tier_5_herald_pack_member_within_reach_of_the_look_is_a_hard_fight():
    assert pack.hard_fight(HERE, FOES) == 'a tier 5 Herald pack'
    far = tuple(replace(m, x=m.x + 60.0) for m in FOES)  # 37-58 off: beyond HARD_SEEN
    assert pack.hard_fight(HERE, trash(FOES) + far) is None


def test_a_tier_4_pack_alone_is_no_hard_fight_by_its_tier():
    assert pack.hard_fight(HERE, tuple(replace(m, tier=4, flags=0) for m in FOES)) is None


def test_a_boss_or_a_super_unique_is_a_hard_fight():
    from inventory_tracking.terror.bosses import BOSSES, SUPER_UNIQUE_FLAG

    boss = monster(1, next(iter(BOSSES)), HERE[0] + 10, HERE[1], 0, 0, 128)
    assert pack.hard_fight(HERE, (*trash(FOES), boss)) == 'a boss'
    pindle = monster(2, 440, HERE[0] + 10, HERE[1], SUPER_UNIQUE_FLAG, 0, 128)
    assert pack.hard_fight(HERE, (pindle,)) == 'a boss'


def test_holding_over_the_safety_s_life_budget_is_a_hard_fight():
    assert pack.hard_fight(HERE, trash(FOES), pressed=True) == "holding is over the safety's life budget"
    assert pack.hard_fight(HERE, trash(FOES), pressed=False) is None


def test_a_mana_burner_is_a_hard_fight():
    from inventory_tracking.combat.threats import manaburn

    burner = replace(trash(FOES)[0], modifiers=(min(manaburn.DRAINING),))
    assert manaburn.drains(burner.modifiers)
    assert pack.hard_fight(HERE, (burner, *trash(FOES)[1:])) == 'a hostile that drains mana'


def test_eight_of_an_elite_pack_is_a_hard_fight_seven_and_any_plain_crowd_are_not():
    elite = tuple(replace(m, tier=0) for m in FOES[:8])  # flags kept: minions and the unique
    assert sum(1 for m in elite if m.flags) == 7
    assert pack.hard_fight(HERE, elite) is None
    eighth = replace(FOES[0], unit_id=9, tier=0)
    assert pack.hard_fight(HERE, (*elite, eighth)) == '8 of an elite pack'
    crowd = tuple(replace(trash(FOES)[0], unit_id=100 + i) for i in range(40))  # a Hell cow field, say
    assert pack.hard_fight(HERE, crowd) is None


# -- R1 on the take's frame --


@pytest.mark.parametrize('on', [False, True])
def test_the_demons_idle_by_the_character_after_the_warp_have_the_mark_out(monkeypatch, on):
    # Live (off): no mark until 42.675, 1.06 s after the demons stood 0.1 off, the mark lasting on 2144188474 holding
    # the pack's order back; on: at once, on the one the pack's order picks as if nothing were marked (2144188474
    # again: a recast on a cursed monster sends the demons, the stopwatch's 125 of 146 such stands, 2026-10-24)
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', on)
    facts = facts_of(monkeypatch)
    assert [d.unit_id for d in mark.pets_with_us(facts.world, facts.foes)] == [1000251762, 1231039863]
    chosen = mark.target(facts)
    if not on:
        assert mark.move_reason(facts) is None
        assert chosen is None
        assert not mark.mark_ahead(facts)
        return
    assert mark.move_reason(facts) == mark.PETS_SAID
    assert chosen is not None
    assert chosen.unit_id == 2144188474
    assert mark.mark_ahead(facts)
    assert mark.worth_a_mark(facts, chosen)
    assert mark.DESIGNATION.rank == mark.MOVE_RANK


def test_an_unowned_ally_is_no_demon_of_r1_s(monkeypatch):
    # The Bloody Foothills' barbarians (monstats 522/523, ally-flagged, no owner; "bound Act 5 Combatant" in the log,
    # rca/2026-10-24/engorge-findings.md) standing by the character are no idle demon, and alone no reason for a mark
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    barbarians = tuple(
        monster(9000 + i, txt, HERE[0] + 1.0, HERE[1], 0, 0, 128, ally=True) for i, txt in enumerate((522, 523))
    )
    facts = facts_of(monkeypatch, demons=DEMONS + barbarians)
    assert [d.unit_id for d in mark.pets_with_us(facts.world, facts.foes)] == [1000251762, 1231039863]
    alone = facts_of(monkeypatch, demons=barbarians)
    assert mark.pets_with_us(alone.world, alone.foes) == []
    assert mark.move_reason(alone) is None


def test_the_warp_s_landing_has_the_mark_out_before_the_demons_are_asked(monkeypatch):
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    facts = facts_of(monkeypatch, last=1.45, hop_ago=0.09)  # landed at 41.53, the key 1.45 s before it
    assert mark.move_reason(facts) == mark.MOVE_SAID
    facts = facts_of(monkeypatch, last=0.30, hop_ago=0.09, demons=())
    assert mark.move_reason(facts) is None  # no demon out: nothing to send


def test_the_mark_after_a_move_goes_out_once_a_move(monkeypatch):
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    # keyed 0.2 s after the landing (0.5 s ago): the move is answered, and the demons get PETS_AGAIN to leave
    facts = facts_of(monkeypatch, last=0.3, hop_ago=0.5)
    assert mark.move_reason(facts) is None
    assert mark.target(facts) is None or mark.DESIGNATION.rank != mark.MOVE_RANK
    # still by the character PETS_AGAIN after the key: again
    facts = facts_of(monkeypatch, last=mark.PETS_AGAIN, hop_ago=2.0)
    assert mark.move_reason(facts) == mark.PETS_SAID


def test_a_short_hop_takes_no_demon_off_and_is_no_move(monkeypatch):
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    far = tuple(replace(d, x=d.x - 8.0) for d in DEMONS)  # the demons off the character: only the hop could ask
    facts = facts_of(monkeypatch, demons=far, hop_ago=0.1, hop=mark.REMARK_HOP - 0.5)
    assert mark.move_reason(facts) is None


def test_demons_by_the_character_with_a_hostile_on_them_strike_it_and_are_not_idle(monkeypatch):
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    on_us = replace(FOES[0], x=HERE[0] + 1.5, y=HERE[1])  # a member 1.5 off the character and the demons
    facts = facts_of(monkeypatch, foes=(on_us, *FOES[1:]))
    assert mark.pets_with_us(facts.world, facts.foes) == []
    assert mark.move_reason(facts) is None


def test_a_regular_fight_keeps_the_mark_s_own_rules(monkeypatch):
    # The player, ~20:27: "we don't need to cast DM like every second for regular enemies"
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    facts = facts_of(monkeypatch, foes=trash(FOES), hop_ago=0.09)
    assert mark.move_reason(facts) is None
    # ... unless the safety prices holding over its life budget
    pressed = {FOES[0].unit_id: DrawPrice(FOES[0].unit_id, -10.0, 1.0, 0.0, 0.37, 5.0, pressed=True)}
    facts = facts_of(monkeypatch, foes=trash(FOES), hop_ago=0.09, draws=pressed)
    assert mark.move_reason(facts) == mark.MOVE_SAID


def test_the_move_s_target_is_the_pack_s_order_as_if_unmarked_and_skips_one_the_keys_took_nowhere_on(monkeypatch):
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    facts = facts_of(monkeypatch)
    assert mark.rules_target(facts) is None  # live: the lasting mark held the pack's order back
    first = mark.move_target(facts)
    assert first is not None
    assert first.unit_id == 2144188474
    missed = {(DEATH_MARK, 2144188474): mark.MARK_RECASTS}
    facts = replace(facts, missed=missed)
    chosen = mark.move_target(facts)
    assert chosen is not None
    assert chosen.unit_id != 3744964841
    assert chosen.tier == 5


# -- JUMP_LANDING_UNPRICED: the warp's landing judged after its own delay --


@pytest.mark.parametrize('on', [False, True])
def test_a_blade_warp_landing_after_the_priced_bound_is_a_landing(monkeypatch, on):
    from inventory_tracking.builds import pursuing
    from inventory_tracking.builds.warlock.skills import BLADE_WARP
    from inventory_tracking.macros import travel as travel_module
    from inventory_tracking.macros.actuator import Abort
    from inventory_tracking.macros.travel import Step
    from tests.inventory_tracking.macros.test_hunt import ASPECT, game, hunter, keys

    monkeypatch.setattr(travel_module, 'JUMP_LANDING_UNPRICED', on)
    real = travel_module.press_skill
    keyed = {}

    def play_once(bound: float):
        play = game()
        play.warp_lands = False  # the blade's impact moves the character IMPACT s after the key
        hunt = hunter(play)
        hunt.build = pursuing(hunt.build)
        run = play.run()

        def land():
            stand = play.world.player
            assert stand is not None
            play.world = replace(play.world, player=replace(stand, x=5015.0, y=5000.0))

        def press(run_, skill):
            done = real(run_, skill)
            keyed['at'] = run_.clock()
            play.later(IMPACT, land)
            return done

        monkeypatch.setattr(travel_module, 'press_skill', press)
        began = run.clock()
        with hunt.priced_for(run, bound):
            hunt.travel.jump(run, Step((5015.0, 5000.0), BLADE_WARP), play.world.player, ASPECT, keys)
        return hunt, run, began

    # The bound as live: past the key, before the impact (40.876 key, 41.312 bound, 41.53 move): the key's own time
    # in this game first, unbounded
    monkeypatch.setattr(pack.HOP, 'at', -math.inf)
    hunt, run, began = play_once(10.0)
    bound = keyed['at'] - began + 0.2
    monkeypatch.setattr(pack.HOP, 'at', -math.inf)
    if not on:
        with pytest.raises(Abort, match='Blade Warp: the character did not move'):
            play_once(bound)
        assert pack.HOP.at == -math.inf
        return
    hunt, run, began = play_once(bound)
    assert pack.HOP.at > began + bound  # the landing seen and `hopped`, after the bound
    assert hunt.travel.jump_failed == {}
    with hunt.priced_for(run, 0.01):
        run.pace.sleep(0.05)
        with pytest.raises(Abort, match='priced act expired'):
            run.world()  # the bound itself still holds at the next look outside a flight


# -- R2, MARK_THEN_WALK: the mark from where the character stands, then the walk in --

FAR = tuple(replace(m, x=m.x - 4.0, y=m.y + 10.0) for m in FOES)  # the take's pack 22.3-36.6 off: beyond the strike


def walker(*, foes=FAR, keyed=None, budget=500.0, worst=100.0, cast=True, pressed=False):
    """A stand-in Hunter for `walk_in` at the take's place: its foes, the safety's last look (a Hold priced `worst`
    against `budget`), the mark's last key `keyed` s before (None: never), and what `mark_from_here` did."""
    from inventory_tracking.macros.build import Step

    now = NOW
    calls = []
    draws = {foes[0].unit_id: DrawPrice(foes[0].unit_id, -1.0, 1.0, 0.0, 0.37, 5.0, pressed=pressed)}
    player = SimpleNamespace(unit_id=PLAYER, x=HERE[0], y=HERE[1], area=71, mode=1)
    world = SimpleNamespace(player=player, monsters=foes + DEMONS, doors=())
    cast_at = {} if keyed is None else {(DEATH_MARK, None): now - keyed}
    hunter = SimpleNamespace(
        foes=lambda world, now: list(foes),
        safety=SimpleNamespace(
            draws=draws, decision={'budget': budget, 'candidates': [{'act': 'Hold', 'worst': worst}]}
        ),
        attack=SimpleNamespace(reach=REACH),
        buffs=SimpleNamespace(cast_at=cast_at),
        travel=SimpleNamespace(
            options=lambda *a: (Step((HERE[0] - 5, HERE[1] + 3), 390), Step((HERE[0] - 4, HERE[1] + 2)))
        ),
        mark_from_here=lambda run, world, foes, key_names: calls.append('mark') or cast,
    )
    run = SimpleNamespace(clock=lambda: now)
    return hunter, run, world, calls


def walk(monkeypatch, **kw):
    from inventory_tracking.levels.model import Ground
    from inventory_tracking.macros.build import Step
    from inventory_tracking.macros.hunting import moves

    monkeypatch.setattr(pack, 'MARK_THEN_WALK', True)
    hunter, run, world, calls = walker(**kw)
    jump = Step((HERE[0] - 15, HERE[1] + 9), 390)
    # stand-ins for the Hunter, the run, the world and the intent (`walker`): walk_in asks them for no more
    out = moves.walk_in(hunter, run, world, Ground(()), jump, jump.spot, 1.8, {}, None)  # pyrefly: ignore[bad-argument-type]
    return jump, out, calls


def test_r2_big_group_is_a_hard_fight_with_six_or_more_near():
    assert pack.big_group(HERE, FOES) == 'a tier 5 Herald pack, 9 near'
    assert pack.big_group(HERE, FOES[:5]) is None  # five: no big group
    assert pack.big_group(HERE, trash(FOES)) is None  # nine of a regular fight


def test_r2_with_no_mark_out_the_mark_goes_first_from_here(monkeypatch):
    _jump, out, calls = walk(monkeypatch)
    assert out is None
    assert calls == ['mark']


def test_r2_while_the_demons_hold_the_approach_is_walked(monkeypatch):
    _jump, out, calls = walk(monkeypatch, keyed=1.0)
    assert out is not None
    assert out.skill is None
    assert calls == []
    _jump, out, calls = walk(monkeypatch, keyed=pack.WALK_HOLD + 0.5)  # the hold over: the mark again first
    assert out is None


def test_r2_standing_over_the_budget_jumps_as_priced(monkeypatch):
    jump, out, calls = walk(monkeypatch, worst=900.0)
    assert out == jump
    assert calls == []


def test_r2_leaves_a_regular_group_and_a_pack_in_reach_alone(monkeypatch):
    jump, out, calls = walk(monkeypatch, foes=trash(FAR))
    assert out == jump
    jump, out, calls = walk(monkeypatch, foes=FOES)  # members within the strike's reach: no approach
    assert out == jump
    assert calls == []


def test_r2_the_ask_has_the_mark_rules_give_the_move_s_target(monkeypatch):
    monkeypatch.setattr(pack, 'MARK_THEN_WALK', True)
    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', False)
    far = tuple(replace(d, x=d.x - 9.0) for d in DEMONS)  # no demon by the character: only the ask can say
    facts = facts_of(monkeypatch, demons=far, last=5.0)
    assert mark.move_reason(facts) is None
    pack.ask_mark(NOW)
    try:
        assert mark.move_reason(facts) == pack.WALK_SAID
        chosen = mark.target(facts)
        assert chosen is not None
        assert chosen.unit_id == 2144188474
    finally:
        pack.ASKED.at = -math.inf


@pytest.mark.parametrize('no_burn', [False, True])
def test_r1_holds_off_in_a_mana_burn_fight_with_dm_move_no_burn(monkeypatch, no_burn):
    # DM_MOVE_NO_BURN (gate R2: R1 in the manaburn scene 3 -> 6 deaths): a Mana Burn member in the take's pack
    from inventory_tracking.combat.threats import manaburn

    monkeypatch.setattr(pack, 'DM_AFTER_EVERY_MOVE', True)
    monkeypatch.setattr(pack, 'DM_MOVE_NO_BURN', no_burn)
    burner = replace(FOES[0], modifiers=(min(manaburn.DRAINING),))
    assert pack.burning(HERE, (burner,))
    assert not pack.burning(HERE, FOES)
    facts = facts_of(monkeypatch, foes=(burner, *FOES[1:]))
    assert (mark.move_reason(facts) is None) == no_burn
    assert mark.move_reason(facts_of(monkeypatch)) == mark.PETS_SAID  # no burner: R1 as before
