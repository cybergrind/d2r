"""Mana-draining packs and the mana floor (combat/threats/manaburn.py; rca/2026-10-21/mana-burn-findings.md): the
numbers are the take's, 20261021T124558Z-25 (Tower Cellar Level 5, 15:46:06-33), a tier 5 Ghost Herald with Cold
Enchanted, Extra Fast and Mana Burn whose pack burnt 730 mana to 0 in 0.66 s."""

import csv
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from inventory_tracking.combat import pack
from inventory_tracking.combat.sim.monsters import REACH
from inventory_tracking.combat.threats import drain_escape as _drain_escape, manaburn


SKILLS = Path(__file__).parents[3] / 'pricing' / 'raw' / 'game-excel' / 'skills.txt'
GHOST = 38  # monstats wraith1
HERALD_MODS = (30, 18, 6, 25)  # the Herald 3599738168: aura, Cold Enchanted, Extra Fast, Mana Burn
MINION_MODS = (18, 6, 25)
UNIQUE, MINION = 0x08, 0x10


def hostile(unit: int, at: tuple[float, float], mods=MINION_MODS, flags=MINION, txt=GHOST) -> SimpleNamespace:
    return SimpleNamespace(unit=unit, at=at, txt=txt, modifiers=mods, flags=flags)


def test_teleport_costs_what_the_game_data_says() -> None:
    assert manaburn.TELEPORT_MANA == 24.0  # skills.txt 54 at level 1, the dearest
    assert manaburn.skill_mana(manaburn.TELEPORT_ROW, level=10) == 15.0
    assert manaburn.skill_mana(manaburn.TELEPORT_ROW, level=40) == 1.0  # minmana
    assert manaburn.RESERVE == 2 * 24.0 + manaburn.STRIKE_MANA
    if not SKILLS.exists():
        pytest.skip('the installed game tables are not here (pricing/raw is git-ignored)')
    with SKILLS.open(encoding='utf-8', errors='replace') as file:
        row = next(r for r in csv.DictReader(file, delimiter='\t') if r['*Id'] == '54')
    assert row['skill'] == 'Teleport'
    assert {k: int(row[k]) for k in manaburn.TELEPORT_ROW} == manaburn.TELEPORT_ROW


def test_the_extra_fast_ghosts_keep_range_is_the_players_18_about_their_reach_plus_a_steps_run() -> None:
    # The take's Extra Fast Ghosts ran 17.4-19.3 units a second; the plain ones 6.2
    assert 17.4 <= manaburn.pace(GHOST, MINION_MODS) <= 19.3
    keep = manaburn.keep_of(GHOST, HERALD_MODS)
    # The player's 18 under Extra Fast (2026-10-21 ~16:30): the Ghosts' reach plus a step's run, 18.3, rounded
    assert keep == manaburn.FAST_KEEP == 18.0
    assert REACH + manaburn.pace(GHOST, HERALD_MODS) * manaburn.STEP_SECONDS == pytest.approx(18.35, abs=0.01)
    assert keep >= pack.PACK_BACK + 8  # the 10-unit hops of 15:46:13.6-15.4 stayed inside it
    # A Mana Burn pack that is not Extra Fast: the Herald pack's 10 (H-B, 09:32:20, lost nothing at 8+)
    assert manaburn.keep_of(GHOST, (25,)) == pack.PACK_BACK
    assert manaburn.drains(HERALD_MODS)
    assert not manaburn.drains((18, 6))


def test_burners_are_the_draining_hostiles_and_the_switch_turns_them_off(monkeypatch) -> None:
    herald = hostile(1, (20.0, 0.0), HERALD_MODS, UNIQUE)
    found = manaburn.burners([herald, hostile(2, (21.0, 0.0)), hostile(3, (5.0, 0.0), (9,), 0)])
    assert [b.unit for b in found] == [1, 2]
    assert manaburn.key_of(found) == 1
    monkeypatch.setattr(manaburn, 'BURN_RANGE', False)
    monkeypatch.setattr(manaburn, 'FAST_RANGE', False)  # the Ghosts are Extra Fast too
    assert manaburn.burners([herald]) == []


