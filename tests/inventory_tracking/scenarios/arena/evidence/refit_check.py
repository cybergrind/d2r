"""The refit monster model against the CHECK half of the evidence, mechanism by mechanism:

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.refit_check [--seconds 4000]

The model (combat/sim/monsters.py with data/monsters_fit.json) was fitted on the train half; nothing
here is fitted. Each mechanism is played in the simplest situation the evidence measured it in and
the model's number is laid beside the check half's:

- **melee**: one plain monster of the type two units from a character that stands still, alone, for
  `--seconds`: its swings a second, the share of them cut short, the share of the whole ones that
  takes life, and the life a second as the main set takes it (cut.py MAIN). The check half's life a
  second is the evidence's middle figure (the drops put on one monster of the type alone and those
  all of whose suspects are its swings), with its lower and upper figure in the note. The pooled row
  is played by the type without a row of its own that has the most seconds in reach on the check half;
- **target choice**: 2,000 monsters of the type between the character and a companion, once with each
  the nearer: the share that goes for the character;
- **ranged**: one plain shooter of the type at the distance the check half's shots at the character
  came from at the median, the character standing still and one companion six units from it: shots
  a second, the share of shots that takes life, life a second, over ten times `--seconds` (one shot
  in a hundred takes life). The check half's share is counted as the fit counts the train half's
  (fit.py `shot_row`: in points, not in drops; the counts' bounds are in the note), its life a
  second is the middle of the points put on the shooter alone and with its share of the shared drops;
- **teleporting out of a shot**: the same with the character hopping eight units away and back every
  second (an assumption about how a hunt moves, nothing measured): the share of the missiles sent at
  it under which it still is when they arrive, beside the check half's share of missiles that ended
  on the character when it teleported meanwhile over the same when it stood;
- **the death nova**: a Cold Enchanted unique dying at 2 to 12 units from the character: the share of
  deaths that takes life and the points, at the levels of the tabled melee types in turn (the
  evidence's nova rows hold no level);
- **the size of a blow**: the quantiles of the single blows of the plays above, beside the check
  half's drops put on one plain monster alone;
- **drops over 300 points from one source**, per 10,000 s of recording: the model played for the time
  the check half's monsters stood in reach and in sight (by rank for melee) and for its deaths of
  Cold Enchanted elites, beside the check half's drops over 300 put on one monster or one nova. The
  drops over 300 that several monsters shared need the takes' crowds: calibrate.py counts those.
- **the recorded death**: whether the Herald of the death scene can deal the 1,051 points at all.

`before` is the model before the refit as evidence.json holds it (`model`, read off its parameters
by evidence/model.py: every swing and every shot lands, a shot a second, the nearest target, no
nova). A ratio is after / measured on the check half; the aim is 0.5 to 2.0, and `main` lists every
row outside it.
"""

import argparse
import json
import math
import random
import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from inventory_tracking.combat.sim.monsters import (
    CHARACTER_FIRST,
    COLD,
    NOVA,
    STRIKE,
    UNIQUE_FLAG,
    Blow,
    Pack,
    Traits,
    Walker,
    fitted,
)
from inventory_tracking.combat.timeline import GAME_RATE
from tests.inventory_tracking.scenarios.arena.cut import MAIN
from tests.inventory_tracking.scenarios.arena.evidence.fit import EVIDENCE, middle
from tests.inventory_tracking.scenarios.arena.evidence.model import FLAGS
from tests.inventory_tracking.scenarios.arena.mobs import is_ranged, shot_parts


Point = tuple[float, float]
HERE: Point = (0.0, 0.0)
MATE: Point = (0.0, 6.0)  # a companion beside the character, out of a missile's contact with it
BESIDE = 2.0  # units: where the melee monster stands
AIM = (0.5, 2.0)  # after / measured: the band a mechanism is to be in
BIG = 300  # points: the evidence's big drop
DEATH = 1051  # points: the drop of the recorded death (fixtures/20261011T195037Z-25-493-death.json)
SECONDS = 4000.0
SHOT_TIMES = 10  # a shooter is played this many times longer than a fighter: one shot in a hundred takes life
ELITE_NEAR = ('0-4', '4-8', '8-12')  # the deaths table's bands a nova reaches in


