"""The Warlock's casts that are more than one aim and one key (macros/build.py `Build.casters`): the
Defiler's summon, Consume on a Defiler, the two together at a game's start and in the middle of a run,
Engorge on a corpse, and the sigil's own answer when its place is off the screen. Each is called by the
buff executor (macros/buffs.py) with a `Casting` and answers with a `Tried`.
"""

import math
import struct
import weakref
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import replace

from inventory_tracking.builds.warlock import bind as binding, buffs as plan, pets
from inventory_tracking.builds.warlock.bind import BIND_NO_KEY, BIND_RETRY
from inventory_tracking.builds.warlock.buffs import (
    CONSUME_RETRY,
    CONSUME_SOON,
    ENGORGE_LOOKS,
    ENGORGE_REACH,
    ENGORGE_RETRY,
    OMEN_TXT,
    OPENER_KEEP,
    OPENER_LEAD,
    OPENER_TXT,
    SIGIL_EARLY,
    SIGIL_EDGE,
    SIGIL_GAP,
    SIGIL_LASTS,
    SIGIL_LOOK,
    SIGIL_MISSILES,
    SIGIL_RADIUS,
    SIGIL_SECONDS,
    SIGIL_SHOWS,
    SIGIL_UNSHOWN,
    UNSHOWN,
    SigilWatch,
    danger_every,
    demon_hurt,
    engorge_every,
    keep_reason,
    kept,
)
from inventory_tracking.builds.warlock.defiler import DEFILER_MANA, DEFILER_RETRY, world_spot
from inventory_tracking.builds.warlock.mark import demons
from inventory_tracking.builds.warlock.skills import BIND_DEMON, CONSUME, ENGORGE, SUMMON_DEFILER
from inventory_tracking.combat import engage, pack as herald_pack
from inventory_tracking.common import LOG
from inventory_tracking.game.layout import DEFILER_CLASS as DEFILER, ITEM_UNIT, MONSTER_UNIT, NO_OWNER, OBJECT_UNIT
from inventory_tracking.game.records import Monster, Player, World
from inventory_tracking.game.view import BODY_LIFT, FEET
from inventory_tracking.macros.actuator import Abort
from inventory_tracking.macros.buffs import keys_of
from inventory_tracking.macros.build import Caster, Casting, Tried
from inventory_tracking.macros.cta import CASTERS as CTA_CASTERS
from inventory_tracking.macros.engine import Run
from inventory_tracking.macros.hunting.base import hostiles
from inventory_tracking.macros.pad import heading_degrees, turned
from inventory_tracking.macros.routines import (
    ACTING,
    LOAD_LIMIT,
    TOWN_NPCS,
    on_screen,
    press_skill,
    screen_fraction,
    standable,
    take_prebuff_weapons,
    world_point,
)
from inventory_tracking.macros.skills import skill_name
from inventory_tracking.macros.teleport import HOVER_SECONDS, ground_fraction
from inventory_tracking.macros.travel import clear_line, label
from inventory_tracking.native.layout import HIRELING_CLASS_ID


# Right of the character, where the user summons; then other sides, a Defiler's width apart.
SUMMON_SPOTS = ((0.66, 0.42), (0.36, 0.44), (0.5, 0.26), (0.64, 0.62), (0.4, 0.64))
# The same sides at half the distance, for known narrow ground (Cave Level 1: nothing at the far ones, 2026-10-12).
NEAR_SPOTS = tuple((round((x + FEET[0]) / 2, 3), round((y + FEET[1]) / 2, 3)) for x, y in SUMMON_SPOTS)
CLEAR = 7.0  # world units around the Defiler that must be empty before Consume
# A tall monster drawn below the Defiler covers it (Consume took the bound demon with the pointer on the Defiler,
# 2026-10-07 01:46), so nothing may stand in this screen column either: across, below and above, in iso units.
COVER_ACROSS, COVER_BELOW, COVER_ABOVE = 9.0, 26.0, 8.0
CONSUME_ATTEMPTS = 3
# A townsperson this near the Defiler is under the pointer on it: Consume cannot take one, so the press shows nothing.
# 22:35:05-13 on 2026-10-19 (Kurast Docks): Meshif (class 264) 0.9-2.8 from the Defiler, three presses showed nothing
# and the game was left. Kashya 14 off (2026-10-07) never was. Such a miss has another Defiler summoned elsewhere.
TOWN_COVER = 4.0
CONSUME_PAD_WAIT = 10.0  # seconds: Consume due in controller mode is asked again this often (`consume_again`)
# A Consume that took another Defiler than the one aimed at is a Consume (rca/2026-10-21/demon-lost-findings.md cause
# 6, verified in the take 20261021T124057Z-22): at 15:41:24.6 "Consume ran out" summoned a Defiler for it (by design,
# `renew_consume`), 1.4 units from the one standing out, which `crowd` does not count (`bystanders` leaves the Defilers
# out); the key at 15:41:25.44 took the standing one (128 -> 0 at 15:41:25.49, the character's mana cap 2661 -> 2907,
# the state on) and the press was judged "not seen in 2.5s", again in 20 s. True: the state on with a Defiler of those
# out before the key gone or dead is the Consume done, said; one Defiler stays out either way. False: only the one
# aimed at.
CONSUME_ANY_DEFILER = True
# The player, 2026-10-21 ~21:02: "also, T5 herald fight - we stood and do NOTHING under the fire, not damaging anything
# for solid 15 seconds" (rca/2026-10-21/consume-in-fight-findings.md). At 20:59:03.66 Consume ran out and its renewal
# began with nothing within CONSUME_CLEAR; the tier 5 pack (15 Flayers) showed within 30 0.07 s later and the renewal
# went on: two summons, a Defiler crowded by the bound Pit Lord summoned again, two Consume keys, 8.3 s with no strike.
# True: a renewal in the field (`renew_consume`) stops at the first look with a hostile within CONSUME_CLEAR of the
# character (`FightCame`, `fight_breaks`) and is put off to the first quiet, CONSUME_SOON on at the soonest (buffs.py
# `consume_due` holds it off while the hostiles are near). False: it goes on to its end, as before.
CONSUME_BREAKS = True
# 2026-10-24 (rca/2026-10-24/consume-miss-findings.md; the player: exp/hour, no death): Consume goes on the unit the
# game's record names under the pointer, not on the one aimed at. 14:30:19.7-27.9: the record named a super healing
# potion's label (4, 2190385010), 2.5 units off the Defiler, at all three keys: 8.1 s standing, no Consume, a Grand
# Charm 1 away (take 20261024T112707Z-101); 14:24:20 an object (type 2) the same way; 13:06:51 the walking mercenary
# (class 338, 1.8 off; `crowd` leaves it out). True: with the record readable (mouse mode) it is read after the aim,
# before the key (`hover_cover`); an item's label or an object (STILL_COVERS: they do not walk off) has another Defiler
# summoned at another spot, a live monster of the look that is not a Defiler (it walks) is looked at again the next
# attempt; no key either way. A Defiler named (CONSUME_ANY_DEFILER), nothing, or a unit the look does not hold: the key
# as before. False: the key whatever the record names, as before. On from the restart after 15:00 on 2026-10-24
# (11 replay tests; the warlock folder plus test_routines.py green with it on: 604).
CONSUME_HOVER_CHECK = True
# World units a Defiler may walk while the pointer travels before the pointer follows it (user, 2026-10-07).
AIM_DRIFT = 1.0
AIM_TRIES = 4
PANEL_OPEN = 'a panel is open'  # what stops a summon with the player's panel open (`hand_off`)
# 2026-10-23 (the player: "push exp/hour"; rca/2026-10-23/defiler-idle-findings.md): a key the mana does not pay for
# casts nothing, and `summon_defiler` went on to the next spot 1.8 s later, up to five (05:27:00-07 with mana 2-38: four
# keys, 7.4 s). True: no key while the mana read is under DEFILER_MANA (defiler.py): `NoMana`, which the renewal puts
# off to the first quiet (CONSUME_SOON). False: keyed whatever the mana, as before.
SUMMON_PAYS = True
NO_MANA = 'no mana'  # the words of `NoMana`
# 2026-10-23 (the same findings): a summon the game refuses (ground a Defiler cannot stand on, the mana) shows no cast
# mode at all, and the summon waited 1.5 s for a Defiler at each spot: 03:57:59-58:18 at the Plains of Despair's entry,
# full mana, the level's ground not yet read, 7 of 11 keys refused, 18.6 s. Of the 418 keys that cast in the takes of
# 2026-10-22/23 the cast mode showed a median 0.03 s after the key (p99 0.06 s, the most 0.76 s with the character
# busy at the key). True: with no cast mode (game/layout.py ACTING) and no Defiler SUMMON_REFUSED s after the key, the
# next spot is keyed at once. False: each spot waited 1.5 s, as before.
SUMMON_REFUSED_FAST = True
SUMMON_REFUSED = 0.35  # seconds after the key with no cast mode: refused
SUMMON_SHOWS = 1.5  # seconds a cast summon is waited for to show
STILL = 1  # a monster's neutral mode: standing, not walking (modes 2-3)


class NoMana(Abort):
    """A summon the mana does not pay for (SUMMON_PAYS): nothing keyed."""


def defilers(world: World) -> list[Monster]:
    return [monster for monster in world.monsters if monster.txt_id == DEFILER]