def test_a_burner_within_its_keep_range_on_the_character_brings_the_hop_back_but_not_one_held_by_a_demon() -> None:
    here = (0.0, 0.0)
    coming = manaburn.burners([hostile(1, (15.7, 0.0), HERALD_MODS, UNIQUE), hostile(2, (19.3, 1.0))])
    why = manaburn.why_back(here, coming, [])
    assert why is not None
    assert why.startswith(manaburn.BURN_SAID)
    assert '(the nearest at 15.7)' in why
    # The pack on a demon 12 units off that stands apart from the character: it holds them (the player's tactic)
    held = manaburn.burners([hostile(1, (15.0, 0.0), HERALD_MODS, UNIQUE), hostile(2, (14.0, 2.0))])
    assert manaburn.why_back(here, held, [(13.0, 1.0)]) is None
    # Surrounded: out, on a demon or not
    around = manaburn.burners([hostile(u, (math.cos(u), math.sin(u))) for u in range(1, 4)])
    assert 'surrounded: 3' in (manaburn.why_back(here, around, [(1.0, 1.0)]) or '')
    assert manaburn.why_back(here, manaburn.burners([hostile(1, (25.0, 0.0))]), []) is None


def test_the_hop_lands_clear_of_every_burners_keep_range_and_away_from_the_pack() -> None:
    here = (0.0, 0.0)
    # On the character, as at 15:46:13.64: six within 5
    burning = manaburn.burners([hostile(u, (2.0 * math.cos(u), 2.0 * math.sin(u))) for u in range(6)])
    spots = manaburn.hop_spots(here, burning, [])
    assert spots
    assert all(manaburn.clear_of(spot, burning) for spot in spots)
    assert manaburn.clear_of(spots[0], burning, manaburn.HOP_CLEAR)
    # Coming in from the east, as at 15:46:12.10: the hop goes west, a hop's length, not a step
    coming = manaburn.burners([hostile(1, (15.7, 0.0), HERALD_MODS, UNIQUE), hostile(2, (19.0, 3.0))])
    first = manaburn.hop_spots(here, coming, [])[0]
    assert first[0] < -10.0
    assert math.dist(here, first) >= min(manaburn.HOP_LENGTHS)


def test_a_move_deeper_into_a_burners_keep_range_intrudes_and_one_out_of_it_does_not() -> None:
    here = (0.0, 0.0)
    burning = manaburn.burners([hostile(1, (18.0, 0.0), HERALD_MODS, UNIQUE)])
    # The take's "better place in the fight" at 15:46:12.23: a Teleport of 22 into the pack
    assert manaburn.intrudes(here, (12.0, -4.0), burning) is not None
    assert manaburn.intrudes(here, (-10.0, 0.0), burning) is None  # away
    assert manaburn.intrudes(here, (0.5, 10.0), burning) is None  # sideways, no nearer by INTRUDE_SLACK
    assert manaburn.intrudes((30.0, 0.0), (37.0, 0.0), burning) is None  # behind it, out of its range


def test_the_mana_floor_is_crossed_by_a_fast_fall_or_the_reserve_with_a_hostile_in_reach(monkeypatch) -> None:
    # The take: 730 at 13.42, 660 at 13.64, 644 at 13.85, 0 at 14.08
    history = [(13.42, 730.0), (13.64, 660.0), (13.85, 644.0)]
    assert manaburn.fell(history, 14.08, 0.0) == 730.0
    why = manaburn.mana_low(history, 14.08, 0.0, 740.0, 9)
    assert why is not None
    assert 'gone within' in why
    assert manaburn.mana_low(history, 13.85, 644.0, 740.0, 9) is None  # 86 of 740 in 0.43 s: not yet
    assert 'under the reserve' in (manaburn.mana_low([], 14.0, 40.0, 740.0, 1) or '')
    assert manaburn.mana_low(history, 14.08, 0.0, 740.0, 0) is None  # nothing in reach: the mana regenerates
    assert manaburn.fell([(10.0, 740.0)], 14.08, 100.0) == 0.0  # out of the window
    assert manaburn.mana_low([(10.0, 740.0)], 14.08, 100.0, 740.0, 9) is None  # above the reserve: a fight
    assert manaburn.mana_low([(10.0, 740.0)], 14.08, 60.0, 740.0, 9) is not None  # under it
    monkeypatch.setattr(manaburn, 'MANA_FLOOR', False)
    assert manaburn.mana_low(history, 14.08, 0.0, 740.0, 9) is None


def test_the_mana_is_read_from_the_stats_and_a_hostile_threatens_within_its_reach() -> None:
    assert manaburn.mana_of(((6, 744192), (8, 168960), (9, 189440))) == (660.0, 740.0)
    assert manaburn.mana_of(((6, 744192),)) is None
    here = (0.0, 0.0)
    near = [hostile(1, (17.0, 0.0), HERALD_MODS, UNIQUE), hostile(2, (17.0, 0.0), (9,), 0), hostile(3, (5.0, 0.0), ())]
    assert [m.unit for m in manaburn.threatened(here, near)] == [1, 3]


