"""Cut the moments of the recorded battles into arena scenes (framework-plan.md, Task 1.8).

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.build_scenes
        [--root inventory_tracking/runs/combat] [--out tests/inventory_tracking/scenarios/arena/fixtures]
        [--per-kind 20] [--per-take 1] [--since YYYYMMDD] [--burst-share 0.3 0.15] [--reach 60]
        [--probe inventory_tracking/runs/alt-d] [--fixed 40] [--keep]

Goes over the takes under `--root`, newest first, finds the moments of each (moments.py: death,
burst, potions, long; stuck.py where the session's probe.log is found) and cuts each into
`<out>/<take>-<frame>-<kind>.json` (cut.py), `--per-kind` of a kind at most and `--per-take` of a kind
from one take (so a set is not twenty moments of the newest evening); every death is cut, whatever the
limits. A moment `cut` refuses is counted by the reason; one frame of a take is cut once, for the first
kind in KINDS that asks for it; a scene without a live hostile is not kept.

`--burst-share` takes the shares of the most life that make a burst. The module's own (moments.py
BURST_SHARE, 0.3) gives the kind `burst`; another gives `burst<percent>` (0.15: `burst15`), lighter
bursts for the choice of scenes only.

`--fixed N` adds up to N scenes of the kind `fixed` (fixed.py: times chosen blind to the outcome, for
averages). The other kinds are cut as ever, files byte for byte the same with or without it. A fixed
moment on a frame another kind cut is skipped (one frame, one scene), counted below. `--per-take` is the
number of fixed scenes from one take; takes are gone over oldest first and the ones kept are strided over
all of them (fixed.py `strides`, `spread`).

`--keep` leaves the scene files already in `--out` alone and cuts ONLY the fixed ones (needs `--fixed`),
frames of the scenes there counted as cut: for adding to a set when takes recorded since would change
the others.

Deterministic: the same takes and logs give the same files. The scene files already in `--out` are
removed first (not with `--keep`).
"""

import argparse
import dataclasses
import re
import sys
from collections import Counter
from collections.abc import Iterator, Sequence
from pathlib import Path

from inventory_tracking.combat.hurts import Sightings, enchantments, sightings
from inventory_tracking.combat.takes import Take
from inventory_tracking.macros.world import LYING_DEAD
from tests.inventory_tracking.scenarios.arena import moments as rules
from tests.inventory_tracking.scenarios.arena.cut import DEFAULT_HERO, Refused, cut
from tests.inventory_tracking.scenarios.arena.fixed import fixed, spread, strides
from tests.inventory_tracking.scenarios.arena.moments import Moment, moments
from tests.inventory_tracking.scenarios.arena.scene import Scene, dump
from tests.inventory_tracking.scenarios.arena.stuck import OPENED, stuck
from tests.inventory_tracking.scenarios.stance.build_fixtures import GROUND_RANGE


REPO = Path(__file__).resolve().parents[4]
ROOT = REPO / 'inventory_tracking' / 'runs' / 'combat'
PROBE = REPO / 'inventory_tracking' / 'runs' / 'alt-d'
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
KINDS = ('death', 'burst', 'potions', 'stuck', 'long')  # the order in which a frame two kinds ask for is given
UNLIMITED = frozenset(('death',))
SCENE_FILE = re.compile(r'\d{8}T\d{6}Z-\d+-\d+-[a-z0-9]+\.json')  # <take>-<frame>-<kind>.json
BELT_COLUMNS = 4


def belt_keys(take: Take) -> frozenset[int]:
    """The key codes of the belt keys 1 to 4. The manifest names the codes of the skill keys only
    (combat/record.py NAMED_KEYS), `6` among them: the number row's codes are one after another, so
    `1` is five before it (the take 20261011T195037Z-25 has `6` at 15 and the three potions of its
    last seconds at 12, 12 and 13: "Drinking (3)" in its log)."""
    six = next((int(code) for code, name in take.manifest.get('keys', {}).items() if name == '6'), None)
    return frozenset() if six is None else frozenset(six - 5 + column for column in range(BELT_COLUMNS))


