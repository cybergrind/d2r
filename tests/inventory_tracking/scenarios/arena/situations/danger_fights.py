"""The thirteen most dangerous fights of the takes of 2026-10-20 and 21 beside the Fane's death, as situations
(rca/2026-10-21/fane-death-sim-findings.md §9; the player, 2026-10-22: "we must be sure that we don't have this issue
again anytime soon"): each cut with the Fane's steps (fane_death.py), so each plays with the level's walls, the blows
capped at the game's most and raised by each unit's own stat 25 as the take read it (shown to the macro too, as the
live client shows it), the Terror Zone's level, the takes' pace, the client's 0.4 s life read and an awareness of 35.

The fights were picked in round 1 from the takes (the lowest life share, the biggest one-second losses, the
rejuvenations drunk); FIGHTS has each one's take and the clock time it starts at. Each plays SECONDS from there.

Where each part comes from, beyond record.py `from_take` and the Fane's steps (`fane_death.out_of_sight`,
`damage_percents`, `pet`):

- the curses: Amplify Damage and Decrepify (states 9 and 60) on the physical share, Conviction and Lower Resist
  (states 28 and 61) on the elements', at the frames that show them on or off, each share as the frame's `r` reading
  lets through (`curses_of`); an off puts back the share the reading then shows, on both weapon sets alike;
- Battle Orders (state 32): up at the start and out where the take shows it go, the most life with it over without
  as the frames show it then; never out in the window: out past the play; not up: `Orders(up=False)`, for the macro to
  cast (`orders_of`); its cast is not known to the macro;
- the resistances of the set in hand: the start's `r` reading, where the take holds one (`hero_of`);
- Teleport: the staff's charges where the frames' `w` shows them (record.py), else the character's own (Enigma);
- types played hand to hand: the shooters (mobs.py `shooter`) the take's hurts show striking within 3.5 (`melee_of`);
- the pace: each type's walk and run as the takes of 2026-10-20 to 22 measure it over 0.5 s windows (fane_death.py
  WINDOWED; a type it lacks from SPEEDS_FILE, the round's frame-to-frame scan, which reads fast closers twice as fast).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.danger_fights --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.danger_fights --seeds 20
"""

import argparse
import datetime
import functools
import json
import statistics
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path
from typing import Any

from inventory_tracking.combat.mechanics.life import zone_level
from inventory_tracking.combat.mechanics.tables import points_of
from inventory_tracking.game.layout import FULL_REJUVENATION
from inventory_tracking.takes.takes import Take
from tests.inventory_tracking.macros.fakes import HUNT_SLOTS
from tests.inventory_tracking.scenarios.arena import cut as cutting
from tests.inventory_tracking.scenarios.arena.cut import HELL_PENALTY, KINDS, through
from tests.inventory_tracking.scenarios.arena.mobs import shooter
from tests.inventory_tracking.scenarios.arena.scene import Mob, WeaponSet
from tests.inventory_tracking.scenarios.arena.situations.fane_death import (
    ALL_OFF,
    ALL_ON,
    AWARE,
    CTA,
    LIFE_READ,
    MAIN,
    MOST_WITH,
    MOST_WITHOUT,
    REACH,
    RULES,
    WINDOWED,
    damage_percents,
    head,
    out_of_sight,
    pet,
    play,
)
from tests.inventory_tracking.scenarios.arena.situations.record import TAKES, from_take, last
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load
from tests.inventory_tracking.scenarios.arena.situations.stage import Orders, Stage


