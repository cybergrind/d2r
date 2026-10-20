"""The loot policy (macros/lootpolicy.py; rca/2026-10-18/arch-level-behaviour.md, Option A steps 1, 2 and 4): every
site's answer, by hand and in the KP_6 loop, pinned by a golden table against the rules the sites had before they asked
`verdict` (kept below as the spec), the disagreements of the study's §2.1 and §2.2 named, and the player's ruling of Q1
(2026-10-18 17:50: in the loop a plain valuable with no room is held by every site). Item classes by their items.txt row
as the bundled metadata names them (items/metadata.py), looked up, not written from memory."""

import itertools
from dataclasses import replace
from types import SimpleNamespace

import pytest

from inventory_tracking.game.records import GOLD, HEALING, NAMED, VALUABLE, Drop, Loot, Rolls, has_room, prized
from inventory_tracking.items.metadata import metadata
from inventory_tracking.loot.shown import RARITIES
from inventory_tracking.macros import pickup
from inventory_tracking.macros.lootpolicy import (
    GUARD,
    LOOP_HOLDS,
    NO_ROOM_PLAIN,
    PRESS,
    RUN,
    SIGHTINGS,
    SITES,
    SWEEP,
    verdict,
)
from inventory_tracking.macros.pickmode import MODES, MOST, SURE, is_candidate
from inventory_tracking.macros.pickup import choose, unshunned
from inventory_tracking.macros.runner import MacroRunner
from inventory_tracking.macros.sightings import Sightings


NORMAL, MAGIC, SET, RARE, UNIQUE = (RARITIES[name] for name in ('normal', 'magic', 'set', 'rare', 'unique'))
FULL = ('##########',) * 4
EMPTY = ('..........',) * 4
HERE = (5000.0, 5000.0)
GAME = ('lk-1', 1)
NOW = 100.0


def class_of(name: str) -> int:
    [found] = [int(cid) for cid, base in metadata()['bases'].items() if base['name'] == name]
    return found


def item(name: str, source: str, quality: int = NORMAL, *, marked: bool = False, rolls: Rolls | None = None) -> Drop:
    """A drop as the read makes it (game/memory.py `GameMemory.loot`): `prized` from its source and the marks."""
    return Drop(
        50, 5010.0, 5000.0, name, VALUABLE, (1, 1), prized=prized(source, marked=marked), source=source,
        txt=class_of(name), quality=quality, rolls=rolls,
    )  # fmt: skip


# One of each kind of thing the pickup takes, as the read finds it
ITEMS = (
    item('El Rune', 'rune'),  # below the marks: the study's worked case
    item('Ral Rune', 'rune'),
    item('Ist Rune', 'rune', marked=True),
    item('Chipped Amethyst', 'material'),
    item('Flawless Topaz', 'material', marked=True),
    item('Southern Worldstone Shard', 'material', marked=True),
    item('Ring', 'material', MAGIC),
    item('Ring', 'material', RARE),
    item('Amulet', 'material', SET),
    item('Amulet', 'unique', UNIQUE),
    item('Jewel', 'material', MAGIC),
    item('Grand Charm', 'material', MAGIC),
    item('Grand Charm', 'unique', UNIQUE),
    item('Kriss', 'shown', MAGIC),  # an identify candidate
    item('Circlet', 'shown', RARE),
    item('Phase Blade', 'shown', MAGIC),  # gear the filter shows, no candidate
    item('Heavy Boots', 'shown', RARE),
    item('Kriss', 'shown', NORMAL, rolls=Rolls(3, ((402, 3),))),  # a Void base, +3 Abyss 3os: sure and a candidate
    item('Monarch', 'shown', MAGIC, rolls=Rolls(4)),  # 4os: sure and a candidate
    item('Plate Mail', NAMED, UNIQUE),
    item('Archon Plate', NAMED, SET),
)


# The sites' own rules before they asked `verdict` (pickup.py `stops_for`, hunt.py `stands_by` and `holds`, removed
# 2026-10-19): the spec the table pins.
def stops_for(drop: Drop, loot: Loot, looped: bool = False) -> bool:
    if drop.kind != VALUABLE or has_room(loot.room, drop.size):
        return False
    return drop.prized or (looped and drop.unit_id not in loot.shown and not is_candidate(drop))


def stands_by(drop: Drop, loot: Loot, waived: set[int]) -> bool:
    return (
        drop.kind == VALUABLE
        and drop.unit_id not in loot.shown
        and drop.unit_id not in waived
        and not has_room(loot.room, drop.size)
    )


def holds(drop: Drop, loot: Loot, looped: bool = False) -> bool:
    if drop.kind != VALUABLE:
        return False
    plain = looped and drop.unit_id not in loot.shown and not is_candidate(drop)
    return drop.prized or has_room(loot.room, drop.size) or plain


