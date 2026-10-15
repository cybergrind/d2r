"""EVIDENCE.md, evidence.json and split.json: what all recorded battles show of the monsters, beside
what the arena's model does, for the refit to be fitted on and judged against.

    uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.report
        [--root inventory_tracking/runs/combat] [--since YYYYMMDD] [--limit N] [--jobs N] [--no-cache]

Every schema 2 take is read once (scan.py; cached per take outside the repo), split by its name into
a train and a check half (scan.py `half`), and measured three times: on the train half, on the check
half and on both (rates.py `measure`). The report's tables carry the train and the check number side
by side wherever the number is one the refit will set a parameter by; the model's present value
(model.py) and the ratio of the train measure to it stand beside them. The raw rows (one per drop)
go to the cache directory as `blows.jsonl`, not into the repo.

The written files hold no clock: equal takes and equal code give equal bytes.
"""

import argparse
import csv
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from functools import cache
from pathlib import Path
from typing import Any

from inventory_tracking.combat.hurts import BESIDE, HURT_LEAST, MISSILE_REACH, SUSPECT_REACH
from inventory_tracking.combat.mechanics.tables import tables
from inventory_tracking.combat.sim.monsters import AWARE, CHARACTER_FIRST, REACH
from tests.inventory_tracking.scenarios.arena.evidence import model, rates, scan
from tests.inventory_tracking.scenarios.arena.evidence.blows import (
    CLASSES,
    ENDED_REACH,
    FRIEND,
    HERO,
    MISSILE,
    NOVA,
    NOVA_FRAMES,
    NOVA_RADIUS,
    PLAIN,
    SOLE_MELEE,
    SOLE_RANGED,
    SWING,
    name_of,
)


HERE = Path(__file__).parent
RAW_MISSILES = scan.REPO / 'pricing' / 'raw' / 'game-excel' / 'missiles.txt'  # git-ignored; names only
BIG = 300  # points: every drop over this is listed
COLD_NOVA = 194  # missiles.txt `coldunique` (mechanics/tables.py MISSILES)
TOP = 20


@cache
def missile_names() -> dict[int, str]:
    """missiles.txt ids to names: the installed game's table when the host has it, else the four the
    bundled tables hold."""
    found = {int(txt): row.get('Missile', '') for txt, row in tables()['missiles'].items()}
    if RAW_MISSILES.exists():
        with RAW_MISSILES.open(encoding='latin-1') as handle:
            for row in csv.DictReader(handle, delimiter='\t'):
                if row.get('*ID', '').isdigit():
                    found[int(row['*ID'])] = row['Missile']
    return found


def missile(txt: Any) -> str:
    return f'{missile_names().get(int(txt), "?")} ({txt})' if str(txt).isdigit() else str(txt)


def show(value: Any, digits: int = 2) -> str:
    if value is None:
        return '-'
    if isinstance(value, float):
        return f'{value:,.{digits}f}'
    return f'{value:,}' if isinstance(value, int) else str(value)


def pair(low: Any, high: Any, digits: int = 2) -> str:
    return f'{show(low, digits)} to {show(high, digits)}'


def over(measured: float | None, modelled: float | None) -> str:
    """The ratio measured / model."""
    return '-' if measured is None or not modelled else f'{measured / modelled:.2f}'


def table(headers: Sequence[str], lines: Sequence[Sequence[Any]]) -> list[str]:
    out = ['| ' + ' | '.join(headers) + ' |', '|' + ' --- |' * len(headers)]
    out += ['| ' + ' | '.join(str(cell) for cell in line) + ' |' for line in lines]
    return [*out, '']


def quants(found: Mapping[str, Any], digits: int = 0) -> str:
    """n and p50 / p90 / max of a spread."""
    if not found or not found.get('n'):
        return 'n 0'
    return f'n {found["n"]}: {show(found["p50"], digits)} / {show(found["p90"], digits)} / {show(found["max"], digits)}'


def model_of(txt: int, level: int | None, rank: str = PLAIN) -> dict[str, Any]:
    flags = model.flags_of(rank)
    return {'blow': model.blow(txt, level, flags), 'shot': model.shot(txt, level, flags)}


def enough_melee(entry: Mapping[str, Any]) -> bool:
    return entry.get('seconds', 0) >= rates.ENOUGH_SECONDS or entry.get('blows', 0) >= rates.ENOUGH_BLOWS


def per_type(train: Mapping[str, Any], check: Mapping[str, Any], whole: Mapping[str, Any]) -> dict[str, Any]:
    """The machine-readable part: per type the melee and ranged measures of both halves with the
    model's numbers beside them."""
    found: dict[str, Any] = {}
    for txt in sorted({k for k in whole['melee'] if k != 'all'} | {k for k in whole['ranged'] if k != 'all'}, key=int):
        melee = {half: m['melee'].get(txt) for half, m in ((scan.TRAIN, train), (scan.CHECK, check))}
        shots = {half: m['ranged'].get(txt) for half, m in ((scan.TRAIN, train), (scan.CHECK, check))}
        level = (whole['melee'].get(txt) or {}).get('level') or (whole['ranged'].get(txt) or {}).get('level')
        found[txt] = {
            'name': name_of(int(txt)),
            'level': level,
            'model': model_of(int(txt), level),
            'melee': melee,
            'ranged': shots,
            'targets': {half: m['targets']['types'].get(txt) for half, m in ((scan.TRAIN, train), (scan.CHECK, check))},
            'reach': {half: m['reach']['types'].get(txt) for half, m in ((scan.TRAIN, train), (scan.CHECK, check))},
        }
    return found


def classes_part(train: Mapping[str, Any], check: Mapping[str, Any], whole: Mapping[str, Any]) -> list[str]:
    def cell(found: Mapping[str, Any]) -> str:
        return f'{found["n"]:,} ({show((found["n_share"] or 0) * 100, 1)}%)'

    def points(found: Mapping[str, Any]) -> str:
        return f'{found["points"]:,} ({show((found["points_share"] or 0) * 100, 1)}%)'

    lines = [
        [name, cell(train['classes'][name]), points(train['classes'][name]), cell(check['classes'][name]),
         points(check['classes'][name]), cell(whole['classes'][name]), points(whole['classes'][name]),
         show(whole['classes'][name]['p50']), show(whole['classes'][name]['max'])]
        for name in CLASSES
    ]  # fmt: skip
    lines.append(
        ['all', f'{train["classes"]["n"]:,}', f'{train["classes"]["points"]:,}', f'{check["classes"]["n"]:,}',
         f'{check["classes"]["points"]:,}', f'{whole["classes"]["n"]:,}', f'{whole["classes"]["points"]:,}', '', '']
    )  # fmt: skip
    out = table(
        ['class', 'train drops', 'train points', 'check drops', 'check points', 'all drops', 'all points',
         'median', 'largest'],
        lines,
    )  # fmt: skip
    out += ['What the classes are made of (all takes):', '']
    out += table(
        ['part', 'drops', 'points', 'median', 'largest'],
        [[name, f'{p["n"]:,}', f'{p["points"]:,}', show(p['p50']), show(p['max'])]
         for name, p in whole['classes']['parts'].items()],
    )  # fmt: skip
    out += ['The suspects of the `several` drops (all takes):', '']
    out += table(
        ['suspects', 'drops', 'points', 'median', 'largest'],
        [[name, f'{p["n"]:,}', f'{p["points"]:,}', show(p['p50']), show(p['max'])]
         for name, p in sorted(whole['classes']['several_of'].items(), key=lambda kv: -kv[1]['points'])],
    )  # fmt: skip
    out += ['The drops nobody is blamed for, by size (all takes):', '']
    out += table(
        ['points', 'drops', 'points in all', 'median'],
        [
            [name, f'{p["n"]:,}', f'{p["points"]:,}', show(p['p50'])]
            for name, p in whole['classes']['unknown_sizes'].items()
        ],
    )
    return out