def standing(world: World) -> set[int]:
    """The Defilers alive in the look (a consumed one may stay listed dead: 0/128, mode 0)."""
    return {m.unit_id for m in defilers(world) if not pets.dead(m)}


def bystanders(world: World, but: int | None = None) -> list[Monster]:
    """Every living monster Consume might take in place of the Defiler: the character's own and any whose stats
    could not be read, but the mercenary and townsfolk. Not a hostile: Consume cannot take it, and counting them made
    every Defiler "crowded" mid-level (2026-10-10 18:48)."""
    return [
        m
        for m in world.monsters
        if m.txt_id not in (DEFILER, HIRELING_CLASS_ID)
        and m.txt_id not in TOWN_NPCS
        and m.unit_id != but
        and (m.ally or m.owner != NO_OWNER or not m.max_life)
    ]


class Unconsumed(Abort):
    """Consume did not take on any Defiler tried (`consume`): nothing else happened, so the prebuff goes on without it
    (`defiler_dance`)."""


def townsfolk_over(world: World, x: float, y: float) -> list[Monster]:
    """The townsfolk within TOWN_COVER of a Defiler at (x, y): the pointer on it may be on them."""
    return [m for m in world.monsters if m.txt_id in TOWN_NPCS and math.hypot(m.x - x, m.y - y) < TOWN_COVER]


def in_the_way(monster: Monster, x: float, y: float) -> bool:
    """Whether the pointer on a Defiler at (x, y) might be on this monster instead."""
    dx, dy = monster.x - x, monster.y - y
    return math.hypot(dx, dy) < CLEAR or (abs(dx - dy) < COVER_ACROSS and -COVER_ABOVE < dx + dy < COVER_BELOW)


def crowd(world: World, x: float, y: float) -> list[Monster]:
    return [m for m in bystanders(world) if in_the_way(m, x, y)]


def log_crowd(world: World, unit: int) -> None:
    """Research: what stands in the Defiler's way, as class and offset from it in world units."""
    target = next((m for m in defilers(world) if m.unit_id == unit), None)
    near = (
        [
            f'class {m.txt_id} at ({m.x - target.x:+.1f}, {m.y - target.y:+.1f})'
            for m in crowd(world, target.x, target.y)
        ]
        if target is not None
        else []
    )
    LOG.info('Macro: the Defiler is crowded by %s; summoning another', ', '.join(near) or 'nothing now')


def open_spots(
    run: Run, world: World, skip: int = 0, tried: Sequence[tuple[float, float]] = ()
) -> list[tuple[float, float]]:
    """SUMMON_SPOTS from the `skip`-th on, those with nobody near first (a Defiler next to the bound demon cannot be
    consumed safely). With the ground known (`run.ground`), only spots a summon can stand on, NEAR_SPOTS last;
    all of them when none can. A replacement (`skip`): spots `tried` last, then the farthest from a bystander first.
    With a tier 4-5 Herald pack about, the spot between the character and the pack first (`between`)."""
    spots = list(SUMMON_SPOTS[skip % len(SUMMON_SPOTS) :] + SUMMON_SPOTS[: skip % len(SUMMON_SPOTS)])
    rect = run.actuator.keys.focused_window_rect()
    if rect is None or world.player is None:
        return spots
    player, aspect = world.player, rect[2] / rect[3]
    ground = run.reads.ground()
    if ground:
        here = (player.x, player.y)
        known = [*spots, *NEAR_SPOTS]
        found = [spot for spot in known if standable(ground, here, world_point(player, *spot, aspect))]
        if len(found) < len(spots):
            LOG.info('Macro: %d of %d summon spots are on ground a Defiler can stand on', len(found), len(known))
        spots = found or spots
    near = bystanders(world)

    def order(spot: tuple[float, float]) -> tuple[bool, bool, bool, float]:
        x, y = world_point(player, *spot, aspect)
        # 22:00:25-29 on 2026-10-19: three Defilers in a row at the side the bound demon (class 189) stood, 4.4 s
        # mid-fight (rca/2026-10-19/tz-leveling-findings.md C8)
        apart = min((math.hypot(m.x - x, m.y - y) for m in near), default=math.inf) if skip else 0.0
        # Nor beside a townsperson, who takes the pointer (TOWN_COVER; 22:35:05 on 2026-10-19)
        return spot in tried, bool(crowd(world, x, y)), bool(townsfolk_over(world, x, y)), -apart

    found = sorted(spots, key=order)
    first = between(run, world) if not skip and not tried else None
    return [first, *found] if first is not None else found


def summon_defiler(
    run: Run, *, until: float | None = None, skip: int = 0, tried: list[tuple[float, float]] | None = None
) -> Monster:
    """Summon one Defiler. `until` (a clock time) keeps trying that long: a new game takes no input for a while.
    `skip` starts that many spots further on, for a Defiler that replaces a crowded one; `tried` (kept by the
    caller) gets the spots it keyed, refused or taken, and they are taken last again."""
    start = run.world()
    before = {monster.unit_id for monster in defilers(start)}
    # A spot that cannot be walked on takes no summon (user, 2026-10-06): try the next one.
    world, spot = None, SUMMON_SPOTS[0]
    spots = open_spots(run, start, skip, tried or ())
    looked = [start]  # the last world looked at: the panel check reads no world of its own

    def came(seen: World) -> bool:
        looked[0] = seen
        return any(m.unit_id not in before for m in defilers(seen))

    while world is None and spots:
        spot = spots.pop(0)
        hand_off(looked[0])
        unpaid(run, looked[0])
        rect = run.actuator.keys.focused_window_rect()
        if run.pad is not None and start.player is not None and rect is not None:
            # Controller mode: a heading toward the spot (macros/pad.py); the game puts it at its own distance.
            here = (start.player.x, start.player.y)
            run.pad.aim_place(here, world_point(start.player, *spot, rect[2] / rect[3]))
        else:
            run.actuator.move(*spot, scatter=(40, 25))
        keyed = press_skill(run, SUMMON_DEFILER)
        world = answer(run, came, keyed, spot)
        if world is None and tried is not None and spot not in tried:
            # 17:33:49-57 on 2026-10-23 (Hole Level 2): each of three summons in one Consume renewal keyed the same two
            # refused spots first again, 0.7 s each time; a refused spot goes last like a taken one (`open_spots`)
            tried.append(spot)
        if world is None and not spots and until is not None and run.clock() < until:
            looked[0] = run.world()
            spots = open_spots(run, looked[0])[:1]
            run.pause('screen')
    if world is None:
        raise Abort('Defiler: not seen at any spot')
    if tried is not None:
        tried.append(spot)
    defiler = next(m for m in defilers(world) if m.unit_id not in before)
    if run.pad is not None and start.player is not None:
        window = run.actuator.keys.focused_window_rect()
        if window is not None:
            log_landing(start.player, world_point(start.player, *spot, window[2] / window[3]), defiler)
    # Research: which field ties a summon to its player (the mercenary's owner field does not).
    LOG.info(
        'Macro: Defiler is unit %s (player unit %s); unit and data: %s',
        defiler.unit_id,
        world.player.unit_id if world.player else None,
        defiler.raw.hex(),
    )
    # Research: is the pointer move honoured? The summon should land where the pointer was sent.
    rect = run.actuator.keys.focused_window_rect()
    if rect is not None and world.player is not None:
        landed = screen_fraction(world.player, defiler.x, defiler.y, rect[2] / rect[3])
        LOG.info(
            'Macro: aimed at (%.3f, %.3f), Defiler drawn at (%.3f, %.3f); pointer %s in window %s',
            *spot,
            landed[0],
            landed[1] + BODY_LIFT,
            run.actuator.keys.pointer(),
            rect,
        )
    run.pause('key')
    return defiler


def unpaid(run: Run, world: World) -> None:
    """`NoMana` when the mana read is under a summon's cost (SUMMON_PAYS); nothing when it pays or is not read."""
    if not SUMMON_PAYS:
        return
    mana = run.reads.mana(world)
    if mana is not None and mana < DEFILER_MANA:
        raise NoMana(f'{NO_MANA} for a Defiler: {mana:.0f} of {DEFILER_MANA:.0f}')


def answer(run: Run, came: Callable[[World], bool], keyed: float, spot: tuple[float, float]) -> World | None:
    """The first look with the new Defiler within SUMMON_SHOWS of the key; None without one, and SUMMON_REFUSED after
    the key with no cast mode shown (SUMMON_REFUSED_FAST): the game refused the spot."""
    acted = [False]

    def answered(seen: World) -> bool:
        if came(seen):
            return True
        if seen.player is not None and seen.player.mode in ACTING:
            acted[0] = True
        return SUMMON_REFUSED_FAST and not acted[0] and run.clock() - keyed >= SUMMON_REFUSED

    seen = run.seen(answered, SUMMON_SHOWS)
    if seen is None or came(seen):
        return seen
    LOG.info('Macro: Summon Defiler at (%.2f, %.2f): no cast in %.2fs, refused', *spot, run.clock() - keyed)
    return None


def hand_off(world: World) -> None:
    """No summon into a panel the player has open (rca/2026-10-14/run-1932-findings.md issue 3): stopped as a key of
    the player's stops a routine; the caller tries again soon. `world` is the caller's latest look: no read of its
    own under the strike (golden loop_counts.json)."""
    panels = world.open_panels
    if panels:
        raise Abort(f'{PANEL_OPEN} ({", ".join(panels)}): no summon into it')