def today(
    site: str, drop: Drop, *, room: bool, mode: str, sold_full: bool, shunned: bool, given_up: bool, looped: bool
):
    """(take, hold) of `site` for `drop` alone on the ground, by the sites' own code: the runner's mode filter
    (`_picked`), the pickup's shuns (`unshunned`) and choice (`choose`), the press's stop (`stops_for`), the level run's
    stand (`stands_by`), the sweep's (`holds`), the guard's predicate (`_valuable_left`, before it asked the verdict:
    every valuable but an identify candidate) and the sightings (`Sightings.update`). `looped`: the KP_6 loop's press
    and sweep (the ruling of 2026-10-18 17:50); the level run, the guard and the sightings answer the same either
    way."""
    loot = Loot(
        (drop,), room=EMPTY if room else FULL, game=GAME,
        shown=frozenset((drop.unit_id,)) if drop.source == 'shown' else frozenset(),
    )  # fmt: skip
    keeper = SimpleNamespace(
        loop=SimpleNamespace(on=True, sold_full={drop.txt} if sold_full else set()), pickup_mode=mode
    )
    loot = MacroRunner._picked(keeper, loot)  # type: ignore[arg-type]
    pickup.SHUNNED.clear()
    if shunned:
        pickup.SHUNNED[drop.unit_id] = NOW + pickup.SHUN_SECONDS
    ground = unshunned(loot, NOW)
    kept = replace(ground, drops=tuple(d for d in ground.drops if not given_up))  # the site's give-ups out
    plan = choose(kept, HERE)
    take = plan is not None and plan.drop.unit_id == drop.unit_id
    if site == GUARD:
        # runner.py `_valuable_left`: the ground read whole, no shuns, no give-ups
        return take, any(d.kind == VALUABLE and not is_candidate(d) for d in loot.drops)
    if site == SIGHTINGS:
        seen = Sightings()
        seen.update(loot, HERE, 79, NOW)
        return take, drop.unit_id in seen.items
    if site == PRESS:
        return choose(ground, HERE) is not None, any(stops_for(d, ground, looped) for d in ground.drops)
    if site == RUN:
        waived = {drop.unit_id} if given_up else set()
        return take, any(stands_by(d, ground, waived) for d in ground.drops)
    assert site == SWEEP
    return take, any(holds(d, kept, looped) for d in kept.drops)


FACTS = list(itertools.product(ITEMS, (True, False), (False, True), (False, True), (False, True), (False, True)))


@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('site', SITES)
def test_every_sites_answer_of_today_is_the_verdict(site, mode):
    # The golden table: item x room x stash stack full x shunned x given up x the loop on, for each site and pickup mode
    wrong = []
    for drop, room, sold_full, shunned, given_up, looped in FACTS:
        found = verdict(
            drop, site, room=room, shown=drop.source == 'shown', mode=mode, sold_full=sold_full, shunned=shunned,
            given_up=given_up, looped=looped,
        )  # fmt: skip
        site_says = today(
            site, drop, room=room, mode=mode, sold_full=sold_full, shunned=shunned, given_up=given_up, looped=looped
        )
        if (found.take, found.hold) != site_says:
            wrong.append((drop.label, drop.quality, room, sold_full, shunned, given_up, looped, site_says, found))
    assert wrong == []
    assert len(FACTS) == len(ITEMS) * 32


def answers(drop: Drop, *, room: bool = False, mode: str = MOST, **facts) -> dict[str, bool]:
    shown = drop.source == 'shown'
    return {site: verdict(drop, site, room=room, shown=shown, mode=mode, **facts).hold for site in SITES}


def test_a_low_rune_with_no_room_by_hand_the_press_and_sweep_go_on_the_run_and_guard_hold():
    # The study's §2.1 worked case (Q1): El Rune taken from r01, marked from Io; by hand as before the ruling
    rune = ITEMS[0]
    held = answers(rune)
    assert held == {PRESS: False, SWEEP: False, RUN: True, GUARD: True, SIGHTINGS: True}
    assert {site for site, hold in held.items() if hold} == NO_ROOM_PLAIN.stands_by
    assert {site for site, hold in held.items() if not hold} == NO_ROOM_PLAIN.moves_on
    assert verdict(rune, RUN, room=False, shown=False).disputed
    assert verdict(rune, RUN, room=False, shown=False, mode=SURE).disputed  # every rune is a sure valuable
    for name in ('Chipped Amethyst', 'Jewel'):
        assert verdict(next(d for d in ITEMS if d.label == name), PRESS, room=False, shown=False).disputed
    magic_ring = next(d for d in ITEMS if d.label == 'Ring' and d.quality == MAGIC)
    assert answers(magic_ring) == held
    assert answers(magic_ring, mode=SURE) == dict.fromkeys(SITES, False)  # the sure mode does not take it
    assert not verdict(rune, RUN, room=True, shown=False).disputed