def reach_part(train: Mapping[str, Any], check: Mapping[str, Any], whole: Mapping[str, Any]) -> list[str]:
    out = [
        f'The model: every melee monster strikes from {REACH} units and no further (sim/monsters.py REACH).',
        '',
        'Distance of the sole striker at `sole melee` drops, types the threat table does not call ranged '
        '(n: p50 / p90 / max):',
        '',
    ]
    lines = [['all melee types', quants(train['reach']['pooled']['blows'], 1),
              quants(check['reach']['pooled']['blows'], 1), quants(whole['reach']['pooled']['blows'], 1)]]  # fmt: skip
    for rank in sorted(whole['reach']['ranks']):
        lines.append(
            [f'rank {rank}', quants(train['reach']['ranks'].get(rank, {}), 1),
             quants(check['reach']['ranks'].get(rank, {}), 1), quants(whole['reach']['ranks'][rank], 1)]
        )  # fmt: skip
    for txt, found in sorted(whole['reach']['types'].items(), key=lambda kv: -kv[1]['blows']['n']):
        if found['blows']['n'] < 4:
            continue
        lines.append(
            [f'{found["name"]} ({txt})', quants((train['reach']['types'].get(txt) or {}).get('blows', {}), 1),
             quants((check['reach']['types'].get(txt) or {}).get('blows', {}), 1), quants(found['blows'], 1)]
        )  # fmt: skip
    out += table(['who', 'train', 'check', 'all takes'], lines)
    out += [
        'The reach curve: all melee types, by the distance a swing began at. `swings/s` is swings begun in the '
        'band per second a live hostile stood in it; the hit chance is of whole swings with the character as the '
        "path record's target (low: drops put on that monster alone; high: with the drops it shares; alone: any "
        f'drop, nothing else hostile within {rates.CROWD:.0f} units). Train, then check in brackets.',
        '',
    ]
    lines = []
    for one, other in zip(train['reach_curve'], check['reach_curve'], strict=True):
        lines.append(
            [f'{one["from"]:g} to {one["to"]:g}', f'{show(one["seconds"], 0)} ({show(other["seconds"], 0)})',
             f'{one["swings"]:,} ({other["swings"]:,})',
             f'{show(one["swings_per_second"], 3)} ({show(other["swings_per_second"], 3)})',
             f'{one["whole_aimed"]:,} ({other["whole_aimed"]:,})',
             f'{pair(one["hit_low"], one["hit_high"])} ({pair(other["hit_low"], other["hit_high"])})',
             f'{show(one["alone_hit"])} of {one["alone"]} ({show(other["alone_hit"])} of {other["alone"]})']
        )  # fmt: skip
    out += table(
        ['units', 'seconds', 'swings', 'swings/s', 'whole, at the character', 'hit chance low to high', 'alone'],
        lines,
    )  # fmt: skip
    return out


def melee_part(train: Mapping[str, Any], check: Mapping[str, Any], whole: Mapping[str, Any]) -> list[str]:
    idle = {str(txt) for txt in train['melee']['all']['left_out']}
    chosen = [k for k, v in train['melee'].items() if k != 'all' and k not in idle and enough_melee(v)]
    chosen.sort(key=lambda k: -train['melee'][k]['seconds'])
    out = [
        f'Time is counted within {rates.MODEL_REACH} units of the character: the model strikes from {REACH} (the '
        'distance bins are half a unit wide), and the reach curve above has the swings begun at their full rate '
        f'up to there. Types with {rates.ENOUGH_SECONDS:.0f} s there or {rates.ENOUGH_BLOWS} sole blows on the train '
        f'half ({len(chosen)} of {len(train["melee"]) - 1} melee types seen). `model` swings/s: GAME_RATE / '
        '(STRIKE_FRAMES + (100 - aip3) / aip3 x aip2) for a monster that stays in reach. `usual frames`: the '
        "commonest length of the type's attack runs by mode (model: STRIKE_FRAMES 16 for all). `cut`: the share of "
        'runs shorter than half of that. `at it`: the share of swings whose path record named the character. '
        '`took life`: of the whole swings at the character, the share with a drop (low: put on that monster alone; '
        'high: with the drops it shares with other suspects); `alone`: any drop, nothing else hostile within '
        f'{rates.CROWD:g} units; `stood`: the character moved under {rates.MOVED:g} units through the swing. The '
        'model lands every swing. **A swing that took no life was not necessarily a miss**: the character blocks, '
        'and its Psychic Ward takes the next damage (builds/warlock/buffs.py); the arena models neither, so the '
        'share that took life is what it has to match. Left out as no fighters '
        f'({rates.ENOUGH_SECONDS:.0f} s or more within reach '
        f'and under one swing in {rates.IDLE:g} s there): '
        + (', '.join(f'{name_of(int(txt))} ({txt})' for txt in sorted(idle)) or 'none')
        + '. Train, then check in brackets.',
        '',
    ]
    lines = []
    for key in ['all', *chosen]:
        one, other = train['melee'][key], check['melee'].get(key) or {}
        modelled = None if key == 'all' else model.blow(int(key), one.get('level'))
        rate = modelled['swings_per_second'] if modelled else None
        lines.append(
            [f'{one["name"]}' + ('' if key == 'all' else f' ({key})'),
             f'{show(one["seconds"], 0)} ({show(other.get("seconds"), 0)})',
             f'{one["swings"]:,} ({show(other.get("swings"))})',
             f'{show(one["swings_per_second"])} ({show(other.get("swings_per_second"))})',
             show(rate), over(one['swings_per_second'], rate),
             ' / '.join(f'{mode}: {n}' for mode, n in (one.get('usual_frames') or {}).items()) or '-',
             f'{show(one["cut_share"])} ({show(other.get("cut_share"))})',
             f'{show(one["aimed_share"])} ({show(other.get("aimed_share"))})',
             f'{one["whole_aimed"]:,} ({show(other.get("whole_aimed"))})',
             f'{pair(one["hit_low"], one["hit_high"])} ({pair(other.get("hit_low"), other.get("hit_high"))})',
             f'{show(one["alone_hit"])} of {one["alone"]} '
             f'({show(other.get("alone_hit"))} of {show(other.get("alone"))})',
             f'{pair(one["stood_hit_low"], one["stood_hit_high"])} of {one["stood"]} '
             f'({pair(other.get("stood_hit_low"), other.get("stood_hit_high"))} of {show(other.get("stood"))})']
        )  # fmt: skip
    out += table(
        ['type', 's within 3.5', 'swings', 'swings/s', 'model', 'ratio', 'usual frames by mode', 'cut', 'at it',
         'whole at it', 'took life, low to high', 'alone', 'stood'],
        lines,
    )  # fmt: skip
    out += [
        f"The tail: between {rates.MODEL_REACH} units and the reach of the train half's sole blows (the 90th "
        f"percentile of the type's own with {rates.ENOUGH_BLOWS} of them, else of all melee types'). Train, then "
        'check in brackets.',
        '',
    ]
    lines = []
    for key in chosen:
        one, other = train['melee'][key], check['melee'].get(key) or {}
        lines.append(
            [f'{one["name"]} ({key})', f'{show(one["reach"], 1)} ({one["reach_from"]})',
             f'{show(one["tail_seconds"], 0)} ({show(other.get("tail_seconds"), 0)})',
             f'{one["tail_swings"]} ({show(other.get("tail_swings"))})',
             f'{show(one["tail_swings_per_second"])} ({show(other.get("tail_swings_per_second"))})',
             f'{one["tail_whole_aimed"]} ({show(other.get("tail_whole_aimed"))})',
             f'{pair(one["tail_hit_low"], one["tail_hit_high"])} '
             f'({pair(other.get("tail_hit_low"), other.get("tail_hit_high"))})']
        )  # fmt: skip
    out += table(['type', 'reach', 's in the tail', 'swings', 'swings/s', 'whole at it', 'took life'], lines)
    out += [
        'What the blows took. `blow`: the drops put on one monster of the type alone (n: p50 / p90 / max). '
        '`model blow`: a plain monster of the type at the level seen, mean / most, as the main set takes it. '
        f'`life/s`: points lost per second a monster of the type stood within {rates.MODEL_REACH} units: by sole '
        'drops / with the drops all of whose suspects are swings of the type / with an even share of the mixed '
        "ones. `model life/s`: the model's swings/s times its mean blow, every swing landing on the character. "
        "The ratio is the middle figure of the train half over the model's.",
        '',
    ]
    lines = []
    for key in chosen:
        one, other = train['melee'][key], check['melee'].get(key) or {}
        modelled = model.blow(int(key), one.get('level'))
        middle = one['points_per_second_same']
        lines.append(
            [f'{one["name"]} ({key})', show(modelled['level']),
             quants(one['blow']), quants(other.get('blow') or {}),
             f'{show(modelled["mean"], 0)} / {show(modelled["most"], 0)}',
             f'{show(one["points_per_second_low"])} / {show(middle)} / {show(one["points_per_second_high"])}',
             f'{show(other.get("points_per_second_low"))} / {show(other.get("points_per_second_same"))} / '
             f'{show(other.get("points_per_second_high"))}',
             show(modelled['points_per_second'], 1), over(middle, modelled['points_per_second'])]
        )  # fmt: skip
    out += table(
        ['type', 'level', 'blow, train', 'blow, check', 'model blow', 'life/s train', 'life/s check',
         'model life/s', 'ratio (middle)'],
        lines,
    )  # fmt: skip
    out += ['By rank, pooled over the melee types (train; check in brackets):', '']

    def took(total: Mapping[str, float]) -> str:
        whole_swings = total['whole_aimed']
        low = rates.ratio(total['hits_sole'], whole_swings)
        return pair(low, rates.ratio(total['hits_sole'] + total['hits_shared'], whole_swings))

    lines = []
    for rank in sorted({v['rank'] for v in whole['melee_by_rank'].values()}):
        sums = []
        for half in (train, check):
            mine = [v for v in half['melee_by_rank'].values() if v['rank'] == rank and str(v['txt']) not in idle]
            total: Counter[str] = Counter()
            for entry in mine:
                for field in ('seconds', 'swings', 'whole_aimed', 'hits_sole', 'hits_shared', 'blows', 'points_sole',
                              'points_same_type'):  # fmt: skip
                    total[field] += entry[field]
            sums.append(total)
        one, other = sums
        lines.append(
            [rank, f'{show(float(one["seconds"]), 0)} ({show(float(other["seconds"]), 0)})',
             f'{show(rates.ratio(one["swings"], one["seconds"]))} '
             f'({show(rates.ratio(other["swings"], other["seconds"]))})',
             f'{one["whole_aimed"]:,} ({other["whole_aimed"]:,})',
             f'{took(one)} ({took(other)})',
             f'{one["blows"]} ({other["blows"]})',
             f'{show(rates.ratio(one["points_sole"] + one["points_same_type"], one["seconds"], 2))} '
             f'({show(rates.ratio(other["points_sole"] + other["points_same_type"], other["seconds"], 2))})']
        )  # fmt: skip
    out += table(
        ['rank', 's in reach', 'swings/s', 'whole at it', 'hit low to high', 'sole blows', 'life/s (middle)'], lines
    )
    return out