@dataclass(frozen=True)
class Row:
    mechanism: str
    what: str
    before: float | None
    after: float | None
    measured: float | None
    note: str = ''

    @property
    def ratio(self) -> float | None:
        if self.after is None or not self.measured:
            return None
        return self.after / self.measured

    @property
    def outside(self) -> bool:
        return self.ratio is not None and not AIM[0] <= self.ratio <= AIM[1]


def through(blow: Blow) -> float:
    """What the main set loses of a blow."""
    return sum(points * MAIN.resist.get(kind, 1.0) for kind, points in blow.parts.items())


def fighter(unit: int, txt: int, at: Point, level: int | None, flags: int = 0, mods: Sequence[int] = (), tier: int = 0):
    walker = Walker(unit, txt, at[0], at[1], level=level or None, flags=flags, mods=tuple(mods), tier=tier)
    walker.traits = replace(walker.traits, melee=True)  # as mobs.py plays whatever is no shooter
    return walker


@dataclass
class Played:
    seconds: float
    begun: int = 0  # swings or shots begun
    whole: int = 0  # swings not cut short
    blows: tuple[float, ...] = ()  # the points of each blow on the character, as the main set takes them

    @property
    def life(self) -> float:
        return sum(self.blows) / self.seconds


def play(
    walker: Walker,
    seconds: float,
    seed: int,
    *,
    shots: Mapping[int, Mapping[str, float]] | None = None,
    targets: Callable[[int], Sequence[Point]] = lambda _frame: (HERE,),
) -> Played:
    """One monster for `seconds` against the targets of each frame."""
    pack = Pack([walker], seed, shots)
    found, blows, until = Played(seconds), [], walker.until
    for frame in range(round(seconds * GAME_RATE)):
        for blow in pack.step(frame, list(targets(frame))):
            if blow.target == 0:
                blows.append(through(blow))
        if walker.doing == STRIKE and walker.until != until:
            found.begun += 1
            found.whole += walker.lands >= 0
        until = walker.until
    found.blows = tuple(blows)
    return found


def quantile(values: Sequence[float], share: float) -> float | None:
    found = sorted(values)
    return found[min(int(share * len(found)), len(found) - 1)] if found else None


def stand_in(evidence: Mapping[str, Any], part: str, count: str, ranged: bool) -> int:
    """The type without a row of its own in the fit that the check half saw most of: it plays the pooled row."""
    own = fitted()['shots' if ranged else 'melee']['types']
    idle = fitted()['melee']['idle']
    found = {
        int(txt): row[part]['check'][count]
        for txt, row in evidence['types'].items()
        if row[part]['check'] and txt not in own and int(txt) not in idle and is_ranged(int(txt)) == ranged
    }
    return max(found, key=lambda txt: found[txt])


def melee_rows(evidence: Mapping[str, Any], seconds: float) -> tuple[list[Row], dict[int, Played]]:
    rows, plays = [], {}
    pooled = stand_in(evidence, 'melee', 'seconds', False)
    for txt in (*map(int, fitted()['melee']['types']), pooled):
        row = evidence['types'][str(txt)]
        check = evidence['check']['melee_all'] if txt == pooled else row['melee']['check']
        name = f'{row["name"]} ({txt})' + (', playing the pooled row' if txt == pooled else '')
        found = plays[txt] = play(fighter(1, txt, (BESIDE, 0.0), row['level']), seconds, txt)
        old = row['model']['blow']
        hit = middle(check['hit_low'], check['hit_high'])
        rows += [
            Row('melee', f'{name}: swings a second', old['swings_per_second'], found.begun / seconds,
                check['swings_per_second'], f'check: {check["swings"]} swings in {check["seconds"]:.0f} s'),
            Row('melee', f'{name}: share of swings cut short', 0.0, 1 - found.whole / found.begun,
                check['cut_share'], f'check: of {check["runs"]} runs'),
            Row('melee', f'{name}: share of whole swings that takes life', 1.0, len(found.blows) / found.whole, hit,
                f'check: {check["hit_low"]} to {check["hit_high"]} of {check["whole_aimed"]}'),
            Row('melee', f'{name}: life a second in reach', old['points_per_second'], found.life,
                check['points_per_second_same'],
                f'check: {check["points_per_second_low"]} to {check["points_per_second_high"]}'),
        ]  # fmt: skip
    return rows, plays


