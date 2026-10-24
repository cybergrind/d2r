"""A tier 5 Bramble Hulk Herald's pack played in the arena with its three rules (herald.py; rca/2026-10-21/
herald-fight-findings.md §3.4, §7): the player's tactic of 2026-10-21 ~09:40 ("death mark nearest mob in group in
direct sight / sigil of lethargy to slow whole group / keep them busy with a daemon ... keep group on our daemon, not
ourselves or merc"). The findings' strict requirements are here, passing where the play meets them and strict xfail
where it does not yet; the sigil's cover (combat/pack.py SIGIL_COVER) and the demons kept out (REBIND_DEMON,
PETS_BETWEEN) are measured against their switches off, on the same seeds. Bind Demon is the player's since 2026-10-21
~16:30 (builds/warlock/bind.py BIND_DEMON_CASTS): the rebind plays show the macro casts none."""

import functools
import math
import statistics
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from inventory_tracking.combat import pack
from tests.inventory_tracking.scenarios.arena.situations.herald import (
    Measures,
    longest,
    measures,
    sampled,
    summons_between,
    t5_hulks,
)
from tests.inventory_tracking.scenarios.arena.situations.situation import Outcome, Situation


SEEDS = (1, 2, 3)
TEN = tuple(range(1, 11))  # R1 and R4, pinned over ten seeds (2026-10-21 ~21:15, below)
# The player, 2026-10-21 ~21:15, on what HOLD_LEADER (echoing_strike/attack.py, ~18:58), QUICK_SETTLE (macros/buffs.py,
# ~17:41) and ENGORGE_PACK_FIRST (builds/warlock/buffs.py, ~15:45) cost here: "yes, keep those 3 switches and pin the
# tests" (rca/2026-10-21/arena-failures-findings.md T1-T3). The pins hold what was measured with them on, a seed or a
# few hundredths of margin, and pass anything better. Death Mark on the held leader (the Herald/safety work under way)
# is expected to improve R1 and R4: tighten these back toward the findings' bounds once it lands.
VARIANTS: dict[str, tuple[Callable[[], Situation], dict[str, bool]]] = {
    'default': (t5_hulks, {}),
    'tactic off': (lambda: t5_hulks(seconds=60.0), {'PACK_TACTIC': False}),
    'long': (lambda: t5_hulks(seconds=60.0), {}),
    # H-A's Herald stood 15-18 off behind its minions: the Herald-centred sigil lay where few of the pack stood
    'herald behind': (lambda: t5_hulks(herald_back=12.0), {}),
    'herald behind, cover off': (lambda: t5_hulks(herald_back=12.0), {'SIGIL_COVER': False}),
    # The bound Urdar dies early; two plain Urdars (demons Bind Demon takes) stand 20.5 north
    'rebind': (lambda: t5_hulks(bound_life=600.0, demons_to_bind=2), {}),
    'rebind off': (lambda: t5_hulks(bound_life=600.0, demons_to_bind=2), {'REBIND_DEMON': False}),
    # The Defiler dies early and is summoned again
    'defiler dies': (lambda: t5_hulks(defiler_life=600.0), {}),
    'defiler dies, between off': (lambda: t5_hulks(defiler_life=600.0), {'PETS_BETWEEN': False}),
}


@contextmanager
def switched(changes: dict[str, bool]) -> Iterator[None]:
    saved = {name: getattr(pack, name) for name in changes}
    for name, value in changes.items():
        setattr(pack, name, value)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(pack, name, value)


@functools.cache
def played(variant: str, seed: int) -> Outcome:
    build, changes = VARIANTS[variant]
    with switched(changes):
        return build().play(seed=seed, keep=True, each_tick=sampled)


def measured(variant: str, seed: int) -> Measures:
    return measures(played(variant, seed))


def held_share(outcome: Outcome) -> float:
    """The share of the ticks from the first sigil on, the pack alive, with half of it or more in the sigil."""
    ticks = [t for t in outcome.stage_.ticks if t.alive]  # type: ignore[attr-defined]
    first = next((t.at for t in ticks if t.sigiled), None)
    after = [t for t in ticks if first is not None and t.at >= first]
    return sum(1 for t in after if t.sigiled >= 0.5 * t.alive) / len(after) if after else 0.0


# -- the findings' strict requirements (§3.4) ---------------------------------------------------------------------

DEFAULT = pytest.mark.xdist_group('herald: default')


@DEFAULT
def test_r1_never_three_of_the_pack_within_5_for_over_a_second():
    # Pinned 2026-10-21 ~21:15 (the ruling above): every seed until HOLD_LEADER; with it, over ten seeds, a spell over
    # 1 s in 5 of 10 (20:09 and 21:15 trees; 3 of 10 with HOLD_LEADER off), so at most 6. Tighten back to every seed
    # once Death Mark goes on the held leader.
    spells = [measured('default', seed).surrounded for seed in TEN]
    assert sum(spell > 1.0 for spell in spells) <= 6, spells


@DEFAULT
def test_r2_half_the_pack_goes_for_a_demon_within_2_s_of_the_first_mark():
    for seed in SEEDS:
        turned = measured('default', seed).turned
        assert turned is not None, seed
        assert turned >= 0.5, seed


@DEFAULT
def test_r3_life_lost_under_15_percent_with_at_most_one_potion():
    # Held since findings §7 (seeds 1 and 3 lost 48% and 22% with 2 and 1 potions). Met from 2026-10-23 03:20 with
    # casters.py ENGORGE_CLEAR_AIM on (rca/2026-10-23/exp-casts-findings.md); still xfails with it off.
    for seed in SEEDS:
        found = measured('default', seed)
        assert found.lost < 0.15, (seed, found)
        assert found.potions <= 1, (seed, found)