def ranged_part(train: Mapping[str, Any], check: Mapping[str, Any], whole: Mapping[str, Any]) -> list[str]:
    chosen = [k for k, v in train['ranged'].items() if k != 'all' and v['shots'] >= rates.ENOUGH_SHOTS]
    chosen.sort(key=lambda k: -train['ranged'][k]['shots'])
    constants = model.CONSTANTS
    out = [
        f'The model: a type the threat table calls ranged lands one shot every {constants["SHOT_FRAMES"]} frames '
        f'({constants["shots_per_second"]:g} a second) on the nearest of the character and its companions within '
        f'{constants["RANGED_REACH"]:g} units in a clear line; no missile flies and none misses.',
        '',
        f'Types with {rates.ENOUGH_SHOTS} shots on the train half. A shot is an attack run during which the monster '
        "let a hostile missile go (the owner id in the missile's record). `s in sight`: seconds within "
        f"{rates.RANGED_REACH:g} units with a clear line over the take's level file (closed doors not looked at; a "
        'take without a level file counts every second). `at it`: the share of shots whose missile came within '
        f'{MISSILE_REACH:g} units of where the character stood when it was let go (a companion standing beside the '
        'character draws the same missiles, so this is the most that were meant for it). `on it` / `on a '
        f'companion`: the share whose missile was last seen within {rates.END_ON} units of the character / of a '
        'companion, whichever was nearer: where the flight ended. `took life`: of the shots that ended on the '
        'character, the share with a drop (low: put on that shooter alone; high: any drop while its missile was '
        "near). `per shot`: the same of all shots: what the model's 1.0 is to be laid against. As with a swing, "
        'a missile that ended on the character and took no life may have been blocked or taken by Psychic Ward. '
        'Train, then check in brackets.',
        '',
    ]
    lines = []
    for key in ['all', *chosen]:
        one, other = train['ranged'][key], check['ranged'].get(key) or {}
        modelled = None if key == 'all' else model.shot(int(key), one.get('level'))
        lines.append(
            [one['name'] + ('' if key == 'all' else f' ({key})' + ('' if one['table_ranged'] else ' *')),
             f'{show(one["seconds_in_sight"], 0)} ({show(other.get("seconds_in_sight"), 0)})',
             f'{one["shots_in_sight"]:,} ({show(other.get("shots_in_sight"))})',
             f'{show(one["shots_per_second"])} ({show(other.get("shots_per_second"))})',
             over(one['shots_per_second'], constants['shots_per_second']),
             f'{show(one["at_hero_share"])} ({show(other.get("at_hero_share"))})',
             f'{show(one["on_hero_share"])} ({show(other.get("on_hero_share"))})',
             f'{show(one["on_friend_share"])} ({show(other.get("on_friend_share"))})',
             f'{pair(one["took_low"], one["took_high"])} of {one["on_hero"]} '
             f'({pair(other.get("took_low"), other.get("took_high"))} of {show(other.get("on_hero"))})',
             f'{pair(one["hit_per_shot_low"], one["hit_per_shot_high"], 3)} '
             f'({pair(other.get("hit_per_shot_low"), other.get("hit_per_shot_high"), 3)})',
             quants(one['shot_from'], 1),
             f'{quants(one["hit"])} ({quants(other.get("hit") or {})})',
             '-' if modelled is None else show(modelled['most'], 0),
             '-' if key == 'all' else
             f'{show(one["points_per_second_low"])} to {show(one["points_per_second_high"])}',
             '-' if modelled is None else show(modelled['points_per_second'], 0)]
        )  # fmt: skip
    out += table(
        ['type', 's in sight', 'shots', 'shots/s', 'ratio to model', 'at it', 'on it', 'on a companion',
         'took life (ended on it)', 'took life per shot', 'shot from, units (n: p50 / p90 / max)',
         'points of a sole hit (n: p50 / p90 / max)', 'model shot, most', 'life/s in sight', 'model life/s'],
        lines,
    )  # fmt: skip
    out += [
        '\\* not ranged by the threat table: the arena plays it as melee, or (no monstats attack) not at all.',
        '',
        "Standing against moving, the shots of the threat table's ranged types that flew at where the character "
        f"stood. `stood`: it was under {rates.MOVED:g} units from there at the end of the missile's flight; `moved`: "
        f'further, by walking; `jumped`: a single step over {rates.JUMP:g} units on the way (a teleport). `ended '
        'on it`: the share of those shots whose missile ended on the character; `took life`: of those that did. '
        'Train, then check in brackets.',
        '',
    ]
    lines = []
    for kind in rates.MOTIONS:
        one, other = train['ranged']['all']['motion'][kind], check['ranged']['all']['motion'][kind]
        lines.append(
            [kind, f'{one["at_hero"]:,} ({other["at_hero"]:,})',
             f'{show(one["at_hero_on_hero_share"])} ({show(other["at_hero_on_hero_share"])})',
             f'{one["on_hero"]:,} ({other["on_hero"]:,})',
             f'{one["hits_sole"]} to {one["hits_any"]} ({other["hits_sole"]} to {other["hits_any"]})',
             f'{pair(one["took_low"], one["took_high"])} ({pair(other["took_low"], other["took_high"])})']
        )  # fmt: skip
    out += table(
        ['the character', 'shots at where it stood', 'ended on it', 'shots that ended on it', 'drops low to high',
         'took life'],
        lines,
    )  # fmt: skip
    one = whole['ranged']['all']
    out += [
        f"Shots against attack runs (all takes, the threat table's ranged types): {one['attack_runs']:,} runs in an "
        f"attack mode, {one['runs_without_missile']:,} of them with no missile of the monster's appearing (a curse, a "
        f'swing by hand, or a missile the recorder missed), {one["blocked_shots"]:,} shots let go with no clear line '
        'by the level file. A missile appearing is the reliable sign of a shot; the mode alone overcounts by a '
        f"fifth. The path record is no guide to a shooter's target: it named the character for "
        f'{show(one["path_aim_hero_share"])} of the {one["path_aim_known"]:,} shots that had a record.',
        '',
    ]
    return out


