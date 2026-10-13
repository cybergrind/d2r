"""The Grand Vizier's two recorded moments as situations, and the experiments on the first
(rca/2026-10-13/kp4-findings.md §1 and §4; the tables of rca/2026-10-13/situations.md are printed from here).

`STALL` is the game of 09:06 on 2026-10-13 (take 20261013T060607Z-108, schema 3), 35.0 s in: both Vizier seals
open, the route at "fight Grand Vizier of Chaos", the Vizier and four minions 57 units off, 48 presses of the
teleport key in 25 s that moved nothing. It is kp4.py's BOSS_AWAY cut through record.py: what that file had
from the session log by hand (the presses, the weapon set, the staff's charges, the seals' unit ids, the
seals opened) is given as `by_hand` and stands in the fixture's `assumed`.

`SEAL` is the game of 12:33 the same day (take 20261013T093331Z-108, schema 4), 72.0 s in for 16 s: the
character opens Vizier seal 1 (object class 396; its mode changes at 73.65 s of the take), the Vizier's pack
of six is first seen 0.95 s later 14 units off (74.60) and the Vizier dies at 84.77. Everything is the take's
own; the pack appears in the arena that long after the arena's own opening of the seal (record.py). In that
take it is class 396 whose opening brings the pack; class 395 (opened at 91.93) brings nothing.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.vizier [--cut] [--seeds N]

`EXPERIMENTS` are the stall's scene with other presses, the pack elsewhere or made aware: each a
`(Situation, presses)` by name, played by `experiment(name, seed)`.
"""

import argparse
import functools
import math
import statistics
from collections.abc import Callable, Sequence

from tests.inventory_tracking.scenarios.arena.kp4 import BOSS_AWAY
from tests.inventory_tracking.scenarios.arena.situations.record import TAKES, from_take
from tests.inventory_tracking.scenarios.arena.situations.situation import (
    FIXTURES,
    Outcome,
    Situation,
    dump,
    held,
    load,
    once,
)
from tests.inventory_tracking.scenarios.arena.situations.stage import EVERYONE, GAME_AWARE


BOSS = 'Grand Vizier of Chaos'
BOSSES = {306: BOSS}  # the super unique Storm Caster of the Chaos Sanctuary (rca/2026-10-13/scripts/vizier.py)
STALL, SEAL = 'vizier-stall', 'vizier-seal'
MINION_FLAG = 0x10
# How far from the character the Vizier was first seen in the other recorded games (scripts/vizier.py,
# 2026-10-13: 15 games, 5 to 40 units; the stall's own 52 is the sixteenth).
DISTANCES = (5, 8, 9, 12, 14, 16, 19, 25, 27, 38, 40)


def cut_stall() -> Situation:
    incident = BOSS_AWAY.incident
    return from_take(
        TAKES / incident.take, incident.start, incident.seconds, name=STALL, about=incident.about,
        reach=BOSS_AWAY.reach, bosses=BOSSES,
        by_hand={
            'why': 'probe.log of session 20261013T060446Z-aa50e0b0, as kp4.py BOSS_AWAY has it',
            'hero': dict(incident.hero),
            'presses': incident.presses,
            'opened': BOSS_AWAY.opened,
            'units': dict(BOSS_AWAY.units),
            'attack': False,  # the first press's stage turns the mode on ("Grand Vizier of Chaos, attack mode")
        },
    )  # fmt: skip


def cut_seal() -> Situation:
    return from_take(
        TAKES / '20261013T093331Z-108', 72.0, 16.0, name=SEAL, bosses=BOSSES,
        about=(
            'Chaos Sanctuary, 2026-10-13 12:34:43: the character opens Vizier seal 1 with attack mode on; the '
            "Vizier's pack of six appears 0.95 s after the seal's change of mode, 14 units off, and the Vizier "
            'dies 10.2 s after it appeared.'
        ),
    )  # fmt: skip


def cut() -> None:
    """Write both fixtures again from their takes."""
    FIXTURES.mkdir(exist_ok=True)
    dump(cut_stall(), FIXTURES / f'{STALL}.json')
    dump(cut_seal(), FIXTURES / f'{SEAL}.json')