def target_rows(evidence: Mapping[str, Any], monsters: int = 2000) -> list[Row]:
    rows = []
    cases = {'hero': ((6.0, 0.0), 'the character nearer'), 'friend': ((14.0, 0.0), 'a companion nearer')}
    pooled = evidence['check']['targets']['pooled']
    for txt in (None, *map(int, fitted()['targets']['types'])):
        check = pooled if txt is None else evidence['types'][str(txt)]['targets']['check']
        played = stand_in(evidence, 'melee', 'seconds', False) if txt is None else txt
        name = 'all types (pooled)' if txt is None else f'{evidence["types"][str(txt)]["name"]} ({txt})'
        first = Traits.of(played).ai in CHARACTER_FIRST
        for nearer, (at, said) in cases.items():
            if not check or check[nearer]['hero_share'] is None:
                continue
            pack = Pack([fighter(unit, played, at, None) for unit in range(1, monsters + 1)], 1)
            mine = sum(pack._target(walker, [HERE, (20.0, 0.0)]) == 0 for walker in pack.walkers.values())
            seen = check[nearer]['seconds']
            rows.append(
                Row('target', f'{name}, {said}: share that goes for the character',
                    1.0 if nearer == 'hero' or first else 0.0, mine / monsters, check[nearer]['hero_share'],
                    f'check: of {seen["hero"] + seen["friend"]:.0f} s')
            )  # fmt: skip
    return rows


def shooter(unit: int, txt: int, away: float, level: int | None) -> tuple[Walker, dict[int, dict[str, float]]]:
    walker = Walker(unit, txt, away, 0.0, level=level or None)
    walker.traits = replace(walker.traits, melee=False)
    return walker, {unit: shot_parts(walker)}


def shot_rows(evidence: Mapping[str, Any], seconds: float) -> tuple[list[Row], dict[int, Played]]:
    rows, plays = [], {}
    pooled = stand_in(evidence, 'ranged', 'shots_in_sight', True)
    for txt in (*map(int, fitted()['shots']['types']), pooled):
        row = evidence['types'][str(txt)]
        check = evidence['check']['ranged_all'] if txt == pooled else row['ranged']['check']
        if not check or not check['shots_in_sight']:
            continue  # the check half did not see the type shoot
        name = f'{row["name"]} ({txt})' + (', playing the pooled row' if txt == pooled else '')
        away = check['shot_from']['p50'] or evidence['check']['ranged_all']['shot_from']['p50']
        walker, parts = shooter(1, txt, away, row['level'])
        length = seconds * SHOT_TIMES
        found = plays[txt] = play(walker, length, txt, shots=parts, targets=lambda _frame: (HERE, MATE))
        in_sight = check['seconds_in_sight']
        life = (check['points_sole'] / in_sight, (check['points_sole'] + check['points_shared']) / in_sight)
        # Hits a shot as the fit counts them (fit.py `shot_row`): the points put on the shooter alone and
        # half of its share of the shared drops, in hits of the check half's mean size.
        hit = evidence['check']['ranged_all']['points_sole'] / evidence['check']['ranged_all']['hits']
        per_shot = (
            (check['points_sole'] + check['points_shared'] / 2) / hit / check['shots'] if check['shots'] else None
        )
        old = row['model']['shot']
        rows += [
            Row('ranged', f'{name}: shots a second in sight', old['shots_per_second'], found.begun / length,
                check['shots_per_second'], f'check: {check["shots_in_sight"]} shots in {in_sight:.0f} s'),
            Row('ranged', f'{name}: share of shots that takes life', 1.0, len(found.blows) / found.begun, per_shot,
                f'check: in hits of {hit:.0f} points; by the counts of drops {check["hit_per_shot_low"]} to '
                f'{check["hit_per_shot_high"]} of {check["shots"]}'),
            Row('ranged', f'{name}: life a second in sight', old['points_per_second'], found.life,
                (life[0] + life[1]) / 2, f'check: {life[0]:.2f} to {life[1]:.2f}; shot from {away} units'),
        ]  # fmt: skip
    return rows, plays