def log_landing(player: Player, toward: tuple[float, float], defiler: Monster) -> None:
    """Controller mode: where Summon Defiler (controllerskillsettings.json usageType 0, distance 2) put the Defiler
    against the heading the stick gave it (rca/2026-10-13/controller-gaps.md step 1)."""
    heading = (toward[0] - player.x, toward[1] - player.y)
    went = (defiler.x - player.x, defiler.y - player.y)
    LOG.info(
        'Pad consume: Summon Defiler toward %.0f degrees: the Defiler (unit %d) landed at (%+.1f, %+.1f) from the '
        'character, %.1f away at %.0f degrees (off %+.0f degrees)',
        heading_degrees(heading), defiler.unit_id, *went, math.hypot(*went), heading_degrees(went),
        turned(heading_degrees(went), heading_degrees(heading)),
    )  # fmt: skip


def mine(world: World) -> dict[int, int]:
    """unit id -> class of the units Consume's target group may take (controllerskillsettings.json targetGroup 6):
    the Defilers, the bound demon and the other summons, the mercenary."""
    return {
        m.unit_id: m.txt_id
        for m in world.monsters
        if m.txt_id in (DEFILER, HIRELING_CLASS_ID) or m.ally or m.owner != NO_OWNER
    }


def log_pad_consume(run: Run, unit: int, before: dict[int, int], began: float, shown: World | None) -> None:
    """Controller mode: which of the character's units Consume took and whether its state appeared."""
    after = mine(run.world())
    gone = [f'unit {u} (class {c}{", the Defiler" if u == unit else ""})' for u, c in before.items() if u not in after]
    LOG.info(
        "Pad consume: Consume pressed with the client's target on the Defiler (unit %d); consumed %s; the state %s",
        unit, ', '.join(gone) or 'nothing',
        f'shown after {run.clock() - began:.2f}s' if shown is not None else 'not shown in 2.5s',
    )  # fmt: skip


FOLLOW_SECONDS = 2.0  # for a Defiler left behind to come into view (summons follow the character)


def in_view(run: Run) -> Monster | None:
    """A standing Defiler drawn in the window, waited for FOLLOW_SECONDS when one stands out of it; None with none
    (not the first standing one: it may be out of view, which stopped the KP_6 loop on 2026-10-17)."""
    rect = run.actuator.keys.focused_window_rect()

    def shown(world: World) -> Monster | None:
        if rect is None or world.player is None:
            return None
        player = world.player
        drawn = [m for m in defilers(world) if on_screen(screen_fraction(player, m.x, m.y, rect[2] / rect[3]))]
        return drawn[0] if drawn else None

    world = run.world()
    found = shown(world)
    if found is not None or not defilers(world):
        return found
    LOG.info('Macro: the standing Defiler is out of view: waited for it to follow')
    if run.seen(lambda w: shown(w) is not None, FOLLOW_SECONDS) is None:
        LOG.info('Macro: no Defiler came into view: another is summoned')
        return None
    return shown(run.world())


def aim_at(run: Run, unit: int) -> bool:
    """Put the pointer on this Defiler where it stands now, following it while it walks. False when it never stood
    still: Consume must not be pressed (the bound demon may be under the pointer)."""
    for _ in range(AIM_TRIES):
        world = run.world()
        target = next((m for m in defilers(world) if m.unit_id == unit), None)
        if target is None or world.player is None:
            raise Abort('the Defiler is gone before Consume')
        rect = run.actuator.keys.focused_window_rect()
        if rect is None:
            raise Abort('no game window')
        if run.pad is not None:
            # Controller mode: the client's target has to name it (macros/pad.py); nothing else is consumed.
            here = (world.player.x, world.player.y)
            return run.pad.aim_unit(MONSTER_UNIT, unit, here, (target.x, target.y), 'the Defiler')
        point = screen_fraction(world.player, target.x, target.y, rect[2] / rect[3])
        if not on_screen(point):
            raise Abort('the Defiler is out of view')
        run.actuator.move(*point, scatter=(5, 5))
        now = next((m for m in defilers(run.world()) if m.unit_id == unit), None)
        if now is None:
            raise Abort('the Defiler is gone before Consume')
        drift = math.hypot(now.x - target.x, now.y - target.y)
        if drift <= AIM_DRIFT:
            return True
        LOG.info('Macro: the Defiler moved %.1f units during the aim; aiming again', drift)
    return False


def log_miss(run: Run, world: World, unit: int) -> None:
    """Research: the scene when a pressed Consume showed nothing, everything as an offset from the
    Defiler in world units (the mercenary and townsfolk too: they may cover it)."""
    target = next((m for m in defilers(world) if m.unit_id == unit), None)
    player = world.player
    if target is None or player is None:
        LOG.info('Macro: Consume showed nothing; Defiler %s is gone, player %s', unit, player)
        return
    near = [
        f'class {m.txt_id} mode {m.mode} at ({m.x - target.x:+.1f}, {m.y - target.y:+.1f})'
        for m in world.monsters
        if m.unit_id != unit and math.hypot(m.x - target.x, m.y - target.y) < 40
    ]
    over = run.hovered() if run.hovered is not None and run.pad is None else 'unread'
    LOG.info(
        'Macro: Consume showed nothing; Defiler mode %s, player mode %s at (%+.1f, %+.1f), '
        'Consume %s, pointer %s, under it %s; near: %s',
        target.mode,
        player.mode,
        player.x - target.x,
        player.y - target.y,
        player.consume,
        run.actuator.keys.pointer(),
        over,
        ', '.join(near) or 'nothing',
    )


def hover_cover(run: Run, world: World) -> tuple[int, int] | None:
    """CONSUME_HOVER_CHECK: what the game's record names under the pointer put on a Defiler, when it is not a unit
    Consume can take there: an item's label or an object (STILL_COVERS), a live monster of the look that is not a
    Defiler (the mercenary, the bound demon). None: a Defiler, nothing, a unit the look does not hold, unread."""
    if not CONSUME_HOVER_CHECK or run.pad is not None or run.hovered is None:
        return None
    run.pace.sleep(HOVER_SECONDS)  # for the record to follow the pointer's move
    over = run.hovered()
    if over is None:
        return None
    if over[0] in STILL_COVERS:
        return over
    if over[0] == MONSTER_UNIT and any(m.unit_id == over[1] and m.txt_id != DEFILER for m in world.monsters):
        return over
    return None


def consume(run: Run, defiler: Monster, tried: list[tuple[float, float]] | None = None) -> None:
    """Consume this Defiler and nothing else (it once took the bound demon, 2026-10-06/07): the key is pressed only
    while nothing stands near the Defiler or over its drawn body (`in_the_way`); if it stays crowded, another
    Defiler is summoned at another open spot. Afterwards the Defiler must be the one gone. A press that changes
    nothing (about one in thirty) is made again under the same checks."""
    missed, tried = False, tried if tried is not None else []
    for attempt in range(CONSUME_ATTEMPTS):

        def clear(w: World, unit: int = defiler.unit_id) -> bool:
            target = next((m for m in defilers(w) if m.unit_id == unit), None)
            return target is None or not crowd(w, target.x, target.y)

        if run.seen(clear, 1.0) is None:
            log_crowd(run.world(), defiler.unit_id)
            defiler = summon_defiler(run, skip=attempt + 1, tried=tried)
            continue
        # Ready first, then aim: the key follows the pointer at once, on the Defiler as it stands.
        run.expect('character ready', lambda w: w.player is not None and w.player.mode not in ACTING, 2.5)
        if not aim_at(run, defiler.unit_id):
            continue
        if run.research is not None:  # which bytes name the unit under the pointer (a later check)
            LOG.info(
                'Macro: Defiler %s under the pointer; type and id at %s', defiler.unit_id, run.research(defiler.unit_id)
            )
        if not clear(run.world()):  # somebody walked up during the pointer move
            continue
        over = hover_cover(run, run.world())
        if over is not None:  # CONSUME_HOVER_CHECK: the key would cast nothing (or on that unit)
            still = over[0] in STILL_COVERS
            LOG.info(
                'Macro: Consume not pressed, under the pointer on the Defiler: %s (%s)', over,
                'it stays: another is summoned' if still else 'it walks: looked at again',
            )  # fmt: skip
            if still and attempt + 1 < CONSUME_ATTEMPTS:
                defiler = summon_defiler(run, skip=attempt + 1, tried=tried)
            continue
        before, began = (mine(run.world()) if run.pad is not None else {}), run.clock()
        others = {m.unit_id for m in defilers(run.world()) if m.unit_id != defiler.unit_id and not pets.dead(m)}
        press_skill(run, CONSUME)
        if run.pad is not None and not run.pad.pressed:
            continue  # the client's target left the Defiler before the press: nothing cast (`Pad target:`)

        def consumed(w: World, unit: int = defiler.unit_id, others: set[int] = others) -> bool:
            if not (w.player and w.player.consume):
                return False
            if all(m.unit_id != unit for m in defilers(w)):
                return True
            return CONSUME_ANY_DEFILER and bool(others - standing(w))

        done = run.seen(consumed, 2.5)
        if run.pad is not None:
            log_pad_consume(run, defiler.unit_id, before, began, done)
        if done is not None:
            taken = others - standing(done) if any(m.unit_id == defiler.unit_id for m in defilers(done)) else set()
            if taken:
                LOG.info(
                    'Macro: Consume took the Defiler %s standing beside the one aimed at (%d): the state is on, one '
                    'Defiler stays out', ', '.join(map(str, sorted(taken))), defiler.unit_id,
                )  # fmt: skip
            run.pause('key')
            return
        world = run.world()
        log_miss(run, world, defiler.unit_id)
        untouched = world.player is not None and world.player.consume is False
        if not untouched or all(m.unit_id != defiler.unit_id for m in defilers(world)):
            raise Abort('Consume: not seen in 2.5s')  # something happened, and not what was meant
        missed = True
        target = next((m for m in defilers(world) if m.unit_id == defiler.unit_id), None)
        over = townsfolk_over(world, target.x, target.y) if target is not None else []
        if over and attempt + 1 < CONSUME_ATTEMPTS:
            LOG.info(
                'Macro: Consume showed nothing, a townsperson (class %d) %.1f from the Defiler: another is summoned',
                over[0].txt_id, math.hypot(over[0].x - defiler.x, over[0].y - defiler.y),
            )  # fmt: skip
            defiler = summon_defiler(run, skip=attempt + 1, tried=tried)
    if missed:
        raise Unconsumed(f'Consume: not seen in 2.5s, {CONSUME_ATTEMPTS} times over')
    raise Unconsumed('something stays too close to the Defiler, or it keeps walking; Consume was not pressed')