def targets_part(train: Mapping[str, Any], check: Mapping[str, Any], whole: Mapping[str, Any]) -> list[str]:
    out = [
        'The model: a monster goes for the nearest of the character and its companions; a type whose monstats `AI` '
        f'is in CHARACTER_FIRST ({", ".join(sorted(CHARACTER_FIRST))}) for the character whenever it is within '
        f'{AWARE:g} units.',
        '',
        f"Seconds a live hostile within {AWARE:g} units of the character had each as its path record's target, by "
        'which of the character and its nearest companion was nearer to the monster (`hero share`: character / '
        '(character + companion)). Units: monsters counted once per cell and take.',
        '',
    ]
    lines = []
    for label, half in (('train', train), ('check', check)):
        for nearer in (HERO, FRIEND):
            cell = half['targets']['pooled'][nearer]
            lines.append(
                [label, 'the character' if nearer == HERO else 'a companion',
                 show(cell['seconds'][HERO], 0), show(cell['seconds'][FRIEND], 0), show(cell['seconds']['other'], 0),
                 show(cell['seconds']['nobody'], 0), show(cell['hero_share']),
                 f'{cell["units"][HERO]:,} / {cell["units"][FRIEND]:,}', '1.00' if nearer == HERO else '0.00']
            )  # fmt: skip
    out += table(
        ['half', 'nearer', 's on the character', 's on a companion', 's on another', 's on nobody', 'hero share',
         'units (character / companion)', 'model'],
        lines,
    )  # fmt: skip
    chosen = sorted(
        train['targets']['types'],
        key=lambda k: -sum(train['targets']['types'][k][FRIEND]['seconds'][who] for who in (HERO, FRIEND)),
    )[:TOP]
    lines = []
    for key in chosen:
        one, other = train['targets']['types'][key], check['targets']['types'].get(key)
        first = (tables()['monsters'].get(key) or {}).get('AI') in CHARACTER_FIRST

        def cell(found: Mapping[str, Any] | None, nearer: str) -> str:
            if not found:
                return '-'
            seconds = found[nearer]['seconds'][HERO] + found[nearer]['seconds'][FRIEND]
            return f'{show(found[nearer]["hero_share"])} of {show(seconds, 0)} s'

        lines.append(
            [f'{one["name"]} ({key})', cell(one, HERO), cell(other, HERO), cell(one, FRIEND), cell(other, FRIEND),
             '1.00' if first else '0.00']
        )  # fmt: skip
    out += ['Per type, the hero share (train: the types with the most seconds with a companion nearer):', '']
    out += table(
        ['type', 'character nearer, train', 'check', 'companion nearer, train', 'check', 'model, companion nearer'],
        lines,
    )  # fmt: skip
    return out


def best(row: Mapping[str, Any]) -> str:
    """A drop's suspects in words."""
    parts = []
    for suspect in row['by'][:4]:
        mods = '' if not suspect['mods'] else f' mods {suspect["mods"]}'
        tier = f' tier {suspect["tier"]}' if suspect['tier'] else ''
        what = suspect['via'] + (f' {missile(suspect["missile"])}' if suspect['missile'] else '')
        parts.append(
            f'{suspect["name"]} ({suspect["txt"]}) {suspect["rank"]}{tier}{mods}, {what} from {suspect["away"]}'
        )
    more = f' and {len(row["by"]) - 4} more' if len(row['by']) > 4 else ''
    return '; '.join(parts) + more if parts else 'nobody'


def big_part(rows: Sequence[Mapping[str, Any]], whole: Mapping[str, Any]) -> list[str]:
    out = [
        "Single drops put on one monster, by its rank and its Herald's tier (all takes; n by half). `over`: the "
        'drops larger than the heaviest blow the model lets that very monster deal the main set (model.py `most`: '
        'its type, level, rank, enchantments and tier), and the largest ratio.',
        '',
    ]
    lines = []
    for key, found in whole['big'].items():
        wanted = (found['rank'], found['tier'])
        mine = [r for r in rows if r['class'] == found['class'] and (r['by'][0]['rank'], r['by'][0]['tier']) == wanted]
        ratios = [r['lost'] / top for r in mine if (top := model.most(r['by'][0])) > 0]
        halves = Counter(scan.half(r['take']) for r in mine)
        lines.append(
            [key.replace('|', ', tier ', 1).replace('|', ', '), f'{halves[scan.TRAIN]} / {halves[scan.CHECK]}',
             show(found['drop']['p50']), show(found['drop']['p90']), show(found['drop']['p99']),
             show(found['drop']['max']), quants(found['away'], 1),
             f'{sum(ratio > 1 for ratio in ratios)} of {len(ratios)}', show(max(ratios, default=None))]
        )  # fmt: skip
    out += table(
        ['rank, tier, class', 'n train / check', 'p50', 'p90', 'p99', 'max', 'from (n: p50 / p90 / max)', 'over',
         'largest ratio'],
        lines,
    )  # fmt: skip
    heavy = sorted((r for r in rows if r['lost'] > BIG), key=lambda r: -r['lost'])
    out += [f'Every drop over {BIG} points ({len(heavy)} in all takes), with its best attribution:', '']
    lines = []
    for row in heavy:
        top = max((model.most(s) for s in row['by'] if s['via'] in (SWING, MISSILE)), default=0.0)
        lines.append(
            [row['lost'], f'{show((row["share"] or 0) * 100, 0)}%' + (' (death)' if row['dead'] else ''),
             f'{row["take"]} #{row["frame"]}', scan.half(row['take']), row['class'], best(row),
             show(top, 0) if top else '-', over(row['lost'], top)]
        )  # fmt: skip
    out += table(
        ['points', 'of the life', 'take, frame', 'half', 'class', 'suspects', "model's most (heaviest)", 'ratio'],
        lines,
    )  # fmt: skip
    return out