def hop_row(evidence: Mapping[str, Any], seconds: float) -> Row:
    """The pooled shooter against a character hopping away and back every second."""
    txt = stand_in(evidence, 'ranged', 'shots_in_sight', True)
    check = evidence['check']['ranged_all']
    walker, parts = shooter(1, txt, check['shot_from']['p50'], evidence['types'][str(txt)]['level'])
    pack = Pack([walker], 7, parts)
    sent = ended = 0
    known: set[tuple[int, int]] = set()
    for frame in range(round(seconds * GAME_RATE)):
        here = HERE if frame // int(GAME_RATE) % 2 == 0 else (0.0, -8.0)
        pack.step(frame, [here, MATE])
        for missile in pack.flying:
            key = (missile.lands, missile.target)
            if missile.target == 0 and key not in known:
                known.add(key)
                sent += 1
                # Where the character will be when it arrives: this play's own schedule.
                then = HERE if missile.lands // int(GAME_RATE) % 2 == 0 else (0.0, -8.0)
                ended += math.dist(then, missile.at) <= 2.5
    jumped, stood = check['motion']['jumped'], check['motion']['stood']
    return Row(
        'ranged',
        'a character hopping 8 units and back each second: the missiles sent at it that still find it, '
        'over the same for one standing still',
        1.0,
        ended / sent,
        jumped['at_hero_on_hero_share'] / stood['at_hero_on_hero_share'],
        f'check: {jumped["at_hero_on_hero_share"]} of {jumped["at_hero"]} shots through which it teleported ended on '
        f'it, {stood["at_hero_on_hero_share"]} of {stood["at_hero"]} with it standing; the model: flight time alone',
    )


def cold_deaths(evidence: Mapping[str, Any], half: str) -> list[Mapping[str, Any]]:
    return [
        row
        for row in evidence[half]['novas']['deaths'].values()
        if 'cold' in row['group'] and row['rank'] == 'elite' and row['away'] in ELITE_NEAR
    ]


def nova_play(levels: Sequence[int], deaths: int, seed: int) -> list[float]:
    """The points of the novas of `deaths` Cold Enchanted uniques dying 2 to 12 units from the character
    (0.0: it took nothing)."""
    rolls, taken = random.Random(seed), []
    for index in range(deaths):
        walker = Walker(
            1, 0, rolls.uniform(2.0, 12.0), 0.0, level=levels[index % len(levels)], flags=UNIQUE_FLAG, mods=(COLD,)
        )
        pack = Pack([walker], seed * 100_003 + index)
        pack.died(1, 0)
        blows = [blow for frame in range(1, 40) for blow in pack.step(frame, [HERE]) if blow.kind == NOVA]
        taken.append(sum(through(blow) for blow in blows))
    return taken