@pytest.mark.slow
@pytest.mark.xdist_group('herald: long')
@pytest.mark.xfail(
    strict=True,
    reason="2026-10-22 (rca/2026-10-21/fane-death-sim-findings.md §9): the arena shows the macro each hostile's stat "
    "25 as the live client does, and its Might is level 16's (x2.9 within 46): the forecast prices the pack's raised "
    'blows and keeps out of reach, so the Herald dies within 60 s in 5 of 10 plays with the tactic off and 3 of 10 '
    'with it (9 and 8 with Might x2.0 unshown; life lost 0.14-0.16 of the most either way, 0.52-0.72 with x2.9 '
    'unshown)',
)
def test_r4_the_herald_dies_no_later_than_1_2_times_today_s_median():
    # Pinned 2026-10-21 ~21:15 (the ruling above). The findings' bound is 1.2 x the tactic-off median over seeds 1-3,
    # every Herald dead. HOLD_LEADER speeds the tactic-off kill (ten-seed median 44.1 -> 34.9 s) and slows the tactic's
    # (50.1 -> 55.5 s): 1.59 x on the 20:09 tree, 1.21 x (43.4 against 35.9) on the 21:15 one, the Herald alive at
    # 60 s in 2 of 10 plays with the tactic and 1 of 10 without. Pinned over ten seeds, a Herald alive counted as never
    # dead: 1.65 x and at least 8 of 10 dead each. Back to 1.2 x once Death Mark goes on the held leader.
    today = [measured('tactic off', seed).herald_dead for seed in TEN]
    now = [measured('long', seed).herald_dead for seed in TEN]
    assert sum(at is not None for at in today) >= 8, today
    assert sum(at is not None for at in now) >= 8, now
    late = [math.inf if at is None else at for at in now]
    usual = [math.inf if at is None else at for at in today]
    assert statistics.median(late) <= 1.65 * statistics.median(usual), (today, now)


@DEFAULT
@pytest.mark.xfail(strict=True, reason='still with a hulk in melee for 0.7-4.8 s: the hops run out (findings §7)')
def test_r5_never_still_for_over_a_second_with_a_hostile_in_melee():
    for seed in SEEDS:
        assert measured('default', seed).still <= 1.0, seed


# -- the sigil at the disc covering the most of the pack (SIGIL_COVER) ----------------------------------------------


@pytest.mark.xdist_group('herald: behind')
def test_the_sigil_holds_half_the_pack_with_its_herald_behind():
    for seed in SEEDS:
        covered = held_share(played('herald behind', seed))
        before = held_share(played('herald behind, cover off', seed))
        # 0.6 until 2026-10-21 ~21:15, the ruling above: seed 2 holds 0.574 with the three switches on (0.86, 0.57,
        # 0.89-0.97 by seed; ten seeds: under 0.6 in 1-3 of 10, as with them off), so 0.55
        assert covered >= 0.55, seed
        assert covered > before + 0.2, seed  # under the Herald (or none) it held half the pack a twentieth at most


@DEFAULT
@pytest.mark.xfail(
    strict=True,
    reason='2026-10-22 (findings §9): with the auras shown (stat 25, Might x2.9) seed 3 keeps the sigil off half the '
    "pack for 9.2 s (held 0.66), where the macro keeps out of the raised blows' reach; with the auras "
    'unshown, 0.92 s (held 0.89)',
)
def test_with_the_pack_bunched_the_sigil_is_kept_on_half_of_it():
    for seed in SEEDS:
        ticks = [t for t in played('default', seed).stage_.ticks if t.alive]  # type: ignore[attr-defined]
        first = next(t.at for t in ticks if t.sigiled)
        under = longest([(t.at, t.sigiled < 0.5 * t.alive) for t in ticks if t.at >= first])
        assert under <= 2.0, seed  # SIGIL_LOOK, SIGIL_GAP, the cast and its state's show
        assert held_share(played('default', seed)) >= 0.85, seed


# -- the demons kept out (REBIND_DEMON, PETS_BETWEEN) ---------------------------------------------------------------


@pytest.mark.xdist_group('herald: rebind')
def test_the_bound_demon_dead_no_demon_is_bound_by_the_macro():
    # Until 2026-10-21 ~16:30 the bound demon dead, a demon in reach was bound within 4 s (REBIND_DEMON). The player
    # then: "I will do bind daemon myself. you don't use bind daemon anywhere for now and keep it so"
    # (builds/warlock/bind.py BIND_DEMON_CASTS False): with REBIND_DEMON on or off, the macro casts no Bind Demon.
    for seed in (1, 2):
        stage = played('rebind', seed).stage_  # type: ignore[attr-defined]
        assert any(txt == 189 for _, _, txt in stage.pet_deaths), seed  # the bound Urdar died
        assert stage.binds == [], seed
        assert played('rebind off', seed).stage_.binds == [], seed  # type: ignore[attr-defined]


@pytest.mark.xdist_group('herald: defiler')
def test_the_defiler_summoned_again_stands_between_the_character_and_the_pack():
    for seed in SEEDS:
        found = summons_between(played('defiler dies', seed))
        assert found, seed
        assert all(defiler < here - 3.0 for defiler, here in found), (seed, found)
        before = summons_between(played('defiler dies, between off', seed))
        assert all(defiler > here for defiler, here in before), (seed, before)