ZONE = datetime.timezone(datetime.timedelta(hours=3))  # the sessions' local time
SECONDS = 20.0  # each fight plays this long from its start
MARGIN = 30.0  # seconds of the take read past the window's end (`head`)
# name -> (take, the local clock time the fight starts at): round 1's table (the findings §9)
FIGHTS: dict[str, tuple[str, str]] = {
    'danger-arachnid-2031': ('20261021T172936Z-84', '2026-10-21T20:31:13'),
    'danger-durance-1338': ('20261021T103753Z-101', '2026-10-21T13:38:20'),
    'danger-durance-1414': ('20261021T111341Z-101', '2026-10-21T14:14:32'),
    'danger-durance-1426': ('20261021T112622Z-101', '2026-10-21T14:26:55'),
    'danger-durance-1956': ('20261021T165545Z-100', '2026-10-21T19:56:58'),
    'danger-plains-0508': ('20261021T020638Z-105', '2026-10-21T05:08:35'),
    'danger-plains-2217': ('20261020T191558Z-105', '2026-10-20T22:17:44'),
    'danger-area86-0407': ('20261021T010755Z-86', '2026-10-21T04:07:58'),
    'danger-area89-0428': ('20261021T012800Z-89', '2026-10-21T04:28:30'),
    'danger-marsh-0930': ('20261021T063019Z-77', '2026-10-21T09:30:41'),
    'danger-wsk-1848': ('20261021T154848Z-131', '2026-10-21T18:48:55'),
    'danger-area92-1815': ('20261021T151308Z-92', '2026-10-21T18:15:10'),
    'danger-area110-1912': ('20261021T161018Z-110', '2026-10-21T19:12:00'),
}
# The types' measured pace (units a second, frame to frame, moving, walk and run pooled: txt -> [steps, median]),
# from the round's scan of the takes of 2026-10-20 to 22 (scratch; read at the cut only, the fixture keeps the numbers)
SPEEDS_FILE = Path(
    '/tmp/claude-1000/-mnt-extra-1000-games-d2r/9e3b68b4-1c22-4d74-be40-0e18ede087a1/scratchpad/scan2/speeds.json'
)
SPEED_STEPS = 300  # a type measured over fewer steps keeps sim/monsters.py's pace
AMPLIFIED, DECREPIFIED, CONVICTED, LOWERED, ORDERS_STATE = 9, 60, 28, 61, 32  # states.txt
PHYSICAL_CURSES, ELEMENT_CURSES = (AMPLIFIED, DECREPIFIED), (CONVICTED, LOWERED)
MELEE_REACH = 3.5  # units: a hurt's attacker this close and striking was hand to hand


