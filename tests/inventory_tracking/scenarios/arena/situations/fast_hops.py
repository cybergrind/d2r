"""Tier 5 Extra Fast packs that do not drain, where the keep range hopped out of every strike, as situations
(rca/2026-10-25/jump-cluster-findings.md; FAST_HOP_STRIKES, gated here and removed 2026-10-26). danger_fights.py `cut`
of

- `fast-apparitions-2323`: 23:23:50 on 2026-10-25 (take 20261025T202255Z-71, tomb 71): a tier 5 Herald pack of 15
  Apparitions (Extra Fast) came onto the Herald stand; hops 1-5 at 23:23:57-59 (surrounded, then "extra fast: N of the
  pack on the character within 18"), no strike from 56.1 to 60.5;
- `fast-goatmen-2303`: 23:03:02 on 2026-10-25 (take 20261025T200015Z-74, Arcane Sanctuary): a tier 5 pack of
  goatmen (Extra Fast), three extra-fast hops at 23:03:07-09 between retreats and safe approaches, the first strike at
  12.62;

played as the live run did (the TZ run's pursuit, one pickup press, its legs, the level a terror zone: full clear),
with the level's walls, the arena's doors opened by a click (game.py DOORS_OPEN) and the pets as the game plays them.
The Extra Fast types run at the pace this take measures for their Extra Fast members (`measured`: 0.5 s windows in modes
2 and 15, the median), not the pooled pace of 2026-10-20 to 22; the plain members of those types run so too.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.fast_hops --cut
    uv run --offline python -m tests.inventory_tracking.scenarios.arena.situations.fast_hops --seeds 20
"""

import argparse
import datetime
import functools
import gzip
import json
import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from inventory_tracking.combat.threats import manaburn
from tests.inventory_tracking.scenarios.arena import game
from tests.inventory_tracking.scenarios.arena.situations import danger_fights as fights
from tests.inventory_tracking.scenarios.arena.situations.canyon_death import Dips
from tests.inventory_tracking.scenarios.arena.situations.door_pack import pursued
from tests.inventory_tracking.scenarios.arena.situations.fane_death import ALL_ON, play as fane_play
from tests.inventory_tracking.scenarios.arena.situations.halls_death import Legs
from tests.inventory_tracking.scenarios.arena.situations.record import TAKES
from tests.inventory_tracking.scenarios.arena.situations.situation import FIXTURES, Outcome, Situation, dump, load
from tests.inventory_tracking.scenarios.arena.situations.stage import Stage


SECONDS = 30.0
CUTS: dict[str, tuple[str, str]] = {
    'fast-apparitions-2323': ('20261025T202255Z-71', '2026-10-25T23:23:50.0'),
    'fast-goatmen-2303': ('20261025T200015Z-74', '2026-10-25T23:03:02.0'),
}
MOVING = (2, 15)  # monster modes: walk, run
WINDOW = (0.45, 0.5)  # seconds between a window's ends
LEAST_WINDOWS = 20  # a type measured over fewer windows keeps the cut's pace


def measured(take: str, start: str, seconds: float, units: set[int]) -> dict[int, float]:
    """Units a second the hostiles `units` cover in the take's window, by type: the displacement over WINDOW-long
    stretches whose ends are in MOVING modes, the median per type."""
    directory = TAKES / take
    manifest = json.loads((directory / 'manifest.json').read_text())
    at = datetime.datetime.fromisoformat(start).replace(tzinfo=fights.ZONE).timestamp()
    begin = at - (manifest['clock']['wall'] - manifest['clock']['monotonic'])
    tracks: dict[int, list[tuple[float, int, float, float, int]]] = defaultdict(list)
    with gzip.open(directory / 'frames.jsonl.gz', 'rt', encoding='utf-8') as frames:
        for line in frames:
            frame = json.loads(line)
            t = frame.get('t', 0.0)
            if t < begin:
                continue
            if t > begin + seconds:
                break
            for row in frame.get('m', ()):
                if row[0] in units and not row[9]:
                    tracks[row[0]].append((t, row[2], row[3], row[4], row[1]))
    paces: dict[int, list[float]] = defaultdict(list)
    for track in tracks.values():
        j = 0
        for i, (t, mode, x, y, txt) in enumerate(track):
            j = max(j, i + 1)
            while j < len(track) and track[j][0] - t < WINDOW[0]:
                j += 1
            if j >= len(track) or track[j][0] - t > WINDOW[1]:
                continue
            later = track[j]
            if mode in MOVING and later[1] in MOVING:
                paces[txt].append(math.dist((x, y), later[2:4]) / (later[0] - t))
    return {txt: round(statistics.median(found), 2) for txt, found in paces.items() if len(found) >= LEAST_WINDOWS}