# -- the player's rulings of 2026-10-21 ~16:30: "Yes, 18 for Extra Fast"; "we can restore mana with rejuv potions, in a
# very scary moments, but make sure that we don't overuse it" --


def test_an_extra_fast_melee_pack_with_no_mana_burn_is_kept_at_18(monkeypatch) -> None:
    monkeypatch.setattr(manaburn, 'FAST_RANGE', True)
    here = (0.0, 0.0)
    hulk = 128  # thornhulk2, H-A's Bramble Hulks of 09:30:41 (mods 28, 8, 6)
    found = manaburn.burners(
        [
            hostile(1, (16.0, 0.0), (28, 8, 6), UNIQUE, hulk),
            hostile(2, (17.0, 0.0), (28, 8, 6), MINION, hulk),
            hostile(3, (5.0, 0.0), (6,), 0, hulk),  # a plain monster of a 'fast' Terror Zone: not a pack
            hostile(4, (5.0, 0.0), (6,), UNIQUE, 374),  # Extra Fast, not melee
        ]
    )
    assert [b.unit for b in found] == [1, 2]
    assert all(b.keep == manaburn.FAST_KEEP == 18.0 and not b.drains for b in found)
    why = manaburn.why_back(here, found, [])
    assert why is not None
    assert why.startswith(manaburn.FAST_SAID)
    monkeypatch.setattr(manaburn, 'FAST_RANGE', False)
    assert manaburn.burners([hostile(1, (16.0, 0.0), (28, 8, 6), UNIQUE, hulk)]) == []


# 15:46:14.32: mana 10 of 740 after the burn, 9 of the pack in reach, the leave a walk
BURNT = manaburn.ManaLook(10.0, 10.0, 740.0, 'mana 10 of 740, 99% gone within 1 s, 9 in reach', 9, 3599738168, False)


def mana_look(**changes) -> manaburn.ManaLook:
    return replace(BURNT, **changes)


def test_a_rejuvenation_for_mana_only_in_a_scary_moment_and_not_overused(monkeypatch) -> None:
    monkeypatch.setattr(manaburn, 'MANA_REJUVENATION', True)
    now, never = 10.1, math.inf
    why = manaburn.rejuvenation_for_mana(mana_look(), now, 4, never, ())
    assert why is not None
    assert 'no Teleport out' in why
    assert manaburn.rejuvenation_for_mana(mana_look(mana=40.0), now, 4, never, ()) is not None  # a walk out
    # Not a scary moment
    assert manaburn.rejuvenation_for_mana(mana_look(why=None), now, 4, never, ()) is None  # the mana well
    assert manaburn.rejuvenation_for_mana(mana_look(danger=0), now, 4, never, ()) is None  # no dangerous pack
    assert manaburn.rejuvenation_for_mana(mana_look(teleport_out=True), now, 4, never, ()) is None  # it can leave
    assert manaburn.rejuvenation_for_mana(mana_look(), now + 1.0, 4, never, ()) is None  # the look is stale
    # Not overused
    assert manaburn.rejuvenation_for_mana(mana_look(), now, 2, never, ()) is None  # the last 2 kept
    assert manaburn.rejuvenation_for_mana(mana_look(), now, 3, never, ()) is not None
    assert manaburn.rejuvenation_for_mana(mana_look(), now, 4, 19.0, ()) is None  # one 19 s ago
    assert manaburn.rejuvenation_for_mana(mana_look(), now, 4, never, (3599738168,)) is None  # one this pack
    monkeypatch.setattr(manaburn, 'MANA_REJUVENATION', False)
    assert manaburn.rejuvenation_for_mana(mana_look(), now, 4, never, ()) is None


def test_the_dangerous_in_reach_are_the_draining_and_the_tier_4_5_heralds_pack(monkeypatch) -> None:
    monkeypatch.setattr(_drain_escape, 'MANA_ESCAPE', False)  # the old path, pinned
    here = (0.0, 0.0)
    near = [
        SimpleNamespace(unit=1, at=(5.0, 0.0), txt=GHOST, modifiers=MINION_MODS, flags=MINION, tier=5),
        SimpleNamespace(unit=2, at=(2.0, 0.0), txt=GHOST, modifiers=(), flags=0, tier=0),  # plain
        SimpleNamespace(unit=3, at=(3.0, 0.0), txt=128, modifiers=(), flags=UNIQUE, tier=4),  # a T4 Herald
    ]
    assert manaburn.dangerous(here, near) == (2, 3)
    assert manaburn.dangerous(here, near[1:2]) == (0, None)