PLAIN = ('El Rune', 'Ral Rune', 'Chipped Amethyst', 'Jewel', 'Ring', 'Amulet', 'Grand Charm')


def test_in_the_loop_every_site_holds_a_plain_valuable_with_no_room_by_the_players_ruling():
    # The player, 2026-10-18 17:50, on Q1: "we should stop and clear inventory with our designated town routine": the
    # loop's press and sweep hold it as its level run, guard and sightings do, and its room rules make the room
    assert 'held in the loop' in NO_ROOM_PLAIN.ruling
    plain = [d for d in ITEMS if verdict(d, PRESS, room=False, shown=d.source == 'shown').disputed]
    assert {d.label for d in plain} == set(PLAIN)  # the magic Ring, the set Amulet, the magic Jewel and Grand Charm
    for drop in plain:
        assert answers(drop, looped=True) == dict.fromkeys(SITES, True), drop.label
        assert answers(drop) == {PRESS: False, SWEEP: False, RUN: True, GUARD: True, SIGHTINGS: True}, drop.label
        for site in (PRESS, SWEEP):
            found = verdict(drop, site, room=False, shown=False, looped=True)
            assert (found.take, found.why, found.disputed) == (False, LOOP_HOLDS, True)


def test_in_the_loop_what_is_not_of_the_class_is_held_as_by_hand():
    # The ruling is the class's: filter-shown gear and identify candidates go on as before, the drops with room too
    for drop in ITEMS:
        for room in (True, False):
            if not room and verdict(drop, PRESS, room=room, shown=drop.source == 'shown').disputed:
                continue
            assert answers(drop, room=room, looped=True) == answers(drop, room=room), (drop.label, room)
    rune = ITEMS[0]
    assert answers(rune, looped=True, shunned=True)[PRESS] is False  # left alone a while: the press's input has it not
    assert answers(rune, looped=True, given_up=True)[SWEEP] is False  # the sweep's spent tries
    assert answers(rune, mode=SURE, looped=True) == answers(rune, looped=True)  # every rune is a sure valuable
    magic_ring = next(d for d in ITEMS if d.label == 'Ring' and d.quality == MAGIC)
    assert answers(magic_ring, mode=SURE, looped=True) == dict.fromkeys(SITES, False)  # the sure mode does not take it


def test_gear_the_filter_shows_with_no_room_holds_only_the_guard_and_sightings():
    # Not of Q1's class: the run goes on for it as the press does (`Loot.shown`), the guard keeps the game for what
    # is no identify candidate
    blade = next(d for d in ITEMS if d.label == 'Phase Blade')
    assert answers(blade) == {PRESS: False, SWEEP: False, RUN: False, GUARD: True, SIGHTINGS: True}
    assert not verdict(blade, GUARD, room=False, shown=True).disputed
    kriss = ITEMS[13]  # a magic Kriss: an identify candidate, held by none
    assert answers(kriss) == dict.fromkeys(SITES, False)


def test_a_prized_drop_with_no_room_is_held_by_every_site():
    for drop in ITEMS:
        if drop.prized:
            assert answers(drop) == dict.fromkeys(SITES, True), drop.label


def test_a_drop_with_room_is_taken_and_only_the_sweep_and_guard_stay_by_it():
    rune = ITEMS[2]  # Ist
    assert all(verdict(rune, site, room=True, shown=False).take for site in SITES)
    assert answers(rune, room=True) == {PRESS: False, SWEEP: True, RUN: False, GUARD: True, SIGHTINGS: True}


def test_the_guard_ignores_the_shuns_and_give_ups_the_hands_keep():
    # The study's §2.2: a drop the hands gave up on still keeps the game
    rune = ITEMS[2]
    assert answers(rune, shunned=True) == {PRESS: False, SWEEP: False, RUN: False, GUARD: True, SIGHTINGS: True}
    assert answers(rune, given_up=True) == {PRESS: True, SWEEP: False, RUN: False, GUARD: True, SIGHTINGS: True}


def test_what_the_mode_does_not_keep_or_a_full_stash_stack_holds_nobody():
    blade = next(d for d in ITEMS if d.label == 'Phase Blade')
    assert answers(blade, mode=SURE) == dict.fromkeys(SITES, False)
    assert answers(ITEMS[2], sold_full=True) == dict.fromkeys(SITES, False)


def test_supplies_are_not_the_policys():
    for supply in (Drop(9, 0.0, 0.0, '6000 gold', GOLD), Drop(10, 0.0, 0.0, 'a super healing potion', HEALING)):
        found = verdict(supply, PRESS, room=True, shown=False)
        assert (found.take, found.hold, found.disputed) == (False, False, False)