def log_consume(run: Run, when: str) -> None:
    """Research: the buff's record, to find where it keeps the time it has left."""
    player = run.world().player
    if player is not None and player.consume_node:
        LOG.info('Macro: Consume record %s (clock %.2f): %s', when, run.clock(), player.consume_node.hex())


def defiler_dance(cast: Casting) -> Tried:
    """End with a newly cast Consume and one Defiler out. Consume is always cast, never taken as good because it is
    active: its time left is not known (user, 2026-10-06). Two demon slots besides the bound demon, an active
    Consume holding one (user, 2026-10-10): a summon with both taken ends the oldest. So a standing Defiler is the
    one consumed, and the one that stays out is summoned after."""
    run, fresh = cast.run, cast.fresh
    log_consume(run, 'before')
    if fresh is not None:  # a new game: nothing is out, and the first summon may have to wait
        defiler = summon_defiler(run, until=fresh.started + LOAD_LIMIT)
        fresh.finish()
    else:
        defiler = in_view(run) or summon_defiler(run)
    try:
        consume(run, defiler)
    except Unconsumed as stop:
        if run.stops(stop):
            raise
        # The prebuff goes on without it: attack mode casts it in the field (buffs.py `consume_due`). 22:35:13 on
        # 2026-10-19: the game was left for it (~15 s)
        LOG.info('Macro: prebuff: no Consume (%s): the prebuff goes on without it; attack mode casts it later', stop)
        if not defilers(run.world()):
            summon_defiler(run)
        return Tried(run.clock())
    log_consume(run, 'after')
    if not defilers(run.world()):
        left_out(run)
    return Tried(run.clock(), cast=True)


class FightCame(Exception):
    """A hostile came within CONSUME_CLEAR during a renewal of Consume in the field (CONSUME_BREAKS): the renewal stops
    at that look. Not an Abort: `Run.seen` would take it for evidence not seen and go on waiting."""


def fight_near(world: World) -> str | None:
    """Why a renewal of Consume stops at this look: the hostiles within CONSUME_CLEAR of the character (hunting/base.py
    `hostiles`, the untouchable among them: they hurt as well; never a Defiler, whose owner may read unset), in words;
    None with none."""
    player = world.player
    if player is None:
        return None
    here = (player.x, player.y)
    near = sorted((math.dist(here, (m.x, m.y)), m.txt_id) for m in hostiles(world) if m.txt_id != DEFILER)
    near = [(units, txt) for units, txt in near if units <= plan.CONSUME_CLEAR]
    if not near:
        return None
    return f'{len(near)} hostile within {plan.CONSUME_CLEAR:.0f}, the nearest (class {near[0][1]}) at {near[0][0]:.1f}'


@contextmanager
def fight_breaks(run: Run) -> Generator[None]:
    """Within the block every look at the game (`Run.observe`, chained) raises `FightCame` once a hostile is within
    CONSUME_CLEAR (CONSUME_BREAKS): the renewal takes no more than a look once a fight comes."""
    if not CONSUME_BREAKS:
        yield
        return
    before = run.observe

    def watch(world: World) -> None:
        if before is not None:
            before(world)
        why = fight_near(world)
        if why is not None:
            raise FightCame(why)

    run.observe = watch
    try:
        yield
    finally:
        run.observe = before


def renew_consume(run: Run) -> None:
    """Consume cast anew mid-run when the buff has run out (user, 2026-10-12: "auto-attack doesn't refresh consume
    buff right now"): a Defiler summoned for it is the one consumed, and another is summoned after. Not the standing
    one: it follows the character with the bound demon beside it. A hostile within CONSUME_CLEAR at any look before
    the Consume lands stops it (`FightCame`, CONSUME_BREAKS). The Defiler left out after it is summoned whatever comes:
    else the upkeep's own Defiler row summons it by the same routine (golden loop_counts.json, walking into reach)."""
    with fight_breaks(run):
        take_prebuff_weapons(run)
        tried: list[tuple[float, float]] = []
        found = to_consume(run) if plan.CONSUME_STANDING else None
        consume(run, found or summon_defiler(run, tried=tried), tried)
    if not defilers(run.world()):
        left_out(run)


def to_consume(run: Run) -> Monster | None:
    """A Defiler standing still (STILL: a walking one makes the aim follow it, 2026-10-12 09:58) drawn in the window
    with nobody in the way of the pointer on it (`crowd`, `townsfolk_over`; the bound demon beside the character crowds
    the one following it), the nearest the character (CONSUME_STANDING); None with none: one is summoned for it."""
    world = run.world()
    rect = run.actuator.keys.focused_window_rect()
    player = world.player
    if rect is None or player is None:
        return None
    aspect = rect[2] / rect[3]
    found = sorted(
        (
            m
            for m in defilers(world)
            if m.mode == STILL
            and on_screen(screen_fraction(player, m.x, m.y, aspect))
            and not crowd(world, m.x, m.y)
            and not townsfolk_over(world, m.x, m.y)
        ),
        key=lambda m: math.dist((player.x, player.y), (m.x, m.y)),
    )
    if not found:
        return None
    here = found[0]
    LOG.info(
        'Macro: Consume on the standing Defiler %d, %.1f off: no summon for it', here.unit_id,
        math.dist((player.x, player.y), (here.x, here.y)),
    )  # fmt: skip
    return here


def left_out(run: Run) -> None:
    """The Defiler left out after a Consume: summoned, or with the mana short (`NoMana`) left to the Defiler's row,
    which summons it once the mana pays (defiler.py DEFILER_PAYS): the Consume made stays a Consume."""
    try:
        summon_defiler(run)
    except NoMana as short:
        LOG.info('Macro: the Defiler left out after the Consume waits (%s): the Defiler row summons it', short)


def consume_again(cast: Casting) -> Tried:
    """Consume cast again (`renew_consume`); a try that fails is logged and the mode goes on. The try
    counts from its start, also when it is stopped half way."""
    run = cast.run
    assert cast.world is not None
    assert cast.key_names is not None
    started = run.clock()
    if run.pad is not None:
        # Not by the pad: a pad summon lands beside the bound demon whatever the heading, and Consume failed on all of
        # four (rca/2026-10-14/run-1904-findings.md §3.6). Renewed in keyboard mode.
        LOG.info(
            'Macro: Consume: not renewed by the pad (its Defiler lands at the feet, by the bound demon); renewed in '
            'keyboard mode, asked again in %.0fs', CONSUME_PAD_WAIT,
        )  # fmt: skip
        return Tried.again(started, CONSUME_RETRY, CONSUME_PAD_WAIT, touched=False)
    cast.buffs.remember(cast.row, started)
    on = cast.world.player is not None and cast.world.player.consume is True
    run.say('Consume renewed before the boss' if on else 'Consume ran out: casting it again')
    try:
        run.keys.update(cast.key_names(cast.world, keys_of(cast.row)))
        renew_consume(run)
    except FightCame as came:
        return put_off(run, came, started, renewing=on)
    except (Abort, ValueError) as stop:
        if run.stops(stop):
            raise
        # A key of the player's stopped it: no failure of the cast, so the next try comes soon.
        wait = CONSUME_RETRY
        tried = Tried(started)
        if 'a key was pressed' in str(stop) or PANEL_OPEN in str(stop) or isinstance(stop, NoMana):
            wait = CONSUME_SOON
            tried = Tried.again(run.clock(), CONSUME_RETRY, wait)
        LOG.info('Macro: no Consume (%s); again in %.0fs', stop, wait)
        return tried
    return Tried(started, cast=True)