def cut(name: str) -> Situation:
    take, start = CUTS[name]
    found = fights.cut(
        name, fight=CUTS[name], seconds=SECONDS,
        about=f'{start}: a tier 5 Extra Fast pack that does not drain, hopped out of every strike (fast_hops.py)',
    )  # fmt: skip
    mobs = list(found.scene.mobs) + [mob for spawn in found.spawns for mob in spawn.mobs]
    # The Extra Fast members' pace for their type: the arena paces by type, so the plain ones of it run so too (the
    # harder fight)
    fast = {mob.unit for mob in mobs if manaburn.EXTRA_FAST in mob.mods}
    paces = measured(take, start, SECONDS, fast)
    found.speeds = {**(found.speeds or {}), **paces}
    found.assumed['speeds'] = (
        f'the Extra Fast types {sorted(paces)} at the pace this take measures ({paces}, `measured`); the others as '
        'danger_fights.py `speeds_of`'
    )
    return found


@functools.cache
def stored(name: str) -> Situation:
    return load(FIXTURES / f'{name}.json')


def play(seed: int, name: str, values: Mapping[str, bool] = ALL_ON) -> tuple[Outcome, float]:
    """One play of `name` with the live code: the outcome and the lowest share of life the blows of a tick leave."""
    dips, legs = Dips(), Legs()

    def extra(stage: Stage, routed: Any) -> None:
        routed.progress.wanted = lambda area: True  # the level is a terror zone (terror/tracker.py)
        legs(stage, routed)
        dips(stage, routed)

    names = ('DOORS_OPEN', 'ALONG_ALL', *game.PETS_AS_GAME)
    saved = {attr: getattr(game, attr) for attr in names}
    for attr in names:
        setattr(game, attr, True)
    try:
        outcome = fane_play(pursued(stored(name), SECONDS), values, seed, lap=0.02, extra=extra)
    finally:
        for attr, value in saved.items():
            setattr(game, attr, value)
    return outcome, round(max(dips.low, 0.0), 3)


def summary(seed: int, name: str, values: Mapping[str, bool] = ALL_ON) -> dict[str, Any]:
    """One play's measures: death, the lowest life, kills, jump casts (the arena's hops), time to the last kill."""
    outcome, low = play(seed, name, values)
    measures = fights.measures(outcome)
    stage: Stage = outcome.stage_  # type: ignore[attr-defined]
    return {
        'dead': measures.dead_at, 'low': low, 'kills': measures.kills, 'leaders': measures.leaders,
        'hops': measures.hops, 'rejuv': measures.rejuvenations, 'first_kill': measures.first_kill,
        'last_kill': max(stage.fell.values(), default=None),
    }  # fmt: skip


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    parser.add_argument('--cut', action='store_true', help='cut the situations from their takes into the fixtures')
    parser.add_argument('--seeds', type=int, default=0)
    args = parser.parse_args(argv)
    if args.cut:
        for name in CUTS:
            dump(cut(name), FIXTURES / f'{name}.json')
            print(name, stored(name).speeds)
        stored.cache_clear()
    for name in CUTS:
        for seed in range(1, args.seeds + 1):
            print(name, seed, json.dumps(summary(seed, name)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