@functools.cache
def stored(name: str) -> Situation:
    return load(FIXTURES / f'{name}.json')


def pack_units(situation: Situation) -> list[int]:
    """The Vizier and his minions: the boss and the minions of its type within 15 units of it."""
    boss = next(unit for unit, name in situation.bosses if name == BOSS)
    lead = next(mob for mob in situation.scene.mobs if mob.unit == boss)
    near = [mob for mob in situation.scene.mobs if mob.txt == lead.txt and math.dist(mob.at, lead.at) <= 15]
    return [mob.unit for mob in near if mob.unit == boss or (mob.flags & MINION_FLAG and mob.life > 0)]


def pack_at(situation: Situation, distance: float) -> Situation:
    """The situation with the Vizier's pack moved as one, along the line from the character to where the
    Vizier stood, so that he stands `distance` from the character."""
    found = situation.variant(f'{situation.name}, the pack {distance:g} off')
    units = set(pack_units(found))
    boss = next(unit for unit, name in found.bosses if name == BOSS)
    here = found.scene.hero.at
    lead = next(mob for mob in found.scene.mobs if mob.unit == boss)
    away = math.dist(here, lead.at)
    shift = ((lead.at[0] - here[0]) * (distance / away - 1), (lead.at[1] - here[1]) * (distance / away - 1))
    for mob in found.scene.mobs:
        if mob.unit in units:
            mob.at = (round(mob.at[0] + shift[0], 1), round(mob.at[1] + shift[1], 1))
    return found


KP4_FAST, KP4_SLOW = 0.3, 1.0  # seconds between presses of a held key: under and over the runner's TRAVEL_QUIET (0.5)


def experiments() -> dict[str, tuple[Situation, object]]:
    """name -> (the situation, its presses; None: the recorded ones)."""
    stall = stored(STALL)
    fast, slow = [held('teleport', every=KP4_FAST)], [held('teleport', every=KP4_SLOW)]
    aware = stall.variant(aware=EVERYONE)
    return {
        'as recorded (48 presses)': (stall, None),
        f'(a) KP_4 held, every {KP4_FAST:g} s': (stall, fast),
        f'(a) attack mode on + KP_4 held, every {KP4_FAST:g} s': (stall.variant(attack=True), fast),
        f'(a) attack mode on + KP_4 every {KP4_SLOW:g} s': (stall.variant(attack=True), slow),
        '(b) the seek key once': (stall, [once('seek')]),
        f'(b) the seek key every {KP4_SLOW:g} s': (stall, [held('seek', every=KP4_SLOW)]),
        '(c) attack mode alone': (stall.variant(attack=True), []),
        f"(e) aware within {GAME_AWARE:g} (the game's radius), recorded presses": (
            stall.variant(aware=GAME_AWARE),
            None,
        ),
        '(e) aware at any distance, recorded presses': (aware, None),
        '(e) aware at any distance, attack mode alone': (aware.variant(attack=True), []),
        f'(e) aware at any distance, attack on + KP_4 held, every {KP4_FAST:g} s': (aware.variant(attack=True), fast),
        f'(e) aware at any distance, attack on + KP_4 every {KP4_SLOW:g} s': (aware.variant(attack=True), slow),
    }


def distanced(distance: float) -> dict[str, tuple[Situation, object]]:
    """(d): the pack `distance` from the character, by how the keys are pressed."""
    moved = pack_at(stored(STALL), distance).variant(attack=True)
    return {
        'attack mode alone': (moved, []),
        f'attack on + KP_4 every {KP4_FAST:g} s': (moved, [held('teleport', every=KP4_FAST)]),
        f'attack on + KP_4 every {KP4_SLOW:g} s': (moved, [held('teleport', every=KP4_SLOW)]),
    }