def put_off(run: Run, came: FightCame, started: float, *, renewing: bool) -> Tried:
    """The answer to a renewal a fight stopped (`FightCame`): a Consume when its state came on in the look the fight
    showed in (not for `renewing`, a Consume still on before a boss: its state says nothing), else the next try in the
    first quiet, CONSUME_SOON on at the soonest."""
    player = run.world().player
    if not renewing and player is not None and player.consume is True:
        LOG.info('Macro: Consume is on; %s: no Defiler left out for it (the fight row summons one)', came)
        return Tried(started, cast=True)
    LOG.info(
        'Macro: Consume put off for the fight: %s %.1fs into the renewal; again in the first quiet (%.0fs on at the '
        'soonest)', came, run.clock() - started, CONSUME_SOON,
    )  # fmt: skip
    return Tried.again(run.clock(), CONSUME_RETRY, CONSUME_SOON)


def defiler_out(cast: Casting) -> Tried:
    """A Defiler summoned where none is alive (so it ends no Consume). In the quiet by `summon_defiler`; under the held
    strike one key at the first open spot (`Buffs.key`), the next look showing whether it came. A failed try is said
    and asked again after DEFILER_RETRY."""
    run, world = cast.run, cast.world
    assert world is not None
    assert cast.key_names is not None
    started = run.clock()
    try:
        run.keys.update(cast.key_names(world, (SUMMON_DEFILER,)))
        if cast.row.phase == 'fight':
            hand_off(world)
            spot = open_spots(run, world)[0]
            rect = run.actuator.keys.focused_window_rect()
            if run.pad is not None and world.player is not None and rect is not None:
                here = (world.player.x, world.player.y)
                run.pad.aim_place(here, world_point(world.player, *spot, rect[2] / rect[3]))
            else:
                run.actuator.aim(*spot, scatter=(40, 25))
            cast.buffs.key(run, SUMMON_DEFILER)
            LOG.info('Macro: Defiler: summoned under the strike at (%.2f, %.2f) of the window', *spot)
            return Tried(run.clock(), cast=True)
        LOG.info('Macro: Defiler: none out; summoning one')
        run.say('Summoning a Defiler')
        summon_defiler(run)
    except (Abort, ValueError) as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: no Defiler (%s); again in %.0fs', stop, DEFILER_RETRY)
        return Tried(started)
    return Tried(started, cast=True)


def between(run: Run, world: World) -> tuple[float, float] | None:
    """The window fraction the fight's Defiler is summoned at between the character and a tier 4-5 Herald pack
    (combat/pack.py PETS_BETWEEN, defiler.py `world_spot`): on the screen and on ground a summon stands on (the level
    map's, where known); None else."""
    spot = world_spot(world)
    rect = run.actuator.keys.focused_window_rect()
    player = world.player
    if spot is None or rect is None or player is None:
        return None
    ground = run.reads.ground()
    if ground and not standable(ground, (player.x, player.y), spot):
        return None
    fraction = ground_fraction(player, *spot, rect[2] / rect[3])
    if not on_screen(fraction):
        return None
    LOG.info('Macro: Defiler: summoned between the character and the pack at (%.1f, %.1f)', *spot)
    return fraction


# Binds that bring no demon are given up for a while (rca/2026-10-21/demon-lost-findings.md cause 5): after the Urdar's
# death three Bind Demons went on Dark Archers of the tier 5 pack (15:41:41.9, 46.1, 49.8) and no ally came. The game's
# data lets it bind them: skills.txt 382 (Bind Demon) TargetableOnly 1, LineOfSight 4, pettype binddemon, petmax 1, the
# capture a chance (Param3 12 "Growthrate/start for % capture", Param4 64 "Cap for % capture", Param8 100 "Synergy
# Chance to Bind w/ Death Mark", all "referenced in monpet.txt", which the dump lacks), a channel (srvmissilea
# binddemonchannelmaker, anim SQ, seqnum 6, interrupt 1); monstats cr_archer3 (*hcIdx 162) demon 1, montype
# corruptrogue equiv1 demon, monstats2 isSel 1: a demon `bind.bindable` keeps. No sequence mode showed on the character
# after any of the three keys, and the three targets died 0.3, 1.1 and 0.9 s after them under the strike. True: after
# BIND_MISSES binds in a row within BIND_FORGET s with none bound (the row is asked only while none is out, so a bind
# asked again is one that brought none), none for BIND_PAUSE s, said. False: one every BIND_RETRY s while due.
BIND_GIVE_UP = True
BIND_MISSES = 2
BIND_FORGET = 20.0  # seconds: an older bind counts for nothing
BIND_PAUSE = 30.0
BINDS: weakref.WeakKeyDictionary[object, list[float]] = weakref.WeakKeyDictionary()  # executor -> its binds' clocks


def bind(cast: Casting) -> Tried:
    """Bind Demon on the demon chosen (bind.py `bind_target`): the shared cast on a monster. With no key the macro can
    press it is said and asked again after BIND_NO_KEY, not a stop of the fight. Binds that brought no demon are given
    up for BIND_PAUSE (BIND_GIVE_UP)."""
    run = cast.run
    started = run.clock()
    if not binding.BIND_DEMON_CASTS:  # the player binds it himself (bind.py BIND_DEMON_CASTS): never pressed
        return Tried.again(started, BIND_RETRY, BIND_NO_KEY, touched=False)
    made = BINDS.setdefault(cast.buffs, [])
    made[:] = [at for at in made if 0.0 <= started - at <= BIND_FORGET]
    if BIND_GIVE_UP and len(made) >= BIND_MISSES:
        LOG.info(
            'Macro: bind: %d %s casts in %.0fs brought no demon: none for %.0fs', len(made), skill_name(BIND_DEMON),
            started - made[0], BIND_PAUSE,
        )  # fmt: skip
        made.clear()
        return Tried.again(started, BIND_RETRY, BIND_PAUSE, touched=False)
    try:
        tried = cast.buffs.shared(cast)
    except (Abort, ValueError) as stop:
        if run.stops(stop):
            raise
        LOG.info('Macro: bind: no %s (%s); again in %.0fs', skill_name(BIND_DEMON), stop, BIND_NO_KEY)
        return Tried.again(started, BIND_RETRY, BIND_NO_KEY, touched=False)
    if tried.cast and tried.at is not None:
        made.append(tried.at)
    return tried


# Under the held strike the game's record of the unit under the pointer (`Run.hovered`) stays on what it named before,
# mostly the strike's own target, wherever the pointer goes: all 276 Engorge misses of the takes 20261020T2* came with
# the strike held, the live monster named stood a median 8.6 units off the corpse aimed at (96 of 172 more than 8),
# and 217 of 253 pairs of misses named the same unit at two corpses. So the record read before the pointer moves says
# what the read after it would. True (the player, 2026-10-20 ~23:20, of the batch identify: "we're not wasting time
# identifying individually every separate item but doing batch when we actually need it", "I'd like to see more this
# kind of mindset in other areas"; rca/2026-10-20/lazy-work-findings.md §2): with the strike held, a record that names
# a live monster or an item is a try not made, nothing touched, the next in ENGORGE_HOVER_RETRY; for a hurt demon
# (buffs.py `demon_hurt`) the strike is let go first instead, so that the record follows the pointer. A unit among the
# corpses read now is no live monster (26 of those misses named one the strike had just killed). False: the pointer
# put on the corpses and the record read there, the look's live monsters as they were.
ENGORGE_HOVER_FIRST = False
ENGORGE_HOVER_RETRY = 1.0  # seconds to the next look at the record while the held strike keeps it
# A try for a pet in danger that is refused or misses is made again at once with another corpse (the findings' cause
# 2: at 15:41:34.1 two corpses were refused, a live archer named under the pointer, and the next try waited 2.5 s, the
# Urdar 128 -> 34 meanwhile; at 15:41:36.6 the key went with an object, type 2, under the pointer and no heal came).
# True, with a pet in danger (pets.py `perilous`, buffs.py PET_ENGORGE): the held strike let go before the pointer
# moves, so that the record follows it (the comment above); up to ENGORGE_DANGER_LOOKS corpses within
# ENGORGE_DANGER_REACH; the next try ENGORGE_DANGER_RETRY after one refused. Always: an object under the pointer keeps
# the cast off the corpse as an item's label does (`covers`). False: ENGORGE_LOOKS within ENGORGE_REACH, ENGORGE_RETRY
# after, an object taken as nothing, as before.
ENGORGE_RETRY_AT_ONCE = True
ENGORGE_DANGER_LOOKS = 4
ENGORGE_DANGER_REACH = 30.0  # world units; on the screen still
ENGORGE_DANGER_RETRY = 0.25  # seconds
# 2026-10-23 (the player: "try to push exp/hour more"; rca/2026-10-23/exp-casts-findings.md §1): a corpse with a live
# unit standing within ENGORGE_CLEAR of it is one the pointer lands on that unit's body, not the corpse. In the take
# 20261022T234119Z-68 (Tal Rasha's Tomb, the Gorebelly pack) 41 tries were refused against 14 keyed: the nearest live
# monster stood a median 2.0 units off the corpse of a refused try (25 of 37 within 3), 7.4 off one keyed (6 of 40
# within 3, with the take -66's); 29 refusals in one 121 s fight, each a pointer move off the strike's target. True:
# the look's units (pets too: the record names them) keep the corpses within ENGORGE_CLEAR out of the tries; with no
# clear corpse nothing is touched and the row is asked again in its retry, while a pet in danger still tries the
# crowded ones after the clear ones. False: the nearest corpses whatever stands on them, as before.
ENGORGE_CLEAR_AIM = True
ENGORGE_CLEAR = 3.0  # world units from a live unit's feet to the corpse within which the pointer finds the unit
# The corpses whose Engorge showed nothing are left out of the tries (pets.py ENGORGE_LEARNS, `PetWatch.refused`)
REFUSED_SAID_SECONDS = 10.0  # between two "each of the corpses in reach showed nothing" lines
REFUSED_SAID: list[float] = [-math.inf]
# What under the pointer stays over a corpse (an object, an item's label: they do not walk off), so a corpse it covers
# is refused for good (pets.py ENGORGE_LEARNS). Live 16:09:12-16:10:28 (take 20261023T130907Z-67): 50 tries refused on
# three corpses under objects (type 2), each with the strike let go first; 22.4 s of 76 s had the strike up for
# Engorge's tries. A live monster over one is not: it moves.
STILL_COVERS = (OBJECT_UNIT, ITEM_UNIT)
# Engorge takes a foe's corpse only (2026-10-24, rca/2026-10-24/engorge-findings.md): in the take 20261024T203210Z-110
# (Bloody Foothills) the 4 keys on the corpse of an Act 5 Combatant (monstats 522, of the player's alignment) showed
# no engorge missile (710/718) and no cast, against 26 of 30 on a foe's. True: a corpse whose unit the look reads as an
# ally (`Monster.ally`: the Combatants, a pet, the mercenary) is left out of the tries. False: every corpse, as before.
ENGORGE_FOE_CORPSES = True  # on 2026-10-25 03:30 with pets.PET_DEMONS_ONLY (the same slow arena set as off)