def nova_rows(evidence: Mapping[str, Any]) -> tuple[list[Row], list[float]]:
    levels = [evidence['types'][txt]['level'] for txt in fitted()['melee']['types']]
    taken = nova_play(levels, 4000, 3)
    hits = [points for points in taken if points]
    deaths = cold_deaths(evidence, 'check')
    seen = sum(row['n'] for row in deaths)
    drops = evidence['check']['novas']['drops'].get('194|cold', {}).get('drop')
    rows = [
        Row('nova', 'a Cold Enchanted elite dying within 12 units: share that takes life', 0.0,
            len(hits) / len(taken), sum(row['nova_n'] for row in deaths) / seen, f'check: of {seen} deaths'),
    ]  # fmt: skip
    if drops:
        rows += [
            Row('nova', 'points of a nova, median', 0.0, statistics.median(hits), drops['p50'],
                f'check: {drops["n"]} drops; levels played: {sorted(set(levels))}'),
            Row('nova', 'points of a nova, 90th percentile', 0.0, quantile(hits, 0.9), drops['p90']),
        ]  # fmt: skip
    return rows, taken


def size_rows(evidence: Mapping[str, Any], melee: Mapping[int, Played], shots: Mapping[int, Played]) -> list[Row]:
    rows = []
    cases = (
        ('a strike', melee, evidence['check']['big'].get('plain|0|sole melee', {}).get('drop'), 'blow'),
        ('a shot', shots, evidence['check']['ranged_all']['hit'], 'shot'),
    )
    for said, plays, check, part in cases:
        if not check or not check['n']:
            continue
        blows = [points for found in plays.values() for points in found.blows]
        old = [evidence['types'][str(txt)]['model'][part]['most'] for txt in plays]
        for name, share in (('median', 0.5), ('90th percentile', 0.9), ('largest', 1.0)):
            key = {0.5: 'p50', 0.9: 'p90', 1.0: 'max'}[share]
            rows.append(
                Row('size', f'points of {said} on the character, {name}',
                    statistics.median(old) if share < 1 else max(old), quantile(blows, share), check[key],
                    f'check: {check["n"]} drops of one plain monster alone; model: {len(blows)} blows'
                    + ('; before: the heaviest blow of the types played' if share == 1 else ''))
            )  # fmt: skip
    return rows


def big_rows(evidence: Mapping[str, Any], seconds: float) -> list[Row]:
    """Blows over BIG from one source, per 10,000 s of recording, for the check half's exposure."""
    check = evidence['check']
    recorded = check['seconds']
    types = fitted()['melee']['types']
    reach = {txt: evidence['types'][txt]['melee']['check']['seconds'] for txt in types}
    whole = sum(reach.values())
    by_rank = {}  # the check half's seconds in reach by rank are in EVIDENCE.md's table, not in evidence.json
    counts: dict[str, float] = {'melee': 0.0, 'ranged': 0.0, 'nova': 0.0}
    # Melee: the check half's monster-seconds in reach, split over the tabled types as their own seconds
    # are, all plain (evidence.json has no seconds by rank; a unique's blows are larger).
    del by_rank
    for txt, share in reach.items():
        row = evidence['types'][txt]
        found = play(fighter(1, int(txt), (BESIDE, 0.0), row['level']), seconds, 11)
        counts['melee'] += sum(p > BIG for p in found.blows) / seconds * check['melee_all']['seconds'] * share / whole
    # Ranged: each tabled shooter for the seconds the check half had it in sight.
    for txt in fitted()['shots']['types']:
        row = evidence['types'][txt]
        seen = row['ranged']['check']
        if not seen or not seen['seconds_in_sight']:
            continue
        walker, parts = shooter(1, int(txt), seen['shot_from']['p50'] or 15.0, row['level'])
        length = seconds * SHOT_TIMES
        found = play(walker, length, 13, shots=parts, targets=lambda _frame: (HERE, MATE))
        counts['ranged'] += sum(p > BIG for p in found.blows) / length * seen['seconds_in_sight']
    # Novas: the check half's deaths of Cold Enchanted elites within 12 units.
    levels = [evidence['types'][txt]['level'] for txt in types]
    taken = nova_play(levels, 4000, 5)
    counts['nova'] = sum(p > BIG for p in taken) / len(taken) * sum(row['n'] for row in cold_deaths(evidence, 'check'))
    sole = ('sole melee', 'sole ranged', 'nova/explosion')
    seen = {
        half: [d for d in evidence['big_drops'] if d['half'] == half and d['class'] in sole]
        for half in ('check', 'train')
    }
    per = 10_000 / recorded
    rows = [
        Row('big', f'drops over {BIG} from one source per 10,000 s', 0.0, sum(counts.values()) * per,
            len(seen['check']) * 10_000 / recorded,
            f'check: {len(seen["check"])} in {recorded:.0f} s (train: {len(seen["train"])} in '
            f'{evidence["train"]["seconds"]:.0f} s); model: melee {counts["melee"] * per:.2f}, ranged '
            f'{counts["ranged"] * per:.2f}, nova {counts["nova"] * per:.2f}; plain monsters only'),
    ]  # fmt: skip
    return rows