def bursts(take: Take, share: float) -> list[Moment]:
    """The bursts of a take at another share of the most life than moments.py BURST_SHARE."""
    return [moment for moment in moments(take, burst_share=share) if moment.kind == 'burst']


def burst_kind(share: float) -> str:
    return 'burst' if share == rules.BURST_SHARE else f'burst{round(share * 100)}'


class Sessions:
    """The service's sessions (runs/alt-d/<stamp>-<id>/): which one's probe.log holds a take's opening,
    its routine lines, and the enchantments its terror probe saw. Each file is read once."""

    def __init__(self, root: Path, since: str | None) -> None:
        self.of: dict[str, Path] = {}  # take name -> session directory
        self.lines: dict[Path, list[str]] = {}
        self.seen: dict[Path, Sightings] = {}
        logs = sorted(root.glob('*/probe.log')) if root.is_dir() else []
        # A session that began before `since` may hold a take after it: the day before is read too.
        logs = [log for log in logs if since is None or log.parent.name[:8] >= str(int(since) - 1)]
        for count, log in enumerate(logs, 1):
            if count % 25 == 0 or count == len(logs):
                print(f'\rprobe logs {count}/{len(logs)}', end='', file=sys.stderr)
            kept = []
            with log.open(encoding='utf-8', errors='replace') as handle:
                for line in handle:
                    if 'Macro: request' in line:
                        kept.append(line.rstrip('\n'))
                    elif 'Combat take' in line and (opened := OPENED.search(line)):
                        kept.append(line.rstrip('\n'))
                        self.of.setdefault(opened[1], log.parent)
            self.lines[log.parent] = kept
        if logs:
            print(file=sys.stderr)

    def probe(self, take: str) -> list[str] | None:
        session = self.of.get(take)
        return None if session is None else self.lines[session]

    def mods(self, take: Take) -> dict[int, tuple[int, ...]]:
        """The enchantments of a take's units by its session's terror probe (combat/hurts.py); nothing
        for a take that holds its own, or without the log."""
        session = self.of.get(take.directory.name)
        if session is None or any('mods' in unit for unit in take.units):
            return {}
        if session not in self.seen:
            log = session / 'terror-probe.jsonl'
            self.seen[session] = sightings([log]) if log.exists() else {}
        return enchantments(self.seen[session], take)


def hostiles(scene: Scene) -> int:
    return sum(
        1 for mob in scene.mobs if mob.owner is None and not mob.ally and mob.mode != LYING_DEAD and mob.life > 0
    )


def takes(root: Path, since: str | None, *, newest_first: bool = True) -> Iterator[Path]:
    """The take directories under `root`, newest first (or oldest)."""
    for manifest in sorted(root.glob('*/manifest.json'), reverse=newest_first):
        if since is None or manifest.parent.name[:8] >= since:
            yield manifest.parent


