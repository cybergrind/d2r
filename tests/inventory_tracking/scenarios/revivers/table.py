"""Which monsters bring other monsters back, read off the game's own tables (2026-10-10).

`derive` reads the dumped excel tables (pricing/raw/game-excel: monstats, skills, levels,
superuniques, monsters-strings) and `revivers.json` beside this file is what it found, so the
scenarios run without the dump (it is not checked in). Rebuild:

    uv run --offline python -m tests.inventory_tracking.scenarios.revivers.table

How a row gets in:

- reviver: a monstats row with one of its Skill1..8 a skills.txt row whose `srvdofunc` is RESURRECT
  (97: `Resurrect` and `Resurrect2`, both `TargetCorpse` 1). What it raises, how often and from how
  far is the monster's AI, not a table column: the Hell AI parameters `aipN(H)` are read by position
  (RULES), and the positions' meaning is the legacy server's source (third-parties/D2MOO
  source/D2Game/src/AI/AiThink.cpp, `D2C_FallenShamanAIParams`, `D2C_GreatMummyAIParams`,
  `D2C_FetishShamanAIParams` and the three target callbacks beside them). That source is the 1.10-era
  game, not this build: the numbers are this build's, their meaning is taken on its word.
- self: a monstats row with a skill whose `srvstfunc` is SELF_RESURRECT (61): it gets up by itself,
  there is nobody to kill first.
- spawner: a monstats row with the `spawn` column set (the monster it makes) and `enabled` 1.

A txt id is monstats `*hcIdx`, the id the game's memory and combat/data/tables.json use. Areas are
levels.txt `nmon1..25` (the Nightmare and Hell population); the Terror Zone is the Herald group of
inventory_tracking/terror/zones.py that holds the area.
"""

import csv
import json
import math
from functools import cache
from pathlib import Path
from typing import Any


HERE = Path(__file__).parent
TABLE = HERE / 'revivers.json'
EXCEL = HERE.parents[3] / 'pricing' / 'raw' / 'game-excel'
RESURRECT = '97'  # skills.txt srvdofunc of Resurrect and Resurrect2
SELF_RESURRECT = '61'  # skills.txt srvstfunc of Self-resurrect
GAME_RATE = 25  # frames a second

# AI -> where its Hell parameters hold the raise chance (percent per think) and the raise range (units
# from the reviver to the corpse), and what it raises. `aidel(H)` is the frames between two thinks.
RULES: dict[str, dict[str, Any]] = {
    'FallenShaman': {
        'chance': 'aip1(H)',
        'range': 'aip4(H)',
        'bases': ('fallen1', 'fallenshaman1'),
        'raises': 'corpses whose BaseId is fallen1 or fallenshaman1 (other shamans too), never a unique or champion',
    },
    'GreaterMummy': {
        'chance': 'aip2(H)',
        'range': 'aip5(H)',
        'flag': 'lUndead',
        'raises': 'corpses of any lUndead monster on its side, champions too, never a unique; it also heals them',
    },
    'FetishShaman': {
        'chance': 'aip1(H)',
        'range': 'aip5(H)',
        'close': 'aip3(H)',  # the squared distance to the corpse from which it raises; further off it walks there
        'bases': ('fetish1', 'fetishblow1'),
        'raises': (
            'corpses whose BaseId is fetish1 or fetishblow1; it walks to the corpse and raises from close by '
            '(aip3(H) against the squared distance); with aip2(H) 3 uniques and champions too'
        ),
    },
}