def bit(words: str | None, index: int) -> bool:
    """Whether state `index` is on in a frame's `s` (hex, little-endian bytes)."""
    if not words or len(words) < 2 * (index // 8 + 1):
        return False
    return bool(int(words[2 * (index // 8) : 2 * (index // 8) + 2], 16) >> (index % 8) & 1)


def shares(read: Sequence[int]) -> dict[str, float]:
    """A reading's shares let through, by kind (physical as read, the elements less Hell's penalty)."""
    return {kind: through(read[index] - (HELL_PENALTY if index else 0)) for index, kind in enumerate(KINDS)}


def window(take: Take, first: int, seconds: float) -> list[dict[str, Any]]:
    """The window's frames, each with the state words (`s`, written only when they change) and the resistance reading
    (`r`, likewise) it stands under, carried from the last frame that wrote them, from before the start too."""
    begin = take.frames[first]['t']
    words, read = last(take, 's', first), last(take, 'r', first)
    found = []
    for frame in take.frames[first:]:
        if frame['t'] - begin > seconds:
            break
        words, read = frame.get('s') or words, frame.get('r') or read
        found.append({**frame, 's': words, 'r': read, 'wrote_r': bool(frame.get('r'))})
    return found


def curses_of(take: Take, first: int, seconds: float) -> tuple[tuple[float, str, float], ...]:
    """The curses on the character as the window's frames show them (the module text)."""
    frames = window(take, first, seconds)
    begin = frames[0]['t']
    found: list[tuple[float, str, float]] = []
    was: tuple[bool, bool] = (False, False)
    for frame in frames:
        words, read = frame['s'], frame['r']
        if words is None or read is None:
            continue
        now = (any(bit(words, state) for state in PHYSICAL_CURSES), any(bit(words, state) for state in ELEMENT_CURSES))
        at = max(round(frame['t'] - begin, 2), 0.0)
        through_now = shares(read)
        if now[0] != was[0] or (now[0] and frame['wrote_r']):
            found.append((at, 'physical', through_now['physical']))
        if now[1] != was[1] or (now[1] and frame['wrote_r']):
            found += [(at, kind, through_now[kind]) for kind in KINDS[1:]]
        was = now
    kept: dict[str, float] = {}
    plain: list[tuple[float, str, float]] = []
    for at, kind, share in found:  # only the changes
        if kept.get(kind) != share:
            plain.append((at, kind, share))
            kept[kind] = share
    return tuple(plain)


def orders_of(take: Take, first: int, seconds: float) -> tuple[Orders, str]:
    """Battle Orders as the take shows it (the module text), and what was read."""
    frames = window(take, first, seconds)
    begin = frames[0]['t']
    if not bit(frames[0]['s'], ORDERS_STATE):
        return Orders(ends=0.0, factor=round(MOST_WITH / MOST_WITHOUT, 4), up=False), 'not up at the start'
    for before, after in pairwise(frames):
        if bit(before['s'], ORDERS_STATE) and not bit(after['s'], ORDERS_STATE):
            most, less = before['p'][8], after['p'][8]
            factor = round(most / less, 4) if most and less and most > less else round(MOST_WITH / MOST_WITHOUT, 4)
            return Orders(ends=round(after['t'] - begin, 2), factor=factor), f'out at {after["t"] - begin:.2f} s'
    return Orders(ends=seconds + 120.0, factor=round(MOST_WITH / MOST_WITHOUT, 4)), 'up through the window'


def melee_of(take: Take, first: int, seconds: float) -> tuple[int, ...]:
    """The shooters the window's hurts show striking within MELEE_REACH."""
    begin = take.frames[first]['t']
    found = set()
    for event in take.events:
        if event.get('event') != 'hurt' or not begin <= event['t'] <= begin + seconds:
            continue
        for row in event.get('by', ()):
            if len(row) > 4 and row[3] in (4, 5) and row[4] <= MELEE_REACH and shooter(row[1]):
                found.add(row[1])
    return tuple(sorted(found))


def speeds_of(types: set[int]) -> dict[int, float]:
    """Each type's pace: WINDOWED's, else SPEEDS_FILE's over SPEED_STEPS or more steps; else the model's."""
    measured = json.loads(SPEEDS_FILE.read_text()) if SPEEDS_FILE.exists() else {}
    found = {txt: WINDOWED[txt] for txt in sorted(types) if txt in WINDOWED}
    for txt in sorted(types - set(found)):
        if str(txt) in measured and measured[str(txt)][0] >= SPEED_STEPS:
            found[txt] = float(measured[str(txt)][1])
    return found


def terrorized(mob: Mob, area: int, level: int) -> Mob:
    """A hostile at the Terror Zone's `level`, its points there, its share of life kept."""
    if mob.owner is not None or mob.ally:
        return mob
    factor = points_of(mob.txt, area, level) / points_of(mob.txt, area)
    return replace(mob, level=level, full=round(mob.full * factor, 1), life=round(mob.life * factor, 1))


def started(take: str) -> datetime.datetime:
    return datetime.datetime.strptime(take.split('-')[0], '%Y%m%dT%H%M%SZ').replace(tzinfo=datetime.UTC)


def cut(
    name: str, fight: tuple[str, str] | None = None, seconds: float = SECONDS, about: str | None = None
) -> Situation:
    """The situation `name` (FIGHTS, or `fight`: its take and clock time) from its take (the module text), `seconds`
    long (stand_guard.py cuts its stand so)."""
    take_name, clock = FIGHTS[name] if fight is None else fight
    at = datetime.datetime.fromisoformat(clock).replace(tzinfo=ZONE)
    into = (at - started(take_name)).total_seconds() + seconds + MARGIN
    about = about or f'{clock}: one of the most dangerous fights of the takes beside the Fane (danger_fights.py)'
    manifest = json.loads((TAKES / take_name / 'manifest.json').read_text())
    player_level = int((manifest.get('character_stats') or {}).get('12') or 96)
    kept = cutting.MOB_RANGE
    cutting.MOB_RANGE = REACH
    try:
        with tempfile.TemporaryDirectory() as scratch:
            small = head(TAKES / take_name, into, Path(scratch))
            found = from_take(small, at.isoformat(), seconds, name=name, reach=REACH, about=about)
            loaded = Take.load(small)
            first = int((found.source or {})['frame'])
            found.scene.mobs += out_of_sight(loaded, found)
            percent = damage_percents(small, loaded.frames[first]['t'])
            curses = curses_of(loaded, first, seconds)
            orders, said = orders_of(loaded, first, seconds)
            melee = melee_of(loaded, first, seconds)
            read = last(loaded, 'r', first)
            staffed = any(frame.get('w') for frame in loaded.frames[: first + 1])
    finally:
        cutting.MOB_RANGE = kept
    area = found.scene.hero.area
    level = zone_level(area, player_level) or player_level
    found.scene.mobs = [pet(terrorized(mob, area, level)) for mob in found.scene.mobs]
    found.spawns = [replace(spawn, mobs=[terrorized(mob, area, level) for mob in spawn.mobs]) for spawn in found.spawns]
    hero = found.scene.hero
    if not staffed:
        # No staff in the frames: Teleport is Enigma's and the swap holds the Call to Arms (fane_death.py MAIN, CTA:
        # the character's two sets of 2026-10-21). cut.py's default swap is a Teleport staff: the macro swapped to it
        # for Battle Orders, found no Call to Arms there and swapped back, four times in 2 s (durance-1956, seed 9)
        hero = replace(hero, sets=(MAIN, CTA), hand=cutting.hand_of(read, (MAIN, CTA)) if read is not None else 0)
    if read is not None:
        held = hero.sets[hero.hand]
        read_set = WeaponSet(held.codes, shares(read), held.teleport_charges)
        hero = replace(hero, sets=(read_set, hero.sets[1]) if hero.hand == 0 else (hero.sets[0], read_set))
    found.scene.hero = replace(hero, slots=HUNT_SLOTS)
    found.curses = tuple(sorted(found.curses + curses))
    found.orders = orders
    found.own_teleport = not staffed
    found.rules = RULES
    found.melee = melee
    found.capped = True
    units = {mob.unit for mob in found.scene.mobs} | {mob.unit for spawn in found.spawns for mob in spawn.mobs}
    found.damage_percent = {unit: rows for unit, rows in percent.items() if unit in units}
    types = {mob.txt for mob in found.scene.mobs if not mob.ally and mob.owner is None}
    types |= {mob.txt for spawn in found.spawns for mob in spawn.mobs}
    found.speeds = speeds_of(types)
    found.aware = AWARE
    found.life_read = LIFE_READ
    found.assumed.update({
        'scene.mobs.level': f'monster level {level}: the Terror Zone at character level {player_level}',
        'scene.hero.sets': "the set in hand's resistances as the start's `r` reads them; without a staff the swap is "
        "the Call to Arms set of the Fane's take (fane_death.py CTA)",
        'scene.hero.slots': 'macros/fakes.py HUNT_SLOTS: the build, Teleport, Battle Orders',
        'curses': 'Amplify Damage / Decrepify and Conviction / Lower Resist at the frames that show them (states 9, '
        "60, 28, 61), each share as the `r` reading lets through, on both sets alike (`curses_of`)",
        'orders': f'Battle Orders (state 32): {said}; its cast not known to the macro',
        'own_teleport': 'no staff in the frames (`w`): Teleport is the character\'s own' if not staffed
        else "the staff's charges as `w` shows them",
        'melee': f'shooters the hurts show striking within {MELEE_REACH}: {list(melee)}',
        'damage_percent': "each hostile's stat 25 as the take read it, on its physical points and shown to the macro",
        'hit': "the fit's chance to take life per swing (the population, fane-death-sim-findings.md §8)",
        'speeds': f'the types\' walk and run as the takes measure them over 0.5 s windows ({len(found.speeds)} types)',
        'life_read': f'the life the macro and the healer read refreshed every {LIFE_READ} s and at a stagger',
        'aware': f'{AWARE:.0f} units (fane_death.py AWARE)',
        'pets': 'the Defiler and the bound Pit Lord at PET_POINTS each (game.py)',
    })  # fmt: skip
    return found


@functools.cache
def stored(name: str) -> Situation:
    return load(FIXTURES / f'{name}.json')


# -- a play and its measures --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Measures:
    """What one play came to."""

    seed: int
    dead_at: float | None
    low_share: float
    rejuvenations: int
    healing: int
    hops: int
    off_footing: int
    retreats: int
    kills: int
    leaders: int  # uniques, champions and Herald minions' leaders killed
    first_kill: float | None

    @property
    def dead(self) -> bool:
        return self.dead_at is not None


def measures(outcome: Outcome) -> Measures:
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    rejuvenations = sum(1 for _, item, _ in outcome.potions if item == FULL_REJUVENATION)
    lows = getattr(stage, 'low_shares', [])
    ranks = {mob.unit: mob.flags for mob in stage.mobs.mobs.values()}
    leaders = sum(1 for unit in stage.fell if ranks.get(unit, 0) & (4 | 8))
    return Measures(
        seed=outcome.seed,
        dead_at=outcome.dead_at,
        low_share=round(min(lows, default=1.0), 3),
        rejuvenations=rejuvenations,
        healing=len(outcome.potions) - rejuvenations,
        hops=len(stage.hops),
        off_footing=sum(1 for _, _, spot in stage.hops if stage.barred is not None and stage.barred(spot)),
        retreats=outcome.said_count('retreat'),
        kills=len(outcome.kills),
        leaders=leaders,
        first_kill=min(stage.fell.values(), default=None),
    )


def row_text(label: str, plays: Sequence[Measures]) -> str:
    died = [play.dead_at for play in plays if play.dead_at is not None]
    lows = [play.low_share for play in plays]

    def mean(values: Sequence[float]) -> float:
        return statistics.fmean(values) if values else 0.0

    return (
        f'| {label} | {len(died)}/{len(plays)} | {"-" if not died else f"{min(died):.1f}"} | '
        f'{min(lows):.0%} / {statistics.median(lows):.0%} | {sum(low < 0.2 for low in lows)} | '
        f'{mean([p.rejuvenations for p in plays]):.1f} | {mean([p.healing for p in plays]):.1f} | '
        f'{mean([p.hops for p in plays]):.1f} | {mean([p.kills for p in plays]):.1f} | '
        f'{mean([p.leaders for p in plays]):.1f} | {sum(p.off_footing for p in plays)} |'
    )


HEAD_ROW = (
    '| fight, fixes | deaths | first death, s | lowest life (least / median) | under 20% | rejuvenations | healing '
    '| Teleports | kills | leaders killed | hops off footing |\n'
    '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |'
)


def played(name: str, values: Mapping[str, bool], seeds: Sequence[int], lap: float | None = 0.02) -> list[Measures]:
    situation = stored(name)
    return [measures(play(situation, values, seed, lap=lap)) for seed in seeds]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true', help='cut the fixtures again from the takes')
    parser.add_argument('--seeds', type=int, default=5)
    parser.add_argument('--name', action='append', choices=sorted(FIGHTS))
    args = parser.parse_args(argv)
    names = args.name or sorted(FIGHTS)
    if args.cut:
        for name in names:
            dump(cut(name), FIXTURES / f'{name}.json')
        stored.cache_clear()
        return 0
    seeds = range(1, args.seeds + 1)
    print(HEAD_ROW)
    for name in names:
        for label, values in (('off', ALL_OFF), ('on', ALL_ON)):
            print(row_text(f'{name}, {label}', played(name, values, seeds)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
