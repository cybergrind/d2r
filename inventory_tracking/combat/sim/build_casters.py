"""Writes sim/casters.json: the game's rows the Chaos Sanctuary casters think and cast by (sim/casters.py).

Run: uv run --offline python -m inventory_tracking.combat.sim.build_casters [<game-excel dir>]

The runtime reads only casters.json (checked in); pricing/raw/game-excel is the build input. Kept: the monstats
rows of the four read AIs (FingerMage, DoomKnight, OblivionKnight, Megademon), the skills they cast and the curses,
each skill's missiles, Hell's difficultylevels bonuses, the curse state ids.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any


SOURCE = Path(__file__).parents[3] / 'pricing' / 'raw' / 'game-excel'
TARGET = Path(__file__).parent / 'casters.json'
AIS = ('FingerMage', 'DoomKnight', 'OblivionKnight', 'Megademon')
CURSES = ('Amplify Damage', 'Decrepify', 'Lower Resist')
# Missiles no skill row names as its server missile: DoomKnightMissile's bolts (notes-ai-74.md), the Venom Lord's
# client flames, the curses' marks (cs-patterns.txt).
EXTRA_MISSILES = (
    'undeadmissile2', 'undeadmissile3', 'undeadmissile4', 'fetishinferno1', 'fetishinferno2',
    'curseamplifydamage', 'cursedecrepify', 'curselowerresist',
)  # fmt: skip
STATES = ('amplifydamage', 'decrepify', 'lowerresist', 'fingermagecurse', 'inferno')
MONSTER_FIELDS = (
    'Id', '*hcIdx', 'BaseId', 'NameStr', 'AI', 'Velocity', 'Run', 'Level(H)', 'aidel(H)', 'aidist(H)',
    *(f'aip{n}(H)' for n in range(1, 9)),
    *(f'Skill{n}' for n in range(1, 9)), *(f'Sk{n}mode' for n in range(1, 9)), *(f'Sk{n}lvl' for n in range(1, 9)),
    'A1MinD(H)', 'A1MaxD(H)', 'A1TH(H)', 'El1Mode', 'El1Type', 'El1Pct(H)', 'El1MinD(H)', 'El1MaxD(H)', 'El1Dur(H)',
)  # fmt: skip
SKILL_FIELDS = (
    'skill', '*Id', 'srvdofunc', 'srvmissilea', 'cltmissilea', 'cltmissileb', 'auratargetstate', 'auralencalc',
    'aurarangecalc', *(f'aurastat{n}' for n in range(1, 5)), *(f'aurastatcalc{n}' for n in range(1, 5)),
    *(f'Param{n}' for n in range(1, 9)), 'monanim', 'calc1', 'calc2', 'calc3',
)  # fmt: skip
MISSILE_FIELDS = (
    'Missile', '*ID', 'Vel', 'Range', 'Size', 'CollideKill', 'LastCollide', 'DamageRate', 'HitShift', 'ToHit',
    'MinDamage', *(f'MinLevDam{n}' for n in range(1, 6)), 'MaxDamage', *(f'MaxLevDam{n}' for n in range(1, 6)),
    'EType', 'EMin', *(f'MinELev{n}' for n in range(1, 6)), 'EMax', *(f'MaxELev{n}' for n in range(1, 6)), 'ELen',
    'Param1', 'Param2', 'Param3',
)  # fmt: skip


def rows(source: Path, name: str) -> list[dict[str, str]]:
    with (source / f'{name}.txt').open(newline='', encoding='utf-8', errors='replace') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def pick(row: dict[str, str], fields: tuple[str, ...]) -> dict[str, str]:
    return {name: row[name] for name in fields if row.get(name)}


def build(source: Path = SOURCE) -> dict[str, Any]:
    monsters = {row['*hcIdx']: pick(row, MONSTER_FIELDS) for row in rows(source, 'monstats') if row['AI'] in AIS}
    named = {row['skill']: row for row in rows(source, 'skills')}
    wanted = {row[f'Skill{n}'] for row in monsters.values() for n in range(1, 9) if row.get(f'Skill{n}')}
    skills = {name: pick(named[name], SKILL_FIELDS) for name in sorted(wanted | set(CURSES)) if name in named}
    by_name = {row['Missile']: row for row in rows(source, 'missiles')}
    missiles_wanted = {skill.get('srvmissilea') for skill in skills.values()} | set(EXTRA_MISSILES)
    missiles = {
        by_name[name]['*ID']: pick(by_name[name], MISSILE_FIELDS) for name in sorted(filter(None, missiles_wanted))
    }
    hell = next(row for row in rows(source, 'difficultylevels') if row['Name'] == 'Hell')
    states = {row['state']: index for index, row in enumerate(rows(source, 'states')) if row['state'] in STATES}
    return {
        'source': 'pricing/raw/game-excel (monstats, skills, missiles, difficultylevels, states); build_casters.py',
        'monsters': monsters,
        'skills': skills,
        'missiles': missiles,
        'hell': {name: hell[name] for name in ('MonsterSkillBonus', 'ResistPenalty')},
        'states': states,
    }


if __name__ == '__main__':
    found = build(Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE)
    TARGET.write_text(json.dumps(found, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(
        f'{TARGET}: {len(found["monsters"])} monsters, {len(found["skills"])} skills, {len(found["missiles"])} missiles'
    )