def rows(directory: Path, name: str) -> list[dict[str, str]]:
    with (directory / f'{name}.txt').open(encoding='latin-1', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def number(text: str) -> int | None:
    return int(text) if text.strip().lstrip('-').isdigit() else None


def skills_of(row: dict[str, str]) -> list[str]:
    return [row[f'Skill{n}'] for n in range(1, 9) if row.get(f'Skill{n}')]


def derive(directory: Path = EXCEL) -> dict[str, Any]:
    """The table from the dumped excel files in `directory`."""
    from inventory_tracking.terror.zones import GROUPS

    monsters = [r for r in rows(directory, 'monstats') if r.get('*hcIdx', '').isdigit()]
    by_id = {r['Id']: r for r in monsters}
    skills = {r['skill']: r for r in rows(directory, 'skills')}
    levels = [r for r in rows(directory, 'levels') if r.get('Id', '').isdigit() and r.get('MonLvlEx(H)')]
    strings = {
        e['Key']: e['enUS'] for e in json.loads((directory / 'monsters-strings.json').read_text(encoding='utf-8-sig'))
    }
    zone_of = {area: group.zone for group in GROUPS for area in group.areas}
    raising = {name for name, s in skills.items() if s['srvdofunc'] == RESURRECT and s['TargetCorpse'] == '1'}
    rising = {name for name, s in skills.items() if s['srvstfunc'] == SELF_RESURRECT}

    def areas(monster_id: str) -> list[dict[str, Any]]:
        found = []
        for level in levels:
            if monster_id in {level[f'nmon{n}'] for n in range(1, 26)}:
                area = int(level['Id'])
                found.append(
                    {
                        'area': area,
                        'name': level['LevelName'],
                        'level': int(level['MonLvlEx(H)']),
                        'zone': zone_of.get(area),
                    }
                )
        return found

    def common(row: dict[str, str]) -> dict[str, Any]:
        return {
            'txt': int(row['*hcIdx']),
            'id': row['Id'],
            'name': strings.get(row['NameStr'], row['NameStr']),
            'ai': row['AI'],
            'herald': row.get('CannotHerald') != '1',
            'areas': areas(row['Id']),
        }

    def raised_by(rule: dict[str, Any]) -> list[dict[str, Any]]:
        if 'bases' in rule:
            kept = [r for r in monsters if r['BaseId'] in rule['bases']]
        else:
            kept = [r for r in monsters if r[rule['flag']] == '1']
        return [{'txt': int(r['*hcIdx']), 'id': r['Id']} for r in kept if r['enabled'] == '1']

    revivers, selves, spawners = [], [], []
    for row in monsters:
        if row['enabled'] != '1':
            continue
        cast = [name for name in skills_of(row) if name in raising]
        if cast:
            rule = RULES.get(row['AI'])
            entry = common(row) | {'skill': cast[0], 'skill_id': int(skills[cast[0]]['*Id'])}
            if rule is not None:
                chance, think = number(row[rule['chance']]), number(row['aidel(H)'])
                entry |= {
                    'raise_chance': chance,
                    'raise_range': number(row[rule['range']]),
                    'think_frames': think,
                    # The mean wait for one raise with a corpse in range, the cast itself not counted
                    # (its length is in no table dumped here): the fastest the tables allow.
                    'raise_frames': round(think * 100 / chance) if chance and think else None,
                    'raises': rule['raises'],
                    'minions': [m for m in (row['minion1'], row['minion2']) if m],
                    'undead': 'low' if row['lUndead'] == '1' else 'high' if row['hUndead'] == '1' else None,
                }
                if 'close' in rule:
                    entry['raise_close'] = round(math.sqrt(int(row[rule['close']])), 1)
            revivers.append(entry)
        if any(name in rising for name in skills_of(row)):
            selves.append(common(row) | {'skill': 'Self-resurrect', 'aip8': number(row['aip8(H)'])})
        if row.get('spawn'):
            made = by_id.get(row['spawn'])
            spawners.append(
                common(row) | {'spawns': row['spawn'], 'spawns_txt': int(made['*hcIdx']) if made is not None else None}
            )
    bosses = [
        {'name': strings.get(s['Name'], s['Name']), 'class': s['Class']}
        for s in rows(directory, 'superuniques')
        if s.get('Class') in {entry['id'] for entry in revivers}
    ]
    return {
        'dated': '2026-10-10',
        'source': 'pricing/raw/game-excel (dumped 2026-10-06): monstats, skills, levels, superuniques, strings',
        'rules': {
            ai: {key: value for key, value in rule.items() if key not in ('bases', 'close')}
            for ai, rule in RULES.items()
        },
        'raised': {ai: raised_by(rule) for ai, rule in RULES.items()},
        'revivers': revivers,
        'self_revivers': selves,
        'spawners': spawners,
        'super_uniques': bosses,
    }


@cache
def table() -> dict[str, Any]:
    return json.loads(TABLE.read_text())


def reviver(monster_id: str) -> dict[str, Any]:
    """The reviver row of a monstats Id."""
    return next(entry for entry in table()['revivers'] if entry['id'] == monster_id)


def raised(ai: str) -> dict[str, int]:
    """Monstats Id -> txt id of what a reviver with that AI raises."""
    return {entry['id']: entry['txt'] for entry in table()['raised'][ai]}


def main() -> int:
    found = derive()
    TABLE.write_text(json.dumps(found, indent=1, ensure_ascii=False) + '\n')
    print(
        f'{TABLE}: {len(found["revivers"])} revivers, {len(found["self_revivers"])} self-revivers, '
        f'{len(found["spawners"])} spawners'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