def clear_corpses(
    near: Sequence[tuple[int, float, float]],
    world: World,
    here: tuple[float, float],
    dead: set[int],
    *,
    crowded_too: bool,
) -> list[tuple[int, float, float]]:
    """The corpses to try, nearest first: with ENGORGE_CLEAR_AIM those with no live unit of the look (`dead`, the
    corpses read now, left out) within ENGORGE_CLEAR (then, with `crowded_too`, the others); all of them else."""
    by_distance = sorted(near, key=lambda corpse: math.dist(here, corpse[1:]))
    if not ENGORGE_CLEAR_AIM:
        return by_distance
    standing = [(m.x, m.y) for m in world.monsters if m.unit_id not in dead]
    clear = [c for c in by_distance if all(math.dist(c[1:], at) > ENGORGE_CLEAR for at in standing)]
    return clear + [c for c in by_distance if c not in clear] if crowded_too else clear


def covers(over: tuple[int, int] | None, alive: set[int]) -> bool:
    """Whether the unit the record names keeps Engorge off the corpse: a live monster, an item's label, an object
    (ENGORGE_RETRY_AT_ONCE)."""
    if over is None:
        return False
    if over[0] == ITEM_UNIT or (ENGORGE_RETRY_AT_ONCE and over[0] == OBJECT_UNIT):
        return True
    return over[0] == MONSTER_UNIT and over[1] in alive


def engorge(cast: Casting) -> Tried:
    """Engorge on the nearest corpse in view within ENGORGE_REACH. With no corpse there nothing is
    touched; with one that the pointer could not be kept on, the pointer was moved and no cast made.
    Under the held strike the record of what is under the pointer is read first (ENGORGE_HOVER_FIRST). For a pet in
    danger more corpses, further, the strike let go first and the next try soon (ENGORGE_RETRY_AT_ONCE); the key is
    told to the pets' watch, which judges its heal (pets.py `keyed`)."""
    run, world, aspect = cast.run, cast.world, cast.aspect
    assert world is not None
    assert aspect is not None
    assert cast.key_names is not None
    player = world.player
    assert player is not None
    assert run.corpses is not None
    watch = pets.watch_of(getattr(cast.buffs, 'cast_at', None))
    urgent = ENGORGE_RETRY_AT_ONCE and plan.PET_ENGORGE and watch.perilous(run.clock())
    # The pack's Engorge (buffs.py ENGORGE_PACK_FIRST) lets the strike go too and is asked again by its own cadence:
    # live at 16:16:39-42 its tries were refused three times in 3 s (the held strike's record on a live Fallen), each
    # asked again at once as `engorge_every`'s 15 s left it overdue against ENGORGE_PACK_SECONDS.
    packed = not urgent and watch.packed(run.clock())
    reach, looks = (ENGORGE_DANGER_REACH, ENGORGE_DANGER_LOOKS) if urgent else (ENGORGE_REACH, ENGORGE_LOOKS)
    every, retry = (danger_every(watch), ENGORGE_DANGER_RETRY) if urgent else (engorge_every(world), ENGORGE_RETRY)
    if packed:
        every = min(every, plan.ENGORGE_PACK_SECONDS)
    here = (player.x, player.y)
    corpses = run.corpses()
    near = [
        corpse
        for corpse in corpses
        if math.dist(here, corpse[1:]) <= reach and on_screen(ground_fraction(player, *corpse[1:], aspect))
    ]
    if ENGORGE_FOE_CORPSES:
        allied = {m.unit_id for m in world.monsters if m.ally}
        near = [corpse for corpse in near if corpse[0] not in allied]
    if not near:
        return Tried.again(run.clock(), every, retry, touched=False)
    if pets.ENGORGE_LEARNS and watch.refused:
        fresh = [corpse for corpse in near if corpse[0] not in watch.refused]
        if not fresh:
            if run.clock() - REFUSED_SAID[0] >= REFUSED_SAID_SECONDS:
                REFUSED_SAID[0] = run.clock()
                LOG.info('Macro: no Engorge: each of the %d corpses in reach showed nothing before', len(near))
            return Tried.again(run.clock(), every, retry, touched=False)
        near = fresh
    tries = clear_corpses(near, world, here, {unit for unit, _, _ in corpses}, crowded_too=urgent)[:looks]
    if not tries:
        LOG.info(
            'Macro: no Engorge: each of the %d corpses in reach has a live unit within %.1f', len(near), ENGORGE_CLEAR
        )
        return Tried.again(run.clock(), every, retry, touched=False)
    alive = {m.unit_id for m in world.monsters}
    let_go = getattr(cast.buffs, 'let_go', None)
    if ENGORGE_HOVER_FIRST:
        alive -= {unit for unit, _, _ in corpses}
        if run.pad is None and run.hovered is not None and let_go is not None:
            over = run.hovered()
            if covers(over, alive):
                if not (demon_hurt(world) or urgent or packed):
                    LOG.info('Macro: no Engorge: the held strike keeps the pointer record on %s; not moved', over)
                    return Tried.again(run.clock(), every, ENGORGE_HOVER_RETRY, touched=False)
                LOG.info('Macro: Engorge for a hurt demon: the strike let go, the pointer record on %s', over)
                let_go()
    elif (urgent or packed) and run.pad is None and let_go is not None:
        let_go()  # the record follows the pointer once the strike is let go
    run.keys.update(cast.key_names(world, (ENGORGE,)))
    # The nearest corpse the pointer really has under it (a live monster often stands on one).
    for unit, x, y in tries:
        if run.pad is not None:
            # Controller mode: the client's target has to name the corpse (macros/pad.py).
            if not run.pad.aim_unit(MONSTER_UNIT, unit, here, (x, y), f'the corpse {unit}'):
                continue
            without = pets.bare(world, run.reads.unit_states) if pets.ENGORGE_LEARNS else frozenset()
            cast.buffs.key(run, ENGORGE)
            if run.pad.pressed:
                watch.keyed(run.clock(), unit, without)
            # Whether Engorge's target (controllerskillsettings.json targetGroup 0, the monsters) can name a corpse
            # at all: the aim's own `Pad target:` lines, and this one for a press (controller-gaps.md step 3).
            LOG.info(
                'Pad target: Engorge on the corpse %d at (%.1f, %.1f), %.1f away, by %s: %s',
                unit, x, y, math.dist(here, (x, y)), run.keys.get(ENGORGE),
                "pressed with the client's target on it" if run.pad.pressed else 'not pressed (the target moved off)',
            )  # fmt: skip
            return Tried(run.clock(), cast=run.pad.pressed)
        run.actuator.aim(*ground_fraction(player, x, y, aspect), scatter=(3, 3))
        over = None
        if run.hovered is not None:
            run.pace.sleep(HOVER_SECONDS)
            over = run.hovered()
            # Not cast with a live monster or an item's label under the pointer; with nothing
            # there it is (whether the record shows a corpse at all is not known yet).
            if covers(over, alive):
                LOG.info('Macro: no Engorge at (%.1f, %.1f): under the pointer %s, not the corpse %d', x, y, over, unit)
                if pets.ENGORGE_LEARNS and over is not None and over[0] in STILL_COVERS:
                    watch.refuse(unit)  # an object or an item's label stays where it is: never tried again
                continue
        without = pets.bare(world, run.reads.unit_states) if pets.ENGORGE_LEARNS else frozenset()
        cast.buffs.key(run, ENGORGE)
        at = run.clock()
        watch.keyed(at, unit, without)
        LOG.info(
            'Macro: Engorge on the corpse %d at (%.1f, %.1f), %.1f away; under the pointer %s',
            unit, x, y, math.dist(here, (x, y)), over,
        )  # fmt: skip
        return Tried(at, cast=True)
    # the pointer was moved: the strike's aim is put back
    return Tried.again(run.clock(), every, retry)