def distance_table(seeds: Sequence[int]) -> str:
    """(d) as a table: a row a distance, for each way of pressing when the Vizier died and the life lost."""
    ways = list(distanced(DISTANCES[0]))
    lines = [
        '| the Vizier, units off | ' + ' | '.join(f'{way}: dead at, s | life lost' for way in ways) + ' |',
        '| ---: |' + ' ---: | ---: |' * len(ways),
    ]
    for distance in (*DISTANCES, 57.4):
        cells = []
        for situation, presses in distanced(distance).values():
            plays = [situation.play(presses, seed=seed) for seed in seeds]  # type: ignore[arg-type]
            cells += [spread([play.boss_dead[BOSS] for play in plays]), spread([play.taken for play in plays], 0)]
        lines.append(f'| {distance:g} | ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def experiment(name: str, seed: int) -> Outcome:
    situation, presses = experiments()[name]
    return situation.play(presses, seed=seed)  # type: ignore[arg-type]


def spread(values: Sequence[float | None], digits: int = 1) -> str:
    found = [value for value in values if value is not None]
    if not found:
        return 'never'
    never = f' (never in {len(values) - len(found)})' if len(found) < len(values) else ''
    if min(found) == max(found):
        return f'{found[0]:.{digits}f}{never}'
    return f'{min(found):.{digits}f} / {statistics.median(found):.{digits}f} / {max(found):.{digits}f}{never}'


def table(seeds: Sequence[int], progress: Callable[[str], None] = lambda name: None) -> str:
    lines = [
        '| experiment | distance to the Vizier: first | least | last | Vizier dead at, s | life lost | moved '
        '| deaths | stage at the end |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |',
    ]
    for name, (situation, presses) in experiments().items():
        progress(name)
        plays = [situation.play(presses, seed=seed) for seed in seeds]  # type: ignore[arg-type]
        gaps = [play.gaps[BOSS] for play in plays]
        stages = sorted({str(play.stage) for play in plays})
        lines.append(
            f'| {name} | {spread([gap and gap[0] for gap in gaps])} | {spread([gap and gap[1] for gap in gaps])} | '
            f'{spread([gap and gap[2] for gap in gaps])} | {spread([play.boss_dead[BOSS] for play in plays])} | '
            f'{spread([play.taken for play in plays], 0)} | {spread([play.moved for play in plays], 0)} | '
            f'{sum(1 for play in plays if play.dead)}/{len(plays)} | {"; ".join(stages)} |'
        )
    return '\n'.join(lines)


def compare(name: str, seeds: Sequence[int]) -> str:
    """The recording beside the arena's plays of a stored situation."""
    situation = stored(name)
    truth = situation.recorded or {}
    plays = [situation.play(seed=seed) for seed in seeds]
    gap = (truth.get('gaps') or {}).get(BOSS)
    rows = [
        ('life lost', truth.get('taken'), spread([play.taken for play in plays], 0)),
        ('least life', truth.get('low'), spread([play.low for play in plays], 0)),
        ('moved', truth.get('moved'), spread([play.moved for play in plays], 0)),
        ('strikes', len(truth.get('strikes', ())), spread([float(len(play.strikes)) for play in plays], 0)),
        ('hostiles killed', len(truth.get('kills', ())), spread([float(len(play.kills)) for play in plays], 0)),
        (
            'the Vizier first seen, units off',
            gap and gap[0],
            spread([play.gaps[BOSS] and play.gaps[BOSS][0] for play in plays]),
        ),
        (
            'the Vizier dead at, s',
            (truth.get('boss_dead') or {}).get(BOSS),
            spread([play.boss_dead[BOSS] for play in plays]),
        ),
    ]
    lines = [f'| {name} | recorded | arena least / median / most ({len(plays)} seeds) |', '| --- | ---: | ---: |']
    lines += [f'| {what} | {"never" if real is None else real} | {arena} |' for what, real, arena in rows]
    return '\n'.join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true', help='cut the fixtures again from the takes')
    parser.add_argument('--seeds', type=int, default=10)
    args = parser.parse_args(argv)
    if args.cut:
        cut()
    seeds = range(1, args.seeds + 1)
    print(compare(STALL, seeds), '\n')
    print(compare(SEAL, seeds), '\n')
    print(table(seeds), '\n')
    print(distance_table(seeds))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