def table(rows: Sequence[Sequence[object]]) -> str:
    widths = [max(len(str(row[column])) for row in rows) for column in range(len(rows[0]))]
    return '\n'.join('  '.join(str(cell).ljust(width) for cell, width in zip(row, widths, strict=True)) for row in rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Cut the moments of the combat takes into arena scenes.')
    parser.add_argument('--root', type=Path, default=ROOT, help='the takes (default: runs/combat)')
    parser.add_argument('--out', type=Path, default=FIXTURES, help='where the scenes go (default: fixtures/)')
    parser.add_argument('--per-kind', type=int, default=20, help='scenes of one kind at most (deaths: all)')
    parser.add_argument('--per-take', type=int, default=1, help='scenes of one kind from one take at most')
    parser.add_argument('--since', help='only takes of this day (YYYYMMDD, UTC) and later')
    parser.add_argument(
        '--burst-share', type=float, nargs='+', default=[rules.BURST_SHARE],
        help='the shares of the most life that make a burst; another than the default gives burst<percent>',
    )  # fmt: skip
    parser.add_argument('--fixed', type=int, default=0, help='scenes of the kind fixed to add (default 0: none)')
    parser.add_argument('--keep', action='store_true', help='leave the scenes in --out alone; cut only the fixed ones')
    parser.add_argument('--reach', type=float, default=GROUND_RANGE, help='units of ground kept round the character')
    parser.add_argument('--probe', type=Path, default=PROBE, help='the service sessions (default: runs/alt-d)')
    args = parser.parse_args(argv)

    shares = {burst_kind(share): share for share in args.burst_share}
    kinds = [*KINDS, *sorted(kind for kind in shares if kind not in KINDS)]
    if args.fixed:
        kinds.append('fixed')  # last: a fixed moment gives way to every other kind's frame
    if args.keep and not args.fixed:
        parser.error('--keep adds the fixed scenes: give --fixed')
    sessions = Sessions(args.probe, args.since)
    found: Counter[str] = Counter()
    kept: Counter[str] = Counter()
    refused: Counter[tuple[str, str]] = Counter()
    passed: Counter[tuple[str, str]] = Counter()  # found and sound, not kept
    assumed: Counter[str] = Counter()
    state: Counter[str] = Counter()
    scenes: list[tuple[str, Scene, Moment]] = []
    directories = list(takes(args.root, args.since))
    already: dict[str, dict[int, str]] = {}  # --keep: the frames of the scenes in --out, by take
    if args.keep:
        for old in sorted(args.out.glob('*.json')):
            if SCENE_FILE.fullmatch(old.name):
                name, frame, kind = old.stem.rsplit('-', 2)
                already.setdefault(name, {})[int(frame)] = kind
    candidates: dict[str, tuple[Path, list[Moment]]] = {}  # the fixed moments of a take whose frame is free
    for count, directory in enumerate(directories, 1):
        print(f'\rtakes {count}/{len(directories)} {directory.name:<24}', end='', file=sys.stderr)
        try:
            take = Take.load(directory)
        except (OSError, ValueError, EOFError, KeyError) as exc:
            state[f'not read ({type(exc).__name__})'] += 1
            continue
        state['read'] += 1
        state['not finished'] += not take.manifest.get('finished_at')
        state['schema 1'] += take.schema < 2
        state['no level file'] += not ((directory / 'level.json').exists() or (directory / 'level.json.gz').exists())
        probe = sessions.probe(directory.name)
        state['probe log found'] += probe is not None
        asked = [] if args.keep else moments(take, belt_keys=belt_keys(take))
        if 'burst' not in shares:
            asked = [moment for moment in asked if moment.kind != 'burst']
        if probe is not None and not args.keep:
            asked += stuck(take, probe)
        for kind, share in shares.items():
            if kind != 'burst' and not args.keep:
                asked += [dataclasses.replace(moment, kind=kind) for moment in bursts(take, share)]
        mods = None
        cut_frames: dict[int, str] = dict(already.get(directory.name, {}))
        from_take: Counter[str] = Counter()
        for moment in sorted(asked, key=lambda m: (kinds.index(m.kind), m.at)):
            kind = moment.kind
            found[kind] += 1
            if moment.frame in cut_frames:
                passed[kind, f'the frame of a {cut_frames[moment.frame]} scene'] += 1
                continue
            if kind not in UNLIMITED and kept[kind] >= args.per_kind:
                passed[kind, 'over --per-kind'] += 1
                continue
            if kind not in UNLIMITED and from_take[kind] >= args.per_take:
                passed[kind, 'over --per-take'] += 1
                continue
            if mods is None:
                mods = sessions.mods(take)
            name = f'{directory.name}-{moment.frame}-{kind}'
            try:
                scene = cut(take, moment.frame, defaults=DEFAULT_HERO, name=name, mods=mods, reach=args.reach)
            except Refused as exc:
                refused[kind, exc.reason] += 1
                continue
            if not hostiles(scene):
                refused[kind, 'no live hostile'] += 1
                continue
            cut_frames[moment.frame] = kind
            from_take[kind] += 1
            kept[kind] += 1
            scenes.append((name, scene, moment))
        if args.fixed:
            asked_fixed = fixed(take)
            found['fixed'] += len(asked_fixed)
            for moment in asked_fixed:
                if moment.frame in cut_frames:
                    passed['fixed', f'the frame of a {cut_frames[moment.frame]} scene'] += 1
            free = [moment for moment in asked_fixed if moment.frame not in cut_frames]
            if take.schema < 2 or not ((directory / 'level.json').exists() or (directory / 'level.json.gz').exists()):
                passed['fixed', 'a take cut would refuse'] += len(free)  # no vitals, or no level file
                free = []
            if free:
                candidates[directory.name] = (directory, free)
    if args.fixed:
        # The takes oldest first, all of them, strided; within a take spread over its length (fixed.py).
        eligible = [candidates[name] for name in sorted(candidates)]
        wanted = -(-args.fixed // max(args.per_take, 1))
        for count, position in enumerate(strides(len(eligible), wanted), 1):
            directory, free = eligible[position]
            print(f'\rfixed {count}/{wanted} {directory.name:<24}', end='', file=sys.stderr)
            room = args.fixed - kept['fixed']
            chosen = [free[i] for i in spread(len(free), min(args.per_take, room))]
            passed['fixed', 'over --fixed or --per-take'] += len(free) - len(chosen)
            take = Take.load(directory)
            mods = sessions.mods(take)
            for moment in chosen:
                name = f'{directory.name}-{moment.frame}-fixed'
                try:
                    scene = cut(take, moment.frame, defaults=DEFAULT_HERO, name=name, mods=mods, reach=args.reach)
                except Refused as exc:
                    refused['fixed', exc.reason] += 1
                    continue
                if not hostiles(scene):
                    refused['fixed', 'no live hostile'] += 1
                    continue
                kept['fixed'] += 1
                scenes.append((name, scene, moment))
        passed['fixed', 'takes not strided'] += sum(len(free) for _, free in eligible) - sum(
            len(eligible[position][1]) for position in strides(len(eligible), wanted)
        )
    print(file=sys.stderr)

    args.out.mkdir(parents=True, exist_ok=True)
    for old in [] if args.keep else args.out.glob('*.json'):
        if SCENE_FILE.fullmatch(old.name):
            old.unlink()
    size = 0
    for name, scene, moment in scenes:
        dump(scene, args.out / f'{name}.json')
        size += (args.out / f'{name}.json').stat().st_size
        assumed.update(scene.assumed)
        hero = scene.hero
        life = f'life {hero.life:.0f}/{hero.max_life:.0f}'
        print(f'{name:<44} area {hero.area:>3}  {hostiles(scene):>3} hostiles  {life}  {moment.note}')

    print()
    print(', '.join(f'{what}: {count}' for what, count in state.items()))
    rows: list[Sequence[object]] = [('kind', 'found', 'cut', 'refused', 'sound but not kept')]
    for kind in kinds:
        why = ', '.join(f'{reason} {count}' for (k, reason), count in sorted(refused.items()) if k == kind) or '-'
        rest = ', '.join(f'{reason} {count}' for (k, reason), count in sorted(passed.items()) if k == kind) or '-'
        rows.append((kind, found[kind], kept[kind], why, rest))
    print(table(rows))
    print(f'{len(scenes)} scenes, {size / 1024:.0f} KB in {args.out}')
    print('assumed, in scenes: ' + ', '.join(f'{name} {count}' for name, count in sorted(assumed.items())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