def death_row(evidence: Mapping[str, Any], swings: int = 20000) -> Row:
    """The Herald of the recorded death: the share of its blows that take DEATH points or more."""
    drop = next(d for d in evidence['big_drops'] if d['points'] == DEATH)
    herald = max(drop['suspects'], key=lambda suspect: suspect['away'])
    walker = fighter(1, herald['txt'], (BESIDE, 0.0), herald['level'], FLAGS['unique'], herald['mods'], herald['tier'])
    pack = Pack([walker], 17)
    walker.aim = 0
    blows = [through(pack._blow(walker, frame)) for frame in range(swings)]
    reach = max(band['to'] for band in fitted()['reach']['tail'])
    far = max((band['share'] for band in fitted()['reach']['tail'] if band['to'] >= herald['away']), default=0.0)
    return Row(
        'death', f'the tier {herald["tier"]} Herald of the death scene: share of its blows of {DEATH} points or more',
        0.0, sum(points >= DEATH for points in blows) / swings, None,
        f'recorded: 1 such drop, from {herald["away"]} units; the model: largest blow {max(blows):.0f} '
        f'(before: {drop["model_most"]:.0f}), reach up to {reach:g} units, {far} of its thinks at that distance '
        f'begin a swing (before: none beyond 3.2)',
    )  # fmt: skip


def check(evidence: Mapping[str, Any], seconds: float = SECONDS) -> list[Row]:
    melee, melee_plays = melee_rows(evidence, seconds)
    shots, shot_plays = shot_rows(evidence, seconds)
    novas, _taken = nova_rows(evidence)
    return [
        *melee,
        *target_rows(evidence),
        *shots,
        hop_row(evidence, seconds),
        *novas,
        *size_rows(evidence, melee_plays, shot_plays),
        *big_rows(evidence, seconds),
        death_row(evidence),
    ]


def number(value: float | None) -> str:
    if value is None:
        return '-'
    return f'{value:.0f}' if abs(value) >= 100 else f'{value:.2f}' if abs(value) >= 1 else f'{value:.3f}'


def table(rows: Sequence[Row]) -> list[str]:
    lines = [
        '| mechanism | what | before | after | measured (check) | after / measured | note |',
        '| --- | --- | ---: | ---: | ---: | ---: | --- |',
    ]
    for row in rows:
        ratio = '-' if row.ratio is None else f'{row.ratio:.2f}' + (' **outside**' if row.outside else '')
        lines.append(
            f'| {row.mechanism} | {row.what} | {number(row.before)} | {number(row.after)} | {number(row.measured)} '
            f'| {ratio} | {row.note} |'
        )
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='The refit monster model against the check half of the evidence.')
    parser.add_argument('--seconds', type=float, default=SECONDS, help='how long each monster is played')
    args = parser.parse_args(argv)
    rows = check(json.loads(EVIDENCE.read_text()), args.seconds)
    print('\n'.join(table(rows)))
    judged = [row for row in rows if row.ratio is not None]
    outside = [row for row in judged if row.outside]
    print(f'\n{len(judged) - len(outside)} of {len(judged)} rows within {AIM[0]:g} to {AIM[1]:g}; outside:')
    for row in outside:
        print(f'- {row.what}: {row.ratio:.2f} ({number(row.after)} against {number(row.measured)}; {row.note})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