def nova_part(train: Mapping[str, Any], check: Mapping[str, Any], whole: Mapping[str, Any]) -> list[str]:
    out = [
        'The model: a death hurts only where the threat table says the corpse explodes (450 points within 4 units: '
        "scenarios/threat/harness.py BLAST, BLAST_RADIUS); an enchanted monster's death does nothing.",
        '',
        f'Deaths of hostiles within {rates.DEATH_REACH:g} units of the character, by what the dead one carried '
        '(monumod 18 cold, 9 fire, 17 lightning), its standing (elite: champion, unique or super unique) and how far '
        f'it was. `missile`: a hostile missile owned by the dead one appeared within {rates.BIRTH} frames of the '
        f'death. `drop after`: the share followed by a drop within {NOVA_FRAMES} frames; `before`: preceded by one '
        '(the control: a death that does nothing shows the same share on both sides). `put on it`: drops of class '
        '`nova/explosion` with this death as the suspect. All takes; n by half. Groups with under 10 deaths in '
        'all bands together are left out.',
        '',
    ]
    sizes: Counter[tuple[str, str]] = Counter()
    for found in whole['novas']['deaths'].values():
        sizes[found['group'], found['rank']] += found['n']
    lines = []
    for key, found in whole['novas']['deaths'].items():
        if sizes[found['group'], found['rank']] < 10:
            continue
        counts = [(half['novas']['deaths'].get(key) or {}).get('n', 0) for half in (train, check)]
        lines.append(
            [found['group'], found['rank'], found['away'], f'{found["n"]:,} ({counts[0]} / {counts[1]})',
             found['with_missile'],
             ', '.join(f'{missile(txt)} x{n}' for txt, n in found['missiles'].items()) or '-',
             show(found['after_share']), show(found['before_share']),
             f'{found["after_points"]:,} / {found["before_points"]:,}', found['nova_n'],
             f'{found["nova_points"]:,}', found['nova_top']]
        )  # fmt: skip
    out += table(
        ['carried', 'standing', 'units', 'deaths (train / check)', 'missile', 'which', 'drop after', 'before',
         'points after / before', 'put on it', 'points', 'largest'],
        lines,
    )  # fmt: skip
    out += ['The `nova/explosion` drops by the missile that was near and what its dead owner carried:', '']
    lines = []
    for key, found in sorted(whole['novas']['drops'].items(), key=lambda kv: -kv[1]['drop']['n']):
        what, group = key.split('|')
        counts = [((half['novas']['drops'].get(key) or {}).get('drop') or {}).get('n', 0) for half in (train, check)]
        lines.append(
            [missile(what), group, f'{found["drop"]["n"]} ({counts[0]} / {counts[1]})', show(found['drop']['p50']),
             show(found['drop']['p90']), show(found['drop']['max']), quants(found['away'], 1)]
        )  # fmt: skip
    out += table(
        ['missile', 'carried', 'drops (train / check)', 'p50', 'p90', 'max',
         'corpse to character (n: p50 / p90 / max)'],
        lines,
    )  # fmt: skip
    return out


def span(values: Sequence[float | None], digits: int = 2) -> str:
    """The least and the most of the values that are there."""
    found = [value for value in values if value is not None]
    return pair(min(found), max(found), digits) if found else '-'