GLOAM = 118  # monstats willowisp1: Chain Lightning, a flier (the tier 5 Herald of 2026-10-21 18:35)
GLOAM_MODS = (18, 28, 5)  # the minions': Cold Enchanted, Stone Skin, Extra Strong (no Extra Fast, no Mana Burn)


def gloam(unit: int, at: tuple[float, float], tier: int = 5, flags: int = MINION) -> SimpleNamespace:
    return SimpleNamespace(unit=unit, at=at, txt=GLOAM, modifiers=GLOAM_MODS, flags=flags, tier=tier)


def test_a_tier_5_pack_of_ranged_elemental_casters_is_kept_at_18_and_a_plain_one_is_not(monkeypatch) -> None:
    assert manaburn.caster(GLOAM)  # threats.json: ranged, elemental 1.9 over physical 0
    assert not manaburn.caster(GHOST)
    found = manaburn.burners([gloam(1, (20.0, 0.0), flags=UNIQUE), gloam(2, (22.0, 0.0)), gloam(3, (9.0, 0.0), 0, 0)])
    assert [b.unit for b in found] == [1, 2]  # not the plain Gloam (no Herald tier, no pack flag)
    assert all(b.keep == manaburn.FAST_KEEP and not b.drains and b.kind == manaburn.CASTER_SAID for b in found)
    assert manaburn.said(found) == manaburn.CASTER_SAID
    assert manaburn.burners([gloam(4, (20.0, 0.0), tier=3)]) == []  # tier 3: the Herald tactic does not apply
    monkeypatch.setattr(manaburn, 'CASTER_RANGE', False)
    assert manaburn.burners([gloam(1, (20.0, 0.0), flags=UNIQUE)]) == []


def test_a_draining_member_names_the_hop_whatever_casters_stand_by() -> None:
    ghost = hostile(5, (12.0, 0.0), HERALD_MODS, UNIQUE)
    found = manaburn.burners([ghost, gloam(6, (20.0, 0.0))])
    assert manaburn.said(found) == manaburn.BURN_SAID
    assert manaburn.said([b for b in found if b.unit == 6]) == manaburn.CASTER_SAID


def member(unit: int, at: tuple[float, float], tier: int = 5, mode: int = 1, ally: bool = False) -> SimpleNamespace:
    return SimpleNamespace(unit_id=unit, x=at[0], y=at[1], tier=tier, mode=mode, ally=ally, owner=manaburn.NO_OWNER)


def test_a_live_herald_pack_in_sight_keeps_the_run_from_a_far_potion_while_rejuvenations_last(monkeypatch) -> None:
    here = (0.0, 0.0)
    pack_ = [member(1, (9.0, 0.0)), member(2, (25.0, 0.0)), member(3, (40.0, 0.0)), member(4, (5.0, 0.0), mode=12)]
    assert manaburn.herald_fight(here, pack_, 7) == 2  # the take's belt: 7 rejuvenations; the dead one not counted
    assert manaburn.herald_fight(here, pack_, manaburn.KEPT_REJUVENATIONS) == 0  # the last two are not the fight's
    assert manaburn.herald_fight(here, [member(5, (9.0, 0.0), tier=0)], 7) == 0
    assert manaburn.herald_fight(here, [member(6, (9.0, 0.0), ally=True)], 7) == 0
    monkeypatch.setattr(manaburn, 'STAY_IN_HERALD_FIGHT', False)
    assert manaburn.herald_fight(here, pack_, 7) == 0


# -- a tier 4-5 Herald pack is not landed in (manaburn.PACK_LANDING; take 20261021T172936Z-84, Arachnid Lair, the
# player, 2026-10-21 ~20:34: "we had a quite bad positioning and suffered alot of damage") --


def held_at(unit: int, at: tuple[float, float], tier: int = 5) -> SimpleNamespace:
    return SimpleNamespace(unit=unit, at=at, tier=tier)