# The sigil goes under the monster where it stands at the key, read again then (the player, 2026-10-20 ~23:05): the
# fight's rows are asked with the look before the strike, and a Death Mark cast first makes that 0.3-0.5 s old. Diablo,
# walking up at 10 units a second, had his sigil at 23:01:55 laid where he had stood, 11 units off him (the take
# 20261020T195849Z-108: the sigil at (7794.5, 5293.5), Diablo at (7803.0, 5287.0) as it showed). False: the look's.
SIGIL_AIM_AFRESH = True
# The sigils' memory per executor (`SigilWatch`): the executor (macros/buffs.py `Buffs`) holds no caster's own.
WATCHES: weakref.WeakKeyDictionary[object, SigilWatch] = weakref.WeakKeyDictionary()


def watch_of(executor: object) -> SigilWatch:
    """The memory of the sigil that lies, of this executor's casts."""
    found = WATCHES.get(executor)
    if found is None:
        found = WATCHES[executor] = SigilWatch()
    owner = getattr(executor, 'cast_at', None)
    if owner is not None:
        plan.LAID.owner, plan.LAID.watch = owner, found  # for buffs.py `opener_due` (SIGIL_OPENER)
    return found


def afresh(cast: Casting) -> Casting:
    """The cast with the world read now, the target where it stands now (SIGIL_AIM_AFRESH); as it was when the target
    is not read again."""
    if not SIGIL_AIM_AFRESH or cast.target is None:
        return cast
    world = cast.run.world()
    found = next((m for m in world.monsters if m.unit_id == cast.target.unit_id), None)
    if world.player is None or found is None:
        return cast
    return replace(cast, world=world, target=found)


def in_flight(run: Run, world: World | None) -> tuple[bool, tuple[float, float, float] | None]:
    """Whether the missiles were read, and the character's sigil among them as (x, y, radius) (skills.py
    SIGIL_MISSILES), None with none."""
    if run.flights is None or world is None or world.player is None:
        return False, None
    try:
        found = run.flights(frozenset(SIGIL_MISSILES))
    except OSError, ValueError, struct.error:
        return False, None
    mine = [(x, y, SIGIL_MISSILES[kind]) for owner, kind, x, y in found if owner == world.player.unit_id]
    return True, (mine[-1] if mine else None)


def sigil(cast: Casting) -> Tried:
    """Sigil: Lethargy on the ground under an elite (slows it, lowers its defence): the executor's
    cast on the ground under a monster, with the sigil's own wait when that is not in view. A monster kept in its
    sigil (buffs.py `kept`) is looked at every SIGIL_LOOK s and gets one when `keep_reason` names why; none sooner than
    SIGIL_GAP after the last."""
    run, target, world = cast.run, cast.target, cast.world
    if herald_pack.SIGIL_COVER and target is not None and herald_pack.in_pack(target.tier):
        return pack_sigil(cast)
    if target is not None and target.txt_id == OMEN_TXT:
        return omen_sigil(cast)
    if target is not None and target.txt_id == OPENER_TXT:
        return opener_sigil(cast)
    watch = watch_of(cast.buffs)
    now = run.clock()
    area = world.player.area if world is not None and world.player is not None else None
    keeping = target is not None and kept(target)
    every = SIGIL_LOOK if keeping else SIGIL_SECONDS
    why, again = None, False
    if keeping and target is not None:
        again = watch.lies(now, area)  # one lies: this one is said with why
        judged = watch.age(now) >= SIGIL_SHOWS
        words = run.reads.unit_states(target) if judged else None
        by_place = words is None or watch.unshown.get(target.unit_id, 0) >= SIGIL_UNSHOWN
        seen, lying = in_flight(run, world) if judged and by_place else (False, None)
        why = keep_reason(watch, target, now, area, words, lying, seen)
        if why is None:
            # It stands in its sigil: looked at again in SIGIL_LOOK, or when the sigil runs out or a Herald's is old
            return Tried(min(now, watch.next_due(target) - SIGIL_LOOK), touched=False)
        if again and watch.age(now) < SIGIL_GAP:
            assert watch.at is not None
            return Tried(watch.at + SIGIL_GAP - every, touched=False)
    aimed, blind = afresh(cast), False
    if SIGIL_SIGHT and aimed.target is not None and aimed.world is not None and aimed.world.player is not None:
        me = aimed.world.player
        blind = not sight_of(run, aimed.world, (me.x, me.y))((aimed.target.x, aimed.target.y))
        if blind and refused(run, aimed.world, watch, now):
            unseen(now, f'{label(aimed.target)} at ({aimed.target.x:.1f}, {aimed.target.y:.1f})')
            return Tried.again(now, every, SIGIL_LOOK, touched=False)
    tried = cast.buffs.shared(aimed)
    if not tried.cast:
        # Off the screen (the blades reach further than it shows): no sigil now, asked again in a second.
        return Tried.again(now, every, 1.0)
    if aimed.target is not None and tried.at is not None:
        if keeping and why is not None and why.startswith(UNSHOWN) and watch.unit == aimed.target.unit_id:
            watch.unshown[aimed.target.unit_id] = watch.unshown.get(aimed.target.unit_id, 0) + 1
        watch.lay(aimed.target.unit_id, (aimed.target.x, aimed.target.y), area, tried.at)
        watch.blind = tried.at if blind else None
        if again:
            here = aimed.target
            LOG.info('Macro: sigil under %s at (%.1f, %.1f): %s', label(here), here.x, here.y, why)
    return tried


def omen_sigil(cast: Casting) -> Tried:
    """The sigil laid at a pending Herald omen's spot before its pack shows (buffs.py OMEN_SIGIL, `omen_anchor`'s
    stand-in): cast on the ground there, once; off the screen it is asked again in a second."""
    run, target = cast.run, cast.target
    assert target is not None
    now = run.clock()
    tried = cast.buffs.shared(cast)
    if not tried.cast or tried.at is None:
        return Tried.again(now, SIGIL_LOOK, 1.0)
    world = cast.world
    area = world.player.area if world is not None and world.player is not None else None
    watch_of(cast.buffs).lay(target.unit_id, (target.x, target.y), area, tried.at)
    LOG.info("Macro: sigil: at the Herald's coming (%.1f, %.1f), before its pack shows", target.x, target.y)
    return tried


def opener_sigil(cast: Casting) -> Tried:
    """A fight's group's sigil first (buffs.py SIGIL_OPENER, `opener_target`'s stand-in): the group and its disc
    (`opening`) of the world read now, laid there unless the one that lies covers OPENER_KEEP of the group (by the
    missile read, its radius too, else where it was aimed); none sooner than SIGIL_GAP after the last. Off the screen
    it is asked again in a second."""
    run, target = cast.run, cast.target
    assert target is not None
    watch = watch_of(cast.buffs)
    now = run.clock()
    world = run.world() if SIGIL_AIM_AFRESH else cast.world
    if world is None or world.player is None:
        world = cast.world
    if world is None or world.player is None:
        return Tried(now, touched=False)
    player = world.player
    here, area = (player.x, player.y), player.area
    foes = [m for m in world.monsters if not m.ally and m.owner == NO_OWNER]
    found = plan.opening(here, foes, [(d.x, d.y) for d in demons(world)])
    if found is None:
        return Tried(now, touched=False)
    seen, lying = in_flight(run, world)
    gone = seen and lying is None and watch.age(now) >= SIGIL_SHOWS  # none of the character's in flight
    if watch.lies(now, area) and not gone and watch.age(now) <= SIGIL_LASTS - SIGIL_EARLY:
        at = (lying[0], lying[1]) if lying is not None else watch.place
        assert at is not None
        share = plan.covers(at, found, lying[2] if lying is not None else SIGIL_RADIUS)
        if share >= OPENER_KEEP:
            return Tried(now, touched=False)  # the one that lies holds the group
        if watch.age(now) < SIGIL_GAP:
            assert watch.at is not None
            return Tried(watch.at, touched=False)  # the row asks again SIGIL_GAP after it
        why = f'the one that lies covers {share:.0%} of it'
    elif watch.lies(now, area) and not gone:
        why = f'the sigil runs out in {max(0.0, SIGIL_LASTS - watch.age(now)):.1f} s'
    else:
        why = 'no sigil of the character lies'
    tried = cast.buffs.shared(replace(cast, world=world, target=replace(target, x=found.spot[0], y=found.spot[1])))
    if not tried.cast or tried.at is None:
        return Tried.again(now, SIGIL_GAP, 1.0)  # off the screen: asked again in a second
    watch.lay(target.unit_id, found.spot, area, tried.at)
    LOG.info(
        'Macro: sigil first: %s, at (%.1f, %.1f), %.0f%% of it there within %.1f s: %s',
        found.why, *found.spot, 100 * plan.covers(found.spot, found), OPENER_LEAD, why,
    )  # fmt: skip
    return tried