def changes(
    train: Mapping[str, Any], check: Mapping[str, Any], whole: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> list[str]:
    """What the refit should change, heaviest first by the points of the train half each carries."""
    total = train['classes']['points'] or 1
    parts, mixes = train['classes']['parts'], train['classes']['several_of']
    cold = [r for r in rows if r['class'] == NOVA and r['by'][0]['missile'] == COLD_NOVA]
    cold_train = [r for r in cold if scan.half(r['take']) == scan.TRAIN]
    cold_check = [r for r in cold if scan.half(r['take']) == scan.CHECK]
    cold_points = sum(r['lost'] for r in cold_train)
    carriers = [d for d in whole['novas']['deaths'].values() if 'cold' in d['group']]
    elite = [d for d in carriers if d['rank'] == 'elite']
    lesser = [d for d in carriers if d['rank'] != 'elite']
    shooters, shooters_check = train['ranged']['all'], check['ranged']['all']
    stood, jumped = shooters['motion']['stood'], shooters['motion']['jumped']
    pack, pack_check = train['melee']['all'], check['melee']['all']
    idle = {str(txt) for txt in train['melee']['all']['left_out']}
    chosen = [k for k, v in train['melee'].items() if k != 'all' and k not in idle and enough_melee(v)]
    blows = {k: model.blow(int(k), train['melee'][k].get('level')) for k in chosen}
    rate_ratios = [
        train['melee'][k]['swings_per_second'] / blows[k]['swings_per_second']
        for k in chosen
        if blows[k]['swings_per_second'] and train['melee'][k]['swings_per_second'] is not None
    ]
    life_ratios = [
        train['melee'][k]['points_per_second_same'] / blows[k]['points_per_second']
        for k in chosen
        if blows[k]['points_per_second'] and train['melee'][k]['points_per_second_same'] is not None
    ]
    near, near_check = train['targets']['pooled'][FRIEND], check['targets']['pooled'][FRIEND]
    first, first_check = train['targets']['pooled'][HERO], check['targets']['pooled'][HERO]
    curve = {(band['from'], band['to']): band for band in train['reach_curve']}
    beyond = [band for band in train['reach_curve'] if band['from'] >= 4.0]
    far_swings = sum(band['whole_aimed'] for band in beyond)

    def far_took(bound: str) -> float | None:
        return rates.ratio(sum((band[bound] or 0) * band['whole_aimed'] for band in beyond), far_swings)

    heavy = [r for r in rows if r['lost'] > BIG]
    sole = [r for r in rows if r['class'] == SOLE_MELEE]
    ratios = [r['lost'] / top for r in sole if (top := model.most(r['by'][0])) > 0]
    shot = [r for r in rows if r['class'] == SOLE_RANGED]
    shot_ratios = [r['lost'] / top for r in shot if (top := model.most(r['by'][0])) > 0]
    none = train['classes']['unknown']
    ticks = next(v for k, v in parts.items() if 'damage over time' in k)
    cost = next(v for k, v in parts.items() if 'fixed cost' in k)
    melee_points = train['classes'][SOLE_MELEE]['points'] + sum(
        mixes.get(kind, {}).get('points', 0) for kind in ('swings of one type', 'swings of several types')
    )
    ranged_points = train['classes'][SOLE_RANGED]['points'] + mixes.get('missiles of several', {}).get('points', 0)
    per_second = shooters['shots_per_second'] or 0.0
    often = [
        1 / (per_second * share) if per_second and share else None
        for share in (shooters['hit_per_shot_high'], shooters['hit_per_shot_low'])
    ]
    items = [
        (
            melee_points,
            f'**Melee: a swing is not a hit** ({melee_points:,} points on the train half: the sole melee drops and '
            'the drops whose suspects are all swings; '
            f'{mixes.get("swings and missiles", {}).get("points", 0):,} more are swings with missiles). Train, the '
            f'melee types that fight: {pack["swings"]:,} swings begun within {rates.MODEL_REACH} units in '
            f'{pack["seconds"]:,.0f} monster-seconds there: {show(pack["swings_per_second"])} a second (check '
            f'{show(pack_check["swings_per_second"])}). Model: 1.1 to 1.6 by type; the measured rate is '
            f"{span(rate_ratios)} of the model's for the {len(rate_ratios)} types with enough time, so **the swing "
            f'rate is not what is wrong**. What is: {show(pack["cut_share"])} of the attack runs are cut short '
            f'before the middle of the swing (check {show(pack_check["cut_share"])}; the model finishes every one), '
            f'and of the {pack["whole_aimed"]:,} whole swings with the character as the target '
            f'{pair(pack["hit_low"], pack["hit_high"])} took life (check '
            f'{pair(pack_check["hit_low"], pack_check["hit_high"])} of {pack_check["whole_aimed"]:,}); with nothing '
            f'else hostile near, {show(pack["alone_hit"])} of {pack["alone"]} (check {show(pack_check["alone_hit"])} '
            f'of {pack_check["alone"]}); with the character standing still, '
            f'{pair(pack["stood_hit_low"], pack["stood_hit_high"])} of {pack["stood"]} (check '
            f'{pair(pack_check["stood_hit_low"], pack_check["stood_hit_high"])} of {pack_check["stood"]}). Model: '
            '1.00. In life per second a monster stands in reach the takes show '
            f"{span(life_ratios)} of the model's, by type. Expected effect: a chance of about 0.2 that a whole "
            'swing takes life and runs cut short at the measured share bring a monster in contact to about a '
            'seventh of what it deals now (0.2 x 0.7); whom it goes for and the size of a blow (the lines below) '
            'make up the rest of the gap. Confidence: high on the direction and the order of size (both halves, '
            f'every type); low per type ({span([train["melee"][k]["whole_aimed"] for k in chosen], 0)} whole swings '
            'each on the train half). What the takes cannot '
            'split: a miss by the to-hit roll, a block, Psychic Ward taking the blow, and the character having left '
            'the reach (the stood-still figure bounds the last).',
        ),
        (
            cold_points,
            f"**A Cold Enchanted monster's death nova (`coldunique`, {COLD_NOVA}): not in the model** "
            f'({cold_points:,} points on the train half, {cold_points / total:.0%} of all its life lost). Train: '
            f"{len(cold_train)} drops with the dead one's nova near and nobody striking, median "
            f'{show(rates.quantile([r["lost"] for r in cold_train], 0.5))}, largest '
            f'{max((r["lost"] for r in cold_train), default=0)}, from a corpse '
            f'{show(rates.quantile([r["by"][0]["away"] for r in cold_train], 0.5), 1)} units off at the median and '
            f'{show(max((r["by"][0]["away"] for r in cold_train), default=None), 1)} at the most. Check: '
            f'{len(cold_check)} drops, median {show(rates.quantile([r["lost"] for r in cold_check], 0.5))}, largest '
            f'{max((r["lost"] for r in cold_check), default=0)}, corpse '
            f'{show(rates.quantile([r["by"][0]["away"] for r in cold_check], 0.5), 1)} units off at the median. '
            f'Model: 0. Who lets it go (all takes, deaths within {rates.DEATH_REACH:g} units): '
            f'{sum(d["with_missile"] for d in elite)} of {sum(d["n"] for d in elite)} deaths of an elite carrying Cold '
            f'Enchanted showed the missiles and {sum(d["nova_n"] for d in elite)} were followed by a drop put on '
            f'them; of {sum(d["n"] for d in lesser):,} deaths of plain monsters and minions carrying it, '
            f'{sum(d["with_missile"] for d in lesser)} and {sum(d["nova_n"] for d in lesser)}. Expected effect: the '
            'single largest named source of big drops (see the list of drops over 300). Confidence: high that it '
            'exists, on who lets it go and on its size (the owner id ties the missile to the corpse; the drops '
            'cluster near 180 and near twice that); the chance that a nova reaching the character takes life is the '
            "deaths table's `put on it` over `missile`. A Fire Enchanted death's explosion (`fireexplosion`, 82) is "
            'seen and takes a median of under 10 points: negligible with fire resistance at the cap.',
        ),
        (
            ranged_points,
            f'**Ranged: the shot rate, whom the shot is at, and what ends on the character** ({ranged_points:,} '
            'points on the train half: sole ranged drops and drops between several missiles). Train, the threat '
            f"table's ranged types: {shooters['shots_in_sight']:,} shots in {shooters['seconds_in_sight']:,.0f} s in "
            f'sight within {rates.RANGED_REACH:g} units: {show(shooters["shots_per_second"])} a second (check '
            f'{show(shooters_check["shots_per_second"])}; model {model.CONSTANTS["shots_per_second"]:g}). '
            f'{show(shooters["at_hero_share"])} of the missiles flew at where the character stood (check '
            f'{show(shooters_check["at_hero_share"])}), {show(shooters["on_hero_share"])} ended on it (check '
            f'{show(shooters_check["on_hero_share"])}) and {show(shooters["on_friend_share"])} on a companion (check '
            f'{show(shooters_check["on_friend_share"])}). Of the {shooters["on_hero"]:,} that ended on it '
            f'{pair(shooters["took_low"], shooters["took_high"])} took life (check '
            f'{pair(shooters_check["took_low"], shooters_check["took_high"])} of {shooters_check["on_hero"]:,}); per '
            f'shot {pair(shooters["hit_per_shot_low"], shooters["hit_per_shot_high"], 3)} (check '
            f'{pair(shooters_check["hit_per_shot_low"], shooters_check["hit_per_shot_high"], 3)}; model 1.0). Per '
            'second in sight, an arena shooter whose nearest target is the character takes life '
            f'{show(often[0], 0)} to {show(often[1], 0)} times as often as a shooter of the takes. Moving: of the '
            'missiles let go at where the character stood, '
            f'{show(stood["at_hero_on_hero_share"])} ended on it when it stood ({stood["at_hero"]:,} shots) and '
            f'{show(jumped["at_hero_on_hero_share"])} when it teleported meanwhile ({jumped["at_hero"]:,}). A hit, '
            'when '
            f"it comes, is larger than the model's shot: {sum(ratio > 1 for ratio in shot_ratios)} of "
            f"{len(shot_ratios)} sole ranged drops (all takes) exceed the model's most for that monster, the largest "
            f'{show(max(shot_ratios, default=None))} times. Expected effect: this is the largest single correction '
            'to the arena (CALIBRATION.md has 392 of its 688 blows as shots). Confidence: high on the rate and on '
            'where missiles end (thousands of shots, halves agree); medium on the share that takes life (tens of '
            'drops); low on the points of a hit per type (the table: under 10 sole hits each).',
        ),
        (
            melee_points - 1,
            f'**Whom a monster goes for** (it scales the melee line). Train: with a companion nearer than the '
            f'character, the path record named the character {show(near["hero_share"])} of the time '
            f'({near["seconds"][HERO]:,.0f} s against {near["seconds"][FRIEND]:,.0f} s on a companion; check '
            f'{show(near_check["hero_share"])}); with the character nearer, {show(first["hero_share"])} (check '
            f'{show(first_check["hero_share"])}). Model: 0 and 1 (the nearest of all), 1 and 1 for the Goatman AI. '
            'By kind the two go opposite ways (the per-type table): melee types name the character about half the '
            'time when a companion is nearer and nine times in ten when it is not; archers name a companion almost '
            'always, whoever is nearer, which the missiles confirm (the ranged line). Expected effect: more melee '
            'on the character than the nearest-of-all rule gives where companions stand in front (the scenes '
            'CALIBRATION.md found under half), fewer arrows. Confidence: high (thousands of monster-seconds, the '
            'halves agree to 0.02).',
        ),
        (
            sum(r['lost'] for r in heavy if scan.half(r['take']) == scan.TRAIN) - cold_points,
            f'**The big single drops.** {len(heavy)} drops over {BIG} points in all takes '
            f'({sum(scan.half(r["take"]) == scan.TRAIN for r in heavy)} train, '
            f'{sum(scan.half(r["take"]) == scan.CHECK for r in heavy)} check), {sum(r["lost"] for r in heavy):,} '
            'points; by class: '
            + ', '.join(f'{n} {name}' for name, n in Counter(r['class'] for r in heavy).most_common())
            + f'. Beside the cold nova: (a) several blows landing between two frames (the `several` rows of the '
            f"list), which right rates give by themselves only if single blows are as large as the takes'; (b) "
            f"single blows over the model's most: {sum(ratio > 1 for ratio in ratios)} of {len(ratios)} sole melee "
            f'drops (all takes) exceed the heaviest blow the model lets that very monster deal, the largest '
            f"{show(max(ratios, default=None))} times (Ice Spawn 458: 320 and 322 points against 93). A blow's "
            'top is too low for some types, which no rate mends. Confidence: medium; the list in section 8 is the '
            f'evidence, and the refit should be shown to produce drops of this size at about this rate '
            f'({len(heavy)} in {whole["seconds"]:,.0f} s).',
        ),
        (
            parts['sole melee, further off and aimed at it']['points'],
            f'**Reach** ({parts["sole melee, further off and aimed at it"]["points"]:,} points on the train half '
            f'came from further than {BESIDE} units). Sole melee blows came from '
            f'{show(train["reach"]["pooled"]["blows"]["p50"], 1)} units at the median and '
            f'{show(train["reach"]["pooled"]["blows"]["p90"], 1)} at the 90th percentile (check '
            f'{show(check["reach"]["pooled"]["blows"]["p50"], 1)} and '
            f'{show(check["reach"]["pooled"]["blows"]["p90"], 1)}; model {REACH}). The reach curve: swings are begun '
            f'at {show(curve[2.0, 3.0]["swings_per_second"])} to {show(curve[3.0, 3.5]["swings_per_second"])} a '
            f'second per monster standing 2 to 3.5 units off, {show(curve[3.5, 4.0]["swings_per_second"])} at 3.5 to '
            f'4 and {show(curve[4.0, 5.0]["swings_per_second"])} at 4 to 5; of the {far_swings:,} whole swings at '
            'the '
            'character begun from 4 units and further '
            f'{pair(far_took("hit_low"), far_took("hit_high"))}'
            ' took life. So 3.2 is right for the body of the blows; beyond it a monster begins a swing ever less '
            'often (the curve) and still takes life now and then: by type and rank, a few blows each (section 4; '
            'hurts.py has the Herald of Tower Cellar 5 striking from 7.7). Confidence: medium for the body, low '
            'for the tail.',
        ),
        (
            none['points'],
            f'**What is not a blow at all** ({none["points"]:,} points on the train half, '
            f'{none["points_share"]:.0%} of its life lost, in {none["n"]:,} drops of a median '
            f'{show(none["p50"])}). No suspect: {parts["unknown, nothing hostile within 8 units"]["n"]:,} of them with '
            f'nothing hostile within 8 units. {ticks["n"]:,} ({ticks["points"]:,} points) come in runs 0.4 s apart: '
            f'damage over time. {cost["n"]:,} ({cost["points"]:,} points) are 2% of the most life each, many in the '
            'first seconds of a take with nobody near: a cost the character pays itself, by the look of it, not '
            "a monster's doing. Expected effect on the refit: none on the blows, and that is the point: a refit "
            "that matches a take's total life lost with blows alone makes the blows carry this share too. Judge "
            'the refit on the drops with a suspect, or model damage over time apart. Confidence: high on the size, '
            'none on the causes (a take holds no state list of the character).',
        ),
    ]
    items.sort(key=lambda item: -item[0])
    return [f'{index}. {text}' for index, (_weight, text) in enumerate(items, 1)] + ['']


def surprises(train: Mapping[str, Any], check: Mapping[str, Any], whole: Mapping[str, Any]) -> list[str]:
    pack, shooters = whole['melee']['all'], whole['ranged']['all']
    late = sorted(k for k, v in whole['ranged'].items() if k != 'all' and not v['table_ranged'] and v['shots'] >= 40)
    return [
        '- **sim/monsters.py reads `aidel` and never uses it.** `Traits.delay` is set from `aidel(H)` and no line of '
        '`Pack` looks at it: a monster thinks again the frame its strike or its stand is over. The swing rate that '
        f"gives is still close to the takes' within {rates.MODEL_REACH} units (section 5), so this is a note, not "
        'a finding.',
        "- **STRIKE_FRAMES 16 and HIT_FRAME 8 are one number for all types; the takes show a swing's length by "
        'type and mode** (section 5, `usual frames`: 10 to 24 frames).',
        f'- **{show(pack["cut_share"])} of the attack runs within reach are cut short** before the middle of the '
        'swing (hit recovery or death under the blades, as far as a take can say). The model has no hit '
        'recovery (its module text says so): its monsters finish every swing.',
        "- **hurts.py `target_unit` reads the target's id and not its unit type** (the dword before it: 0 a "
        "player, 1 a monster). `aimed` compares the id with the character's alone. Not seen to matter; the "
        'type is there to be read (blows.py `target_of`).',
        '- **hurts.py `hurts` starts again after a frame whose vitals were not read**, so a drop across such a '
        'frame is not a row; calibrate.py `life_lost` counts it. blows.py counts across, as calibrate does.',
        '- **hurts.py `missile_point` raises on a missile row with an empty path record** (struct.error); such '
        'rows exist (4 of 125 takes sampled hold some). `hurts` only reads the missiles of the frame before a '
        'drop and has not met one; blows.py passes over them.',
        "- **units.jsonl does not hold the companions at all**: the mercenary and the pets are only in the frames' "
        'rows (`owner`, `ally`), which is where blows.py `companions` takes them from.',
        "- **The recorder writes no first sight for some of the character's own missiles** (20261012T165857Z-115: "
        '420 frame rows of `echoingstrike` and 67 of `echoingstrike_detonate` whose unit ids missiles.jsonl never '
        "names). blows.py takes such a missile for the character's when every first sight of its type in the take is.",
        "- **A missile's owner is in its record** (offset 0xE8: unit type and id) and nothing in the repo reads "
        "it; `hurt` events list missiles by type and distance only. With it a drop's `near` could name the shooter.",
        "- **mobs.py plays a type as ranged only by the threat table's flag.** These let hostile missiles go in "
        "the takes in 40 attack runs or more (an enchantment's sparks among them) and are melee, or nothing, in "
        'the arena: '
        + ', '.join(f'{whole["ranged"][k]["name"]} ({k}): {whole["ranged"][k]["shots"]}' for k in late)
        + '.',
        "- **The threat table's `hard` factor is on every shot of the arena** (Black Soul 640: 5.0). The takes hold "
        f'{(whole["ranged"].get("640") or {}).get("shots", 0)} Black Soul shots and '
        f'{(whole["ranged"].get("640") or {}).get("hits", 0)} sole hits: nothing to refit it on.',
        "- **cut.py calls the main set's physical resistance unknown; the manifests have it.** 14 takes whose "
        '`character_stats` show the main set in hand (fire 190, lightning 179, cold 189 before the penalty) hold '
        "stat 36 (`damageresist`) at 10 in 13 and -90 in one (a curse), the same 10 as the staff's set.",
        f"- **A shooter's path record seldom names whom it shoots at**: {show(shooters['path_aim_hero_share'])} of "
        f'{shooters["path_aim_known"]:,} shots with a record named the character, while '
        f"{show(shooters['on_hero_share'])} of the missiles ended on it. So `aimed` in a `hurt` event's `by` "
        'understates the shooters.',
        '',
    ]


def render(
    train: Mapping[str, Any],
    check: Mapping[str, Any],
    whole: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    counts: Mapping[str, Any],
) -> str:
    owners = whole['missile_owners']
    out = [
        "# Evidence for the refit of the arena's monsters",
        '',
        'Generated by `uv run --offline python -m tests.inventory_tracking.scenarios.arena.evidence.report` from the '
        f'takes under `{counts["root"]}`' + (f' since {counts["since"]}' if counts['since'] else '') + '; do not edit '
        'by hand. `evidence.json` beside this file holds the same measures per type for a program to read; '
        '`split.json` names the takes of each half. The method is in the module texts of `blows.py` (who a drop is '
        "put on) and `rates.py` (what is counted); the model's numbers are read off its parameters by `model.py`.",
        '',
        f'- **Takes:** {counts["found"]} found, {counts["read"]} read (schema 2), {counts["skipped"]} left out '
        f'({", ".join(f"{n} {why}" for why, n in counts["why"].items()) or "none"}).',
        f'- **Split:** by take name ({scan.SPLIT_RULE}): **train {train["takes"]} takes, {train["seconds"]:,.0f} s, '
        f'{train["classes"]["n"]:,} drops, {train["classes"]["points"]:,} points; check {check["takes"]} takes, '
        f'{check["seconds"]:,.0f} s, {check["classes"]["n"]:,} drops, {check["classes"]["points"]:,} points.** '
        'The refit is to be fitted on train and judged on check; every number that can become a parameter is given '
        'for both. Takes of one game session fall in both halves, so the halves are not independent of each other '
        'in area and monster mix: check guards against fitting noise, not against a different zone.',
        f"- **A drop** is a fall of the character's life of {HURT_LEAST} points or more between two read frames "
        '(combat/hurts.py `lost`: a fall of the most life with it is no blow), counted across frames whose vitals '
        'were not read.',
        '- **Sample sizes are small.** The takes hold '
        f'{whole["classes"]["n"]:,} drops in {whole["seconds"] / 3600:.1f} hours; '
        f'{whole["classes"][SOLE_MELEE]["n"]} are a melee blow of one monster alone and '
        f'{whole["classes"][SOLE_RANGED]["n"]} a shot of one alone. Every number below has its n; a per-type number '
        'on under 10 is an anecdote.',
        '',
        '## 1. What the takes can and cannot say',
        '',
        f"- **Whose a missile is: read, not inferred.** The missile's unit record holds its owner's unit id. Of "
        f'the hostile missiles tracked ({sum(owners.values()):,}), {owners.get("foe", 0):,} belong to a monster the '
        f"take saw and {owners.get('unknown', 0):,} to none it saw. Neither the type's `MissA1` (not in the bundled "
        "tables) nor co-occurrence is needed; where the installed game's monstats names a type's missile the "
        'owner id agrees with it (blows.py).',
        f"- **Whom a monster is after:** the path record's target, in {whole['takes_with_paths']} of "
        f'{whole["takes"]} takes. Without it only a monster beside the character ({BESIDE} units) is a striker.',
        f"- **Lines of sight:** the level file's flight layer, in {whole['takes_with_ground']} of {whole['takes']} "
        'takes; closed doors are ignored.',
        f'- **Enchantments:** in the take since 2026-10-11 22:23 UTC, else from the terror probe logs '
        f'({counts["mods_known"]:,} of {counts["units"]:,} units known).',
        '- **Not in a take:** the animation frame of a swing (a swing is a run of frames in one attack mode); '
        'whether a blow missed, was blocked or found the character gone; poison and other damage over time (no '
        "state list of the character); the damage kind of a drop; the character's resistances before 2026-10-11 "
        f'22:23 UTC ({counts["with_resists"]} of the {whole["classes"]["n"]:,} drops carry them, so no table here is '
        'split by resistance; the rows in the cache hold them).',
        f"- **A drop's suspects:** a hostile in an attack mode beside the character or within {SUSPECT_REACH:g} "
        f'units with the character as its target; the owners of the hostile missiles within {MISSILE_REACH:g} units '
        f"(or within {ENDED_REACH:g} and gone by the next frame); a dead owner makes it a death's missile; with "
        f'no suspect, an enchanted or exploding hostile that died within {NOVA_RADIUS:g} units in the '
        f'{NOVA_FRAMES} frames before.',
        '',
        '## 2. Who took the life: the classes of the drops',
        '',
        *classes_part(train, check, whole),
        f'## 3. Coverage: the {TOP} types with the most time within melee reach (all takes)',
        '',
        *table(
            ['type', 'ranged by the table', 's in reach', 's within 12', 's within 30'],
            [
                [
                    f'{row["name"]} ({row["txt"]})',
                    'yes' if row['ranged'] else '',
                    show(row['seconds_in_reach'], 0),
                    show(row['seconds_within_12'], 0),
                    show(row['seconds_within_30'], 0),
                ]
                for row in whole['coverage']
            ],
        ),
        '## 4. Melee reach',
        '',
        *reach_part(train, check, whole),
        '## 5. Melee: how often a monster in reach swings, and how often the swing takes life',
        '',
        *melee_part(train, check, whole),
        '## 6. Ranged: shots, whom they are at, hits',
        '',
        *ranged_part(train, check, whole),
        '## 7. Target choice',
        '',
        *targets_part(train, check, whole),
        '## 8. Big blows',
        '',
        *big_part(rows, whole),
        '## 9. Death novas and explosions',
        '',
        *nova_part(train, check, whole),
        '## 10. What the refit should change, in order of the life it explains',
        '',
        'Ordered by the points of the train half each line carries (said at its head). Each line: the measured '
        "number on train and on check, the model's, the sample, the expected effect and how far to trust it.",
        '',
        *changes(train, check, whole, rows),
        '## 11. What looked wrong on the way (nothing was changed)',
        '',
        *surprises(train, check, whole),
    ]
    return '\n'.join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='The evidence for the monster refit, from all takes.')
    parser.add_argument('--root', type=Path, default=scan.ROOT, help='the directory of the takes')
    parser.add_argument('--since', help='YYYYMMDD: leave out takes begun before')
    parser.add_argument('--limit', type=int, help='read the last so many takes only (development)')
    parser.add_argument('--jobs', type=int, help='worker processes (default: the cores, 16 at most)')
    parser.add_argument('--no-cache', action='store_true', help='read every take again')
    parser.add_argument('--cache', type=Path, default=scan.CACHE, help='where per-take results and raw rows go')
    parser.add_argument('--out', type=Path, default=HERE, help='where EVIDENCE.md, evidence.json and split.json go')
    args = parser.parse_args(argv)
    directories = scan.takes_under(args.root, args.since, args.limit)
    found = scan.scan(directories, cache=None if args.no_cache else args.cache, jobs=args.jobs)
    read = [one for one in found if 'rows' in one]
    halves = {name: [one for one in read if scan.half(one['take']) == name] for name in (scan.TRAIN, scan.CHECK)}

    def measured(part: Sequence[Mapping[str, Any]], reaches: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return rates.measure([row for one in part for row in one['rows']], [one['tally'] for one in part], reaches)

    train = measured(halves[scan.TRAIN])
    check, whole = measured(halves[scan.CHECK], train['reach']), measured(read, train['reach'])
    rows = [row for one in read for row in one['rows']]
    try:
        root = str(args.root.resolve().relative_to(scan.REPO))
    except ValueError:
        root = str(args.root)
    counts = {
        'root': root,
        'since': args.since,
        'found': len(found),
        'read': len(read),
        'skipped': len(found) - len(read),
        'why': dict(Counter(one['skipped'].split(' (')[0] for one in found if 'skipped' in one)),
        'mods_known': sum(one['tally']['mods_known'] for one in read),
        'units': sum(one['tally']['units'] for one in read),
        'with_resists': sum(row['resists'] is not None for row in rows),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'EVIDENCE.md').write_text(render(train, check, whole, rows, counts), encoding='utf-8')
    split = {
        'rule': scan.SPLIT_RULE,
        scan.TRAIN: [one['take'] for one in halves[scan.TRAIN]],
        scan.CHECK: [one['take'] for one in halves[scan.CHECK]],
        'left_out': {one['take']: one['skipped'] for one in found if 'skipped' in one},
    }
    (args.out / 'split.json').write_text(json.dumps(split, indent=0, sort_keys=True) + '\n', encoding='utf-8')
    slim = {
        name: {k: v for k, v in half.items() if k not in ('melee', 'melee_by_rank', 'ranged')}
        | {'melee_all': half['melee'].get('all'), 'ranged_all': half['ranged'].get('all')}
        for name, half in ((scan.TRAIN, train), (scan.CHECK, check), ('all', whole))
    }
    for half in slim.values():
        half['targets'] = {'pooled': half['targets']['pooled']}
        half['reach'] = {k: v for k, v in half['reach'].items() if k != 'types'}
    evidence = {
        'about': 'tests/inventory_tracking/scenarios/arena/evidence: see EVIDENCE.md; fit on train, judge on check',
        'counts': counts,
        'split_rule': scan.SPLIT_RULE,
        'thresholds': {
            'enough_seconds': rates.ENOUGH_SECONDS,
            'enough_blows': rates.ENOUGH_BLOWS,
            'enough_shots': rates.ENOUGH_SHOTS,
            'big': BIG,
        },
        'model': model.CONSTANTS,
        **slim,
        'types': per_type(train, check, whole),
        'big_drops': [
            {
                'points': row['lost'],
                'share': row['share'],
                'dead': row['dead'],
                'take': row['take'],
                'frame': row['frame'],
                'half': scan.half(row['take']),
                'class': row['class'],
                'suspects': [
                    {k: s[k] for k in ('txt', 'name', 'rank', 'tier', 'mods', 'level', 'away', 'via', 'missile')}
                    for s in row['by']
                ],
                'model_most': max((model.most(s) for s in row['by'] if s['via'] in (SWING, MISSILE)), default=None),
            }
            for row in sorted(rows, key=lambda r: -r['lost'])
            if row['lost'] > BIG
        ],
    }
    (args.out / 'evidence.json').write_text(
        json.dumps(evidence, indent=None, separators=(',', ':'), sort_keys=True) + '\n', encoding='utf-8'
    )
    if not args.no_cache:
        with (args.cache / 'blows.jsonl').open('w', encoding='utf-8') as handle:
            handle.writelines(json.dumps(row, separators=(',', ':')) + '\n' for row in rows)
    print(
        f'{len(read)} takes read ({len(found) - len(read)} left out): train {train["takes"]} takes / '
        f'{train["classes"]["n"]} drops / {train["classes"]["points"]} points, check {check["takes"]} / '
        f'{check["classes"]["n"]} / {check["classes"]["points"]}',
        file=sys.stderr,
    )
    print(f'{args.out / "EVIDENCE.md"}, evidence.json, split.json written', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