def test_a_move_into_a_herald_packs_back_range_or_onto_a_pending_omen_is_named_and_one_away_is_not(
    herald2_on,
    monkeypatch,
) -> None:
    pack_ = [held_at(7, (20.0, 0.0)), held_at(8, (40.0, 0.0), tier=0)]
    assert manaburn.pack_landing((0.0, 0.0), (14.0, 0.0), pack_) == 7  # 6 from the member, 14 nearer
    assert manaburn.pack_landing((0.0, 0.0), (-5.0, 0.0), pack_) is None  # away
    assert manaburn.pack_landing((14.0, 0.0), (14.0, 3.0), pack_) is None  # about as near as before: a side step
    assert manaburn.pack_landing((0.0, 0.0), (36.0, 0.0), [held_at(8, (40.0, 0.0), tier=0)]) is None  # no Herald's
    omen = (7511.5, 5058.5)  # 20:31:17.14: the Teleport from (7513.5, 5069.5) to (7517.9, 5055.4), 7.1 from it
    assert manaburn.pack_landing((7513.5, 5069.5), (7517.9, 5055.4), (), [omen]) == manaburn.OMEN_LANDED
    assert manaburn.pack_landing((7513.5, 5069.5), (7513.5, 5079.5), (), [omen]) is None
    monkeypatch.setattr(manaburn, 'PACK_LANDING', False)
    assert manaburn.pack_landing((0.0, 0.0), (14.0, 0.0), pack_) is None
    assert manaburn.pack_landing((7513.5, 5069.5), (7517.9, 5055.4), (), [omen]) is None


# -- the keep range only under a threat (manaburn.THREAT_GATE; the coordinator, 2026-10-21 ~21:20, the player: "there
# were EASY heralds", "we were FULL health and full potions") --


def kept(unit: int, at: tuple[float, float], drains: bool = False) -> manaburn.Burner:
    kind = manaburn.BURN_SAID if drains else manaburn.CASTER_SAID
    return manaburn.Burner(unit, at, manaburn.FAST_KEEP, drains=drains, kind=kind)


def test_a_pack_is_kept_at_range_only_under_a_threat_and_never_for_a_leftover(monkeypatch) -> None:
    here = (0.0, 0.0)
    casters = [kept(1, (12.0, 0.0)), kept(2, (14.0, 2.0))]
    hostiles = [SimpleNamespace(unit=1, life=1.0), SimpleNamespace(unit=2, life=0.08)]  # 2: a leftover at 11/128
    asked: list = []

    def priced(found: list, place: tuple[float, float]) -> float:
        asked.append(place)
        return 50.0  # 50 of 2900 in THREAT_SECONDS: an easy pack

    assert manaburn.threatening(here, hostiles, casters, priced, 2900.0) == []  # full life, nothing lost
    assert asked == [here]  # within the keep range: priced where the character stands
    assert manaburn.threatening(here, hostiles, casters, priced, 2900.0, felt=0.12) == casters[:1]  # life lost
    assert manaburn.threatening(here, hostiles, casters, priced, 2000.0, whole=0.7) == casters[:1]  # hurt
    assert manaburn.threatening(here, hostiles, casters, lambda f, p: 400.0, 2900.0) == casters[:1]  # priced high
    far = [kept(1, (40.0, 0.0))]
    asked.clear()
    manaburn.threatening(here, hostiles, far, priced, 2900.0)
    assert math.dist(asked[0], (40.0, 0.0)) == pytest.approx(manaburn.FAST_KEEP)  # priced at its keep range
    burner = [kept(3, (12.0, 0.0), drains=True)]
    assert manaburn.threatening(here, [SimpleNamespace(unit=3, life=1.0)], burner, priced, 2900.0) == burner
    monkeypatch.setattr(manaburn, 'THREAT_GATE', False)
    assert manaburn.threatening(here, hostiles, casters, priced, 2900.0) == casters


def test_a_pool_that_shrinks_is_no_burn_and_a_burn_under_the_same_pool_still_is(monkeypatch) -> None:
    # 20:30:32 (take 20261021T172936Z-84): the most mana 740 -> 526, the mana 740 -> 511 within a second
    shrank = [(31.2, 740.0, 740.0), (31.6, 740.0, 740.0), (31.9, 526.0, 526.0)]
    assert manaburn.fell(shrank, 32.0, 511.0, 526.0) == 15.0
    assert manaburn.mana_low(shrank, 32.0, 511.0, 526.0, 3) is None
    assert not manaburn.burnt(shrank, 32.0, 511.0, 526.0)
    burnt = [(31.2, 740.0, 740.0), (31.6, 600.0, 740.0)]  # 15:46:13-14's burn, the pool the same
    assert manaburn.burnt(burnt, 32.0, 10.0, 740.0)
    monkeypatch.setattr(manaburn, 'SAME_MOST', False)
    assert manaburn.mana_low(shrank, 32.0, 511.0, 526.0, 3) is not None  # as played: "43% gone within 1 s"