# 2026-10-23 (the player: "try to push exp/hour more"; rca/2026-10-23/exp-casts-findings.md §2): a pack's sigil was laid
# again whenever the one that lay covered under SIGIL_HALF of the pack and a disc covered one member more. Its ground
# lasts 19 s (missiles.txt sigillethargy* Range 100+25 a level frames: SIGIL_LASTS), but a sigil aimed at the disc
# lands on the feet of a monster whose body is under the pointer, up to 6 units off the disc (the missiles of the take
# 20261022T233432Z-66), and the pack shifts as it fights: the next look found the one that lay covering 5-6 of 15
# against the disc's 9 and laid it again, 42 of that take's 50 sigils, one every 1.3-3 s. True: one that covers
# SIGIL_KEEP_SHARE of what the best disc would (the Herald weighted) is kept until it runs out or the pack leaves it
# (28 of those 41 recasts not made). False: any disc covering more lays it again, as before.
SIGIL_KEEP_SHARE_ON = True
SIGIL_KEEP_SHARE = 0.5

# 2026-10-24 (the LONG_FIGHT of the take 20261024T075426Z-51, an elite DuneBeast pack in Harem Level 2: 34 s, 13 sigil
# keys, 3 sigils): the game lays no sigil at a spot behind a wall. The key put the sigil on the right button for 80 ms,
# the character stayed in neutral (mode 1) or went on striking, and no missile 686 showed; the keys that laid one had a
# clear line. Of the 272 sigil keys of the takes of 2026-10-23 and -24 matched to their spot, those whose straight line
# from the character crossed no wall (travel.py `clear_line`) laid one 207 times of 212, those through a wall 26 of 60
# (the game's own sight test is not the walkable grid: half of those still land, but no rule told which). Not the read:
# the patch of 2026-10-23 19:03 left the missile read whole (the two that landed after the first were seen and kept).
# True: a sigil goes at a spot in sight first, the pack's at the best disc in sight (`sighted_disc`); with none, one
# key through the wall, and when that one lays no missile (`refused`), none out of sight for SIGIL_REFUSED_SKIP from
# its key, looked at again in SIGIL_LOOK (the coordinator, 2026-10-24: keep the through-wall ones that land). Replayed
# on the 63 keys through a wall of those takes (29 landed, 34 refused): 49 pressed, 28 landed, 21 refused; a key only
# in sight would have lost the 29.
# False: through walls, as before.
SIGIL_SIGHT = True
SIGIL_REFUSED_SKIP = 3.0
SIGHT_SAID = 3.0  # seconds between two "out of sight" lines
_unseen_said = [-math.inf]


def refused(run: Run, world: World, watch: SigilWatch, now: float) -> bool:
    """Whether the last key was one out of sight (`SigilWatch.blind`) under SIGIL_REFUSED_SKIP ago that laid no
    sigil: none of the character's in flight SIGIL_SHOWS after it (`in_flight`), or not looked for yet. With the
    missiles unread it counts as refused: one key out of sight a SIGIL_REFUSED_SKIP."""
    if watch.blind is None or watch.blind != watch.at or not 0.0 <= watch.age(now) < SIGIL_REFUSED_SKIP:
        return False
    if watch.age(now) < SIGIL_SHOWS:
        return True
    return in_flight(run, world)[1] is None


def sight_of(run: Run, world: World, here: tuple[float, float]) -> Callable[[tuple[float, float]], bool]:
    """Whether the character sees a ground point: no wall or closed door on the straight line (travel.py
    `clear_line`); every point with the level's ground unread."""
    ground = run.reads.ground()
    return lambda spot: clear_line(ground, world.doors, here, spot)


def sighted_disc(
    here: tuple[float, float],
    pack: Sequence[herald_pack.Member],
    radius: float,
    sees: Callable[[tuple[float, float]], bool],
) -> tuple[tuple[float, float], str] | None:
    """The disc in sight (`sight_of`) that covers the most of the pack, the Herald weighted (combat/pack.py
    `cover_weight`): at a member or at the middle of what its disc covers, the nearer of two alike; None with none."""
    found: list[tuple[float, float]] = []
    for member in pack:
        inside = [m.at for m in herald_pack.covering(member.at, pack, radius)]
        found += [member.at, (sum(p[0] for p in inside) / len(inside), sum(p[1] for p in inside) / len(inside))]
    seen = [spot for spot in found if sees(spot)]
    if not seen:
        return None
    best = max(seen, key=lambda spot: (herald_pack.cover_weight(spot, pack, radius), -math.dist(spot, here)))
    return best, f'in sight, the disc covering {len(herald_pack.covering(best, pack, radius))} of {len(pack)}'


def unseen(now: float, what: str) -> None:
    """Says that no sigil is laid, the spot being out of sight, once in SIGHT_SAID."""
    if now - _unseen_said[0] >= SIGHT_SAID or now < _unseen_said[0]:
        _unseen_said[0] = now
        LOG.info('Macro: sigil: %s behind a wall: none laid (the key out of sight before laid none)', what)


def pack_sigil(cast: Casting) -> Tried:
    """A tier 4-5 Herald pack's sigil (combat/pack.py SIGIL_COVER): at the disc that covers the most of the pack, or on
    the demon that holds it (`sigil_spot`), of the world read now. Laid again only when the one that lies covers under
    SIGIL_HALF of the pack and a disc covers more (with SIGIL_KEEP_SHARE_ON: over twice as much), or when it runs out
    (SIGIL_EARLY); none sooner than SIGIL_GAP after the last. Where it lies is the missile read (its radius too), else
    where it was aimed; who stands in it is told by place (SIGIL_EDGE inside the radius), not by fifteen monsters'
    state words a look."""
    run, anchor = cast.run, cast.target
    assert anchor is not None
    watch = watch_of(cast.buffs)
    now = run.clock()
    world = run.world() if SIGIL_AIM_AFRESH else cast.world
    if world is None or world.player is None:
        world = cast.world
    if world is None or world.player is None:
        return Tried(now, touched=False)
    player = world.player
    here, area = (player.x, player.y), player.area
    hostiles = [m for m in world.monsters if not m.ally and m.owner == NO_OWNER]
    pack = herald_pack.nearby(here, herald_pack.members(hostiles))
    if not pack:
        return Tried(now, touched=False)
    seen, lying = in_flight(run, world)
    radius = (lying[2] if lying is not None else SIGIL_RADIUS) - SIGIL_EDGE
    gone = seen and lying is None and watch.age(now) >= SIGIL_SHOWS  # none of the character's in flight
    sent = [(d.x, d.y) for d in demons(world)]
    if engage.sigil_waits():
        # The T5 pack's plan (combat/engage.py ENGAGE_PLAN): the sigil goes where the demons meet the pack, once
        # the mark has put them there
        return Tried(now, touched=False)
    spot, where = herald_pack.sigil_spot(here, pack, sent, radius)
    if watch.lies(now, area) and not gone and watch.age(now) <= SIGIL_LASTS - SIGIL_EARLY:
        at = (lying[0], lying[1]) if lying is not None else watch.place
        assert at is not None
        inside = herald_pack.covering(at, pack, radius)
        planned = engage.sigil_kept(at, [m.at for m in pack], here, sent)
        if planned is True:
            return Tried(now, touched=False)  # it lies where the melee is (ENGAGE_PLAN)
        if planned is None:
            if len(inside) >= herald_pack.SIGIL_HALF * len(pack):
                return Tried(now, touched=False)
            held, best = herald_pack.cover_weight(at, pack, radius), herald_pack.cover_weight(spot, pack, radius)
            if best <= held:
                return Tried(now, touched=False)  # no disc covers more: kept
            if SIGIL_KEEP_SHARE_ON and held >= SIGIL_KEEP_SHARE * best:
                return Tried(now, touched=False)  # it holds half of what a new one would at least: kept
        if watch.age(now) < SIGIL_GAP:
            assert watch.at is not None
            return Tried(watch.at + SIGIL_GAP - SIGIL_LOOK, touched=False)
        why = (
            f'the melee is {math.dist(at, spot):.1f} off the one that lies'
            if planned is False
            else f'the one that lies covers {len(inside)} of {len(pack)}'
        )
    elif watch.lies(now, area) and not gone:
        why = f'the sigil runs out in {max(0.0, SIGIL_LASTS - watch.age(now)):.1f} s'
    else:
        why = 'no sigil of the character lies'
    blind = False
    if SIGIL_SIGHT:
        sees = sight_of(run, world, here)
        if not sees(spot):
            other = sighted_disc(here, pack, radius, sees)
            if other is not None:
                spot, where = other
            elif refused(run, world, watch, now):
                unseen(now, f"the pack's disc at ({spot[0]:.1f}, {spot[1]:.1f}) and every other")
                return Tried.again(now, SIGIL_LOOK, SIGIL_LOOK, touched=False)
            else:
                blind, where = True, f'{where}, behind a wall (one try)'
    tried = cast.buffs.shared(replace(cast, world=world, target=replace(anchor, x=spot[0], y=spot[1])))
    if not tried.cast or tried.at is None:
        # Off the screen: no sigil now, asked again in a second.
        return Tried.again(now, SIGIL_LOOK, 1.0)
    watch.lay(anchor.unit_id, spot, area, tried.at)
    watch.blind = tried.at if blind else None
    LOG.info("Macro: sigil: the pack's at (%.1f, %.1f), %s within %.1f: %s", *spot, where, radius, why)
    return tried


CASTERS: dict[str, Caster] = {
    'defiler dance': defiler_dance,
    'consume': consume_again,
    'engorge': engorge,
    'sigil': sigil,
    'defiler': defiler_out,
    'bind': bind,
    **CTA_CASTERS,  # Call to Arms (macros/cta.py)
}