def test_a_draining_member_with_the_mana_safe_is_kept_only_in_a_herald_pack_or_extra_fast(monkeypatch) -> None:
    here = (0.0, 0.0)
    burner = [kept(3, (12.0, 0.0), drains=True)]

    def hostile(tier: int = 0, mods: tuple[int, ...] = (manaburn.MANA_BURN,)) -> list:
        return [SimpleNamespace(unit=3, life=1.0, tier=tier, modifiers=mods)]

    def priced(found: list, place: tuple[float, float]) -> float:
        return 0.0

    assert manaburn.threatening(here, hostile(), burner, priced, 2900.0, mana_safe=True) == []  # the Dark Ones
    assert manaburn.threatening(here, hostile(), burner, priced, 2900.0, mana_safe=False) == burner  # mana low/burnt
    assert manaburn.threatening(here, hostile(tier=5), burner, priced, 2900.0, mana_safe=True) == burner  # a Herald's
    fast = hostile(mods=(manaburn.MANA_BURN, manaburn.EXTRA_FAST))
    # MANA_BUDGET (2026-10-22, the Lower Kurast buzzards): an Extra Fast drainer outside a Herald's pack is priced
    assert manaburn.threatening(here, fast, burner, priced, 2900.0, mana_safe=True) == []  # priced at nothing
    assert manaburn.threatening(here, fast, burner, lambda f, p: 400.0, 2900.0, mana_safe=True) == burner  # a threat
    assert manaburn.threatening(here, fast, burner, lambda f, p: 50.0, 2900.0, mana_safe=True, spare=40.0) == burner
    assert manaburn.threatening(here, hostile(tier=5, mods=fast[0].modifiers), burner, priced, 2900.0, mana_safe=True)
    monkeypatch.setattr(manaburn, 'MANA_BUDGET', False)
    assert manaburn.threatening(here, fast, burner, priced, 2900.0, mana_safe=True) == burner  # the Ghosts of 15:46
    monkeypatch.setattr(manaburn, 'DRAIN_GATE', False)
    assert manaburn.threatening(here, hostile(), burner, priced, 2900.0, mana_safe=True) == burner


# -- BURN_STALL_COMMIT (2026-10-24, rca/2026-10-24/manaburn-cycle-findings.md §1): the Sand Warriors of take
# 20261024T132953Z-63 (monstats 92 scarab2, Extra Fast and Mana Burn, tier 5) --

SAND_WARRIOR = 92
EXTRA_FAST_BURN = (20, 27, 6, 25)


def test_a_mana_burn_pack_of_no_drainer_type_may_be_fought_in_and_a_ghost_about_forbids_it() -> None:
    warriors = [
        hostile(1, (0.0, 20.0), EXTRA_FAST_BURN, 8, SAND_WARRIOR),
        hostile(2, (3.0, 21.0), EXTRA_FAST_BURN, 16, SAND_WARRIOR),
    ]
    burning = manaburn.burners(warriors)
    assert {b.kind for b in burning} == {manaburn.BURN_SAID}
    assert manaburn.committable((0.0, 0.0), burning, warriors)
    ghost = hostile(3, (5.0, 5.0), (), 0, GHOST)  # wraith1: 200-300 mana a blow by its own row
    assert not manaburn.committable((0.0, 0.0), burning, [*warriors, ghost])
    assert not manaburn.committable((0.0, 0.0), [], warriors)


def test_a_committed_pack_keeps_only_its_landing_only_drainers_and_another_pack_is_kept() -> None:
    warriors = [
        hostile(1, (0.0, 20.0), EXTRA_FAST_BURN, 8, SAND_WARRIOR),
        hostile(2, (3.0, 21.0), EXTRA_FAST_BURN, 16, SAND_WARRIOR),
    ]
    burning = manaburn.burners(warriors)
    plain = manaburn.Burner(9, (30.0, 0.0), 18.0, kind=manaburn.LANDING_ONLY)
    key = manaburn.key_of(burning)
    assert key is not None
    assert manaburn.committed([*burning, plain], key) == [plain]
    assert manaburn.committed(burning, key + 1) == burning
    assert manaburn.committed(burning, None) == burning
